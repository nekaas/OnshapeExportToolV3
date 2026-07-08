"""Structured event bus — the backbone for live updates, audit, and AI-readiness.

Every meaningful state change in the platform (a job starting, an export
finishing, a credential failing, a backup completing) is published as a typed
:class:`Event` onto a process-wide :class:`EventBus`. Subscribers fan the event
out to wherever it needs to go:

* the **audit log** persists it to SQLite (see :mod:`onshape_export_manager.core.audit`),
* the **WebSocket stream** pushes it to connected browsers in real time,
* **notifications** match it against configured channels,
* and a future **AI assistant** can consume the same stream to observe and act.

The bus is deliberately dependency-free and thread-safe so it can be shared by
the synchronous background worker thread, the async web event loop, and the CLI
without any of them knowing about the others. Subscribers may be plain callables
(invoked synchronously) or coroutine functions (scheduled onto the loop that
published, or run on a fresh loop if none is running).

Design goals:

* **Never let a subscriber break the publisher.** A raising subscriber is
  logged and skipped; publishing always succeeds.
* **Keep a bounded in-memory ring buffer** of recent events so a newly connected
  client (or a late-starting audit consumer) can replay what it missed.
* **Zero-config**: ``EventBus()`` works standalone; everything else is opt-in.
"""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from onshape_export_manager.core.logger import EVENT_LOGGER, get_logger


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventSeverity(StrEnum):
    """Severity classification used for filtering, alerting, and audit levels."""

    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(StrEnum):
    """Top-level grouping for an event, used by subscribers to route/filter."""

    SYSTEM = "system"
    WORKER = "worker"
    QUEUE = "queue"
    EXPORT = "export"
    SCHEDULER = "scheduler"
    CONFIG = "config"
    AUTH = "auth"
    STORAGE = "storage"
    BACKUP = "backup"
    NOTIFICATION = "notification"
    PLUGIN = "plugin"
    SECURITY = "security"


class EventType(StrEnum):
    """Canonical event names. Stable strings — safe to match on in plugins/AI.

    Grouped by category. New event types are additive; never rename an existing
    value (subscribers and persisted audit rows depend on the string).
    """

    # System / lifecycle
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH_WARNING = "system.health_warning"

    # Worker
    WORKER_STARTED = "worker.started"
    WORKER_STOPPED = "worker.stopped"
    WORKER_TICK = "worker.tick"

    # Queue / jobs
    JOB_ENQUEUED = "queue.job_enqueued"
    JOB_STARTED = "queue.job_started"
    JOB_COMPLETED = "queue.job_completed"
    JOB_FAILED = "queue.job_failed"
    JOB_RETRY_SCHEDULED = "queue.job_retry_scheduled"
    JOB_CANCELLED = "queue.job_cancelled"

    # Export results
    EXPORT_COMPLETED = "export.completed"
    EXPORT_FAILED = "export.failed"

    # Scheduler
    SCHEDULE_TRIGGERED = "scheduler.triggered"
    SCHEDULE_CREATED = "scheduler.created"
    SCHEDULE_UPDATED = "scheduler.updated"
    SCHEDULE_DELETED = "scheduler.deleted"

    # Configuration
    CONFIG_UPDATED = "config.updated"
    LABELS_CHANGED = "config.labels_changed"

    # Auth / security
    AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"

    # Organizations / credentials
    ORG_CREATED = "config.org_created"
    ORG_DELETED = "config.org_deleted"
    CREDENTIAL_RATE_LIMITED = "config.credential_rate_limited"

    # Backups
    BACKUP_CREATED = "backup.created"
    BACKUP_RESTORED = "backup.restored"
    BACKUP_FAILED = "backup.failed"

    # Notifications
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # Plugins
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_ERROR = "plugin.error"

    # Generic / custom (plugins may emit this with arbitrary data)
    CUSTOM = "custom"


# Default category for each event type, so callers usually only pass an EventType.
_TYPE_CATEGORY: dict[EventType, EventCategory] = {
    EventType.SYSTEM_STARTUP: EventCategory.SYSTEM,
    EventType.SYSTEM_SHUTDOWN: EventCategory.SYSTEM,
    EventType.SYSTEM_HEALTH_WARNING: EventCategory.SYSTEM,
    EventType.WORKER_STARTED: EventCategory.WORKER,
    EventType.WORKER_STOPPED: EventCategory.WORKER,
    EventType.WORKER_TICK: EventCategory.WORKER,
    EventType.JOB_ENQUEUED: EventCategory.QUEUE,
    EventType.JOB_STARTED: EventCategory.QUEUE,
    EventType.JOB_COMPLETED: EventCategory.QUEUE,
    EventType.JOB_FAILED: EventCategory.QUEUE,
    EventType.JOB_RETRY_SCHEDULED: EventCategory.QUEUE,
    EventType.JOB_CANCELLED: EventCategory.QUEUE,
    EventType.EXPORT_COMPLETED: EventCategory.EXPORT,
    EventType.EXPORT_FAILED: EventCategory.EXPORT,
    EventType.SCHEDULE_TRIGGERED: EventCategory.SCHEDULER,
    EventType.SCHEDULE_CREATED: EventCategory.SCHEDULER,
    EventType.SCHEDULE_UPDATED: EventCategory.SCHEDULER,
    EventType.SCHEDULE_DELETED: EventCategory.SCHEDULER,
    EventType.CONFIG_UPDATED: EventCategory.CONFIG,
    EventType.LABELS_CHANGED: EventCategory.CONFIG,
    EventType.AUTH_LOGIN_SUCCEEDED: EventCategory.AUTH,
    EventType.AUTH_LOGIN_FAILED: EventCategory.AUTH,
    EventType.AUTH_LOGOUT: EventCategory.AUTH,
    EventType.ORG_CREATED: EventCategory.CONFIG,
    EventType.ORG_DELETED: EventCategory.CONFIG,
    EventType.CREDENTIAL_RATE_LIMITED: EventCategory.CONFIG,
    EventType.BACKUP_CREATED: EventCategory.BACKUP,
    EventType.BACKUP_RESTORED: EventCategory.BACKUP,
    EventType.BACKUP_FAILED: EventCategory.BACKUP,
    EventType.NOTIFICATION_SENT: EventCategory.NOTIFICATION,
    EventType.NOTIFICATION_FAILED: EventCategory.NOTIFICATION,
    EventType.PLUGIN_LOADED: EventCategory.PLUGIN,
    EventType.PLUGIN_ENABLED: EventCategory.PLUGIN,
    EventType.PLUGIN_DISABLED: EventCategory.PLUGIN,
    EventType.PLUGIN_ERROR: EventCategory.PLUGIN,
    EventType.CUSTOM: EventCategory.SYSTEM,
}


@dataclass(slots=True)
class Event:
    """An immutable record of something that happened in the platform.

    Attributes
    ----------
    type:
        The canonical :class:`EventType`.
    category:
        Top-level grouping; defaults from the event type.
    severity:
        Importance, used for filtering, alerting, and audit-log level.
    message:
        Human-readable summary (shown in the UI activity feed).
    data:
        Structured, JSON-serializable payload with event-specific fields.
    source:
        Subsystem that emitted the event (e.g. ``"worker"``, ``"web"``).
    actor:
        Who/what initiated it (``"system"``, ``"scheduler"``, a username).
    id / timestamp:
        Auto-generated unique id and UTC timestamp.
    """

    type: EventType
    message: str = ""
    category: EventCategory | None = None
    severity: EventSeverity = EventSeverity.INFO
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    actor: str = "system"
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.category is None:
            self.category = _TYPE_CATEGORY.get(self.type, EventCategory.SYSTEM)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        payload = asdict(self)
        payload["type"] = str(self.type)
        payload["category"] = str(self.category)
        payload["severity"] = str(self.severity)
        payload["timestamp"] = self.timestamp.astimezone(timezone.utc).isoformat()
        return payload


# A subscriber receives one Event. It may be a plain callable or a coroutine fn.
Subscriber = Callable[[Event], None] | Callable[[Event], Awaitable[None]]


@dataclass(slots=True)
class _Subscription:
    callback: Subscriber
    types: frozenset[EventType] | None
    categories: frozenset[EventCategory] | None
    token: int


class EventBus:
    """Thread-safe publish/subscribe hub for :class:`Event` objects.

    Subscribers register with :meth:`subscribe`, optionally filtering by event
    type or category. Publishers call :meth:`publish` (or the convenience
    :meth:`emit`). Recent events are retained in a bounded ring buffer for
    replay via :meth:`recent`.
    """

    def __init__(self, *, history_size: int = 500) -> None:
        self._subscriptions: list[_Subscription] = []
        self._history: deque[Event] = deque(maxlen=history_size)
        self._lock = threading.RLock()
        self._token = 0
        self.logger = get_logger(EVENT_LOGGER)

    # -- Subscription ------------------------------------------------------

    def subscribe(
        self,
        callback: Subscriber,
        *,
        types: list[EventType] | None = None,
        categories: list[EventCategory] | None = None,
    ) -> int:
        """Register *callback*; returns a token usable with :meth:`unsubscribe`.

        If *types* or *categories* are given, the subscriber only receives
        matching events. Omitting both subscribes to everything.
        """
        with self._lock:
            self._token += 1
            token = self._token
            self._subscriptions.append(
                _Subscription(
                    callback=callback,
                    types=frozenset(types) if types else None,
                    categories=frozenset(categories) if categories else None,
                    token=token,
                )
            )
            return token

    def unsubscribe(self, token: int) -> bool:
        """Remove a subscription by token. Returns True if one was removed."""
        with self._lock:
            before = len(self._subscriptions)
            self._subscriptions = [s for s in self._subscriptions if s.token != token]
            return len(self._subscriptions) != before

    # -- Publishing --------------------------------------------------------

    def emit(
        self,
        type: EventType,
        message: str = "",
        *,
        severity: EventSeverity = EventSeverity.INFO,
        data: dict[str, Any] | None = None,
        source: str = "system",
        actor: str = "system",
        category: EventCategory | None = None,
    ) -> Event:
        """Construct and publish an :class:`Event` in one call."""
        event = Event(
            type=type,
            message=message,
            category=category or _TYPE_CATEGORY.get(type, EventCategory.SYSTEM),
            severity=severity,
            data=dict(data or {}),
            source=source,
            actor=actor,
        )
        self.publish(event)
        return event

    def publish(self, event: Event) -> Event:
        """Fan *event* out to all matching subscribers. Never raises.

        Returns the event so callers can capture its generated id/timestamp.
        """
        with self._lock:
            self._history.append(event)
            subscriptions = list(self._subscriptions)
        for subscription in subscriptions:
            if not self._matches(subscription, event):
                continue
            self._dispatch(subscription.callback, event)
        return event

    @staticmethod
    def _matches(subscription: _Subscription, event: Event) -> bool:
        if subscription.types is not None and event.type not in subscription.types:
            return False
        if subscription.categories is not None and event.category not in subscription.categories:
            return False
        return True

    def _dispatch(self, callback: Subscriber, event: Event) -> None:
        try:
            result = callback(event)
            if asyncio.iscoroutine(result):
                self._schedule_coroutine(result)
        except Exception:  # noqa: BLE001 - a subscriber must never break publishing
            self.logger.exception("Event subscriber raised for %s", event.type)

    def _schedule_coroutine(self, coro: Awaitable[None]) -> None:
        """Run a coroutine subscriber without blocking the publisher.

        If a loop is already running on this thread (the web event loop), the
        coroutine is scheduled onto it. Otherwise (e.g. the worker thread) it is
        run to completion on a throwaway loop.

        Note: today's real subscribers (audit, WebSocket fan-out) are all sync
        callables, so this path is a safety net. If async subscribers are added
        later, prefer running them via a dedicated long-lived loop rather than
        relying on whichever loop happens to be publishing, since a short-lived
        worker-tick loop may exit before a scheduled task runs.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            loop.create_task(coro)  # type: ignore[arg-type]
            return
        try:
            asyncio.run(coro)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - isolate async subscriber failures
            self.logger.exception("Async event subscriber failed")

    # -- Inspection --------------------------------------------------------

    def recent(
        self,
        *,
        limit: int = 100,
        categories: list[EventCategory] | None = None,
        min_severity: EventSeverity | None = None,
    ) -> list[Event]:
        """Return up to *limit* recent events, newest last, with optional filters."""
        wanted_categories = frozenset(categories) if categories else None
        min_rank = _SEVERITY_RANK[min_severity] if min_severity else None
        with self._lock:
            events = list(self._history)
        if wanted_categories is not None:
            events = [e for e in events if e.category in wanted_categories]
        if min_rank is not None:
            events = [e for e in events if _SEVERITY_RANK[e.severity] >= min_rank]
        return events[-limit:]

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)


_SEVERITY_RANK: dict[EventSeverity, int] = {
    EventSeverity.DEBUG: 0,
    EventSeverity.INFO: 1,
    EventSeverity.SUCCESS: 1,
    EventSeverity.WARNING: 2,
    EventSeverity.ERROR: 3,
    EventSeverity.CRITICAL: 4,
}
