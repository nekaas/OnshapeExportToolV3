"""Notification channels — deliver events to Discord, Slack, Teams, email, webhooks.

The :class:`NotificationService` subscribes to the shared
:class:`~onshape_export_manager.core.events.EventBus` and, for each published
:class:`~onshape_export_manager.core.events.Event`, dispatches it to every
configured channel whose category/severity filter matches. Delivery happens on a
background daemon thread so a slow webhook never blocks the publisher (the worker
or the web request that emitted the event).

Channels are configured entirely through the browser (no JSON editing): the web
layer reads/writes the ``notifications`` section of ``config.json`` via the
:class:`~onshape_export_manager.core.configuration.NotificationChannelConfig`
model. Each channel has a *kind* (``discord`` / ``slack`` / ``teams`` /
``email`` / ``webhook``), a *target* (webhook URL or email address), a minimum
severity, and an optional category allow-list.

Senders use the already-present ``requests`` library for HTTP and the stdlib
``smtplib`` for email, so no new dependencies are required. Each sender is small,
self-contained, and easy to extend — adding a new provider means adding one
function to :data:`SENDERS`.
"""

from __future__ import annotations

import queue
import smtplib
import threading
from dataclasses import dataclass
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, Callable

from onshape_export_manager.core.events import (
    Event,
    EventBus,
    EventSeverity,
    EventType,
)
from onshape_export_manager.core.logger import NOTIFICATION_LOGGER, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.core.configuration import ConfigManager


_SEVERITY_RANK: dict[str, int] = {
    "debug": 0,
    "info": 1,
    "success": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}

# Accent colors (Discord/Slack int + hex) keyed by severity for richer messages.
_SEVERITY_COLOR: dict[str, int] = {
    "debug": 0x6B7280,
    "info": 0x6366F1,
    "success": 0x10B981,
    "warning": 0xF59E0B,
    "error": 0xEF4444,
    "critical": 0xB91C1C,
}


@dataclass(slots=True)
class ChannelSpec:
    """A normalized, ready-to-send channel definition (decoupled from pydantic)."""

    id: str
    name: str
    kind: str
    enabled: bool
    target: str
    min_severity: str
    categories: frozenset[str]
    options: dict[str, Any]

    def matches(self, event: Event) -> bool:
        if not self.enabled or not self.target:
            return False
        # Delivery-result meta-events are never themselves delivered (loop guard).
        if event.type in _META_EVENT_TYPES:
            return False
        if self.categories and str(event.category) not in self.categories:
            return False
        event_rank = _SEVERITY_RANK.get(str(event.severity), 1)
        min_rank = _SEVERITY_RANK.get(self.min_severity, 1)
        return event_rank >= min_rank


@dataclass(slots=True)
class DeliveryResult:
    """Outcome of attempting to deliver one event to one channel."""

    channel_id: str
    kind: str
    ok: bool
    detail: str = ""


class NotificationService:
    """Subscribes to the event bus and delivers events to configured channels."""

    def __init__(
        self,
        config_manager: "ConfigManager",
        event_bus: EventBus,
        *,
        http_post: Callable[..., Any] | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.timeout = timeout
        self.logger = get_logger(NOTIFICATION_LOGGER)
        self._http_post = http_post or _default_http_post
        self._token: int | None = None
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=2000)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Subscribe to the bus and start the delivery worker (idempotent)."""
        if self._token is not None:
            return
        self._stop.clear()
        self._token = self.event_bus.subscribe(self._enqueue)
        thread = threading.Thread(
            target=self._run, name="oem-notifications", daemon=True
        )
        self._thread = thread
        thread.start()
        self.logger.info("Notification service started")

    def stop(self, *, timeout: float = 5.0) -> None:
        """Unsubscribe and stop the delivery worker."""
        if self._token is not None:
            self.event_bus.unsubscribe(self._token)
            self._token = None
        self._stop.set()
        self._queue.put_nowait(_SENTINEL)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    def _enqueue(self, event: Event) -> None:
        """Bus subscriber: hand the event to the delivery thread (non-blocking)."""
        if event is _SENTINEL:  # pragma: no cover - defensive
            return
        # Never deliver our own delivery-result meta-events. They are still
        # published to the bus (so the audit log and WebSocket feed see them),
        # but feeding them back into delivery would create a self-sustaining
        # loop: every send emits NOTIFICATION_SENT, which would match an
        # all-categories channel and trigger another send, ad infinitum.
        if event.type in _META_EVENT_TYPES:
            return
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self.logger.warning("Notification queue full; dropping event %s", event.type)

    def _run(self) -> None:
        while not self._stop.is_set():
            event = self._queue.get()
            if event is _SENTINEL:
                break
            try:
                self.dispatch(event)
            except Exception:  # noqa: BLE001 - delivery must never kill the thread
                self.logger.exception("Notification dispatch failed for %s", event.type)

    # -- Dispatch ----------------------------------------------------------

    def channels(self) -> list[ChannelSpec]:
        """Load and normalize the configured channels (empty on config error)."""
        try:
            config = self.config_manager.load()
        except Exception:  # noqa: BLE001 - never let bad config break notifications
            return []
        notifications = config.app.notifications
        if not notifications.enabled:
            return []
        specs: list[ChannelSpec] = []
        for channel in notifications.channels:
            specs.append(
                ChannelSpec(
                    id=channel.id,
                    name=channel.name or channel.id,
                    kind=channel.kind,
                    enabled=channel.enabled,
                    target=channel.target,
                    min_severity=channel.min_severity,
                    categories=frozenset(channel.categories),
                    options=dict(channel.options),
                )
            )
        return specs

    def dispatch(self, event: Event) -> list[DeliveryResult]:
        """Deliver *event* to every matching channel. Returns per-channel results."""
        results: list[DeliveryResult] = []
        for spec in self.channels():
            if not spec.matches(event):
                continue
            results.append(self._deliver(spec, event))
        return results

    def _deliver(self, spec: ChannelSpec, event: Event) -> DeliveryResult:
        sender = SENDERS.get(spec.kind)
        if sender is None:
            return DeliveryResult(spec.id, spec.kind, False, f"unknown kind '{spec.kind}'")
        try:
            sender(self, spec, event)
        except Exception as exc:  # noqa: BLE001 - report, don't raise
            self.logger.warning("Channel %s (%s) delivery failed: %s", spec.name, spec.kind, exc)
            self._emit_meta(EventType.NOTIFICATION_FAILED, spec, str(exc))
            return DeliveryResult(spec.id, spec.kind, False, str(exc))
        self._emit_meta(EventType.NOTIFICATION_SENT, spec, "delivered")
        return DeliveryResult(spec.id, spec.kind, True, "delivered")

    def test_channel(self, spec: ChannelSpec) -> DeliveryResult:
        """Send a synthetic test event to one channel (used by the UI 'Test' button)."""
        test_event = Event(
            type=EventType.CUSTOM,
            message=f"Test notification from Onshape Export Manager → {spec.name}",
            severity=EventSeverity.INFO,
            source="notifications",
            actor="test",
        )
        return self._deliver(spec, test_event)

    def _emit_meta(self, event_type: EventType, spec: ChannelSpec, detail: str) -> None:
        """Emit a meta-event about delivery, without recursing infinitely.

        Meta-events use the NOTIFICATION category; channels that subscribe to
        the NOTIFICATION category are skipped for these to avoid loops.
        """
        try:
            self.event_bus.emit(
                event_type,
                f"Notification {('sent to' if event_type == EventType.NOTIFICATION_SENT else 'failed for')} {spec.name}",
                severity=(
                    EventSeverity.INFO
                    if event_type == EventType.NOTIFICATION_SENT
                    else EventSeverity.WARNING
                ),
                data={"channel": spec.name, "kind": spec.kind, "detail": detail},
                source="notifications",
                actor="system",
            )
        except Exception:  # noqa: BLE001 - meta emission is best-effort
            pass


# -- Senders ---------------------------------------------------------------


def _format_text(event: Event) -> str:
    """Plain-text rendering used by Slack/Teams/webhook fallbacks and email body."""
    icon = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🔥",
    }.get(str(event.severity), "ℹ️")
    lines = [f"{icon} {event.message or event.type}"]
    lines.append(f"Type: {event.type} · Severity: {event.severity} · Source: {event.source}")
    if event.data:
        details = ", ".join(f"{k}={v}" for k, v in list(event.data.items())[:10])
        lines.append(f"Details: {details}")
    lines.append(f"At: {event.timestamp.isoformat()}")
    return "\n".join(lines)


def _send_discord(service: NotificationService, spec: ChannelSpec, event: Event) -> None:
    payload = {
        "embeds": [
            {
                "title": (event.message or str(event.type))[:256],
                "description": _format_text(event)[:4000],
                "color": _SEVERITY_COLOR.get(str(event.severity), 0x6366F1),
            }
        ]
    }
    service._http_post(spec.target, json=payload, timeout=service.timeout)


def _send_slack(service: NotificationService, spec: ChannelSpec, event: Event) -> None:
    # Slack incoming webhooks accept {"text": ...}; blocks add severity color.
    payload = {
        "text": _format_text(event),
        "attachments": [
            {
                "color": f"#{_SEVERITY_COLOR.get(str(event.severity), 0x6366F1):06x}",
                "text": event.message or str(event.type),
            }
        ],
    }
    service._http_post(spec.target, json=payload, timeout=service.timeout)


def _send_teams(service: NotificationService, spec: ChannelSpec, event: Event) -> None:
    # Microsoft Teams "MessageCard" connector format.
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": f"{_SEVERITY_COLOR.get(str(event.severity), 0x6366F1):06x}",
        "summary": (event.message or str(event.type))[:200],
        "title": event.message or str(event.type),
        "text": _format_text(event).replace("\n", "  \n"),
    }
    service._http_post(spec.target, json=payload, timeout=service.timeout)


def _send_webhook(service: NotificationService, spec: ChannelSpec, event: Event) -> None:
    # Generic webhook: deliver the full structured event for downstream automation.
    service._http_post(spec.target, json=event.to_dict(), timeout=service.timeout)


def _send_email(service: NotificationService, spec: ChannelSpec, event: Event) -> None:
    options = spec.options
    host = str(options.get("smtp_host", ""))
    if not host:
        raise ValueError("email channel requires options.smtp_host")
    port = int(options.get("smtp_port", 587))
    username = str(options.get("smtp_username", ""))
    password = str(options.get("smtp_password", ""))
    use_tls = bool(options.get("use_tls", True))
    sender = str(options.get("from_address") or username or "onshape-export-manager@localhost")
    recipients = [addr.strip() for addr in spec.target.split(",") if addr.strip()]
    if not recipients:
        raise ValueError("email channel requires at least one recipient in target")

    message = EmailMessage()
    message["Subject"] = f"[Onshape Export] {event.message or event.type}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(_format_text(event))

    with smtplib.SMTP(host, port, timeout=service.timeout) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


SENDERS: dict[str, Callable[["NotificationService", ChannelSpec, Event], None]] = {
    "discord": _send_discord,
    "slack": _send_slack,
    "teams": _send_teams,
    "webhook": _send_webhook,
    "email": _send_email,
}


def _default_http_post(url: str, *, json: dict[str, Any], timeout: float) -> Any:
    """Default HTTP POST using the requests library, raising on non-2xx."""
    import requests

    response = requests.post(url, json=json, timeout=timeout)
    response.raise_for_status()
    return response


# Delivery-result events the service itself emits. These must never be fed back
# into delivery (see NotificationService._enqueue) or they would loop forever.
_META_EVENT_TYPES: frozenset[EventType] = frozenset(
    {EventType.NOTIFICATION_SENT, EventType.NOTIFICATION_FAILED}
)

# Sentinel pushed onto the delivery queue to wake the worker for shutdown.
_SENTINEL: Event = Event(type=EventType.CUSTOM, message="__notifications_stop__")
