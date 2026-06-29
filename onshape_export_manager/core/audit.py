"""Audit log and telemetry persistence — durable storage for the event bus.

:class:`AuditService` subscribes to an :class:`~onshape_export_manager.core.events.EventBus`
and writes every published :class:`~onshape_export_manager.core.events.Event` to
the ``events`` table (schema v3). It also exposes query helpers so the web layer
can serve a filterable audit trail and recent-activity feed without touching SQL.

:class:`TelemetryStore` records time-series samples (CPU%, queue depth, export
throughput, …) to the ``telemetry`` table and reads them back for historical
charts. It is intentionally separate from the audit log: events are discrete
facts; telemetry is sampled numbers.

Both are thread-safe by virtue of the underlying :class:`Database` opening a
fresh connection per call, so the worker thread and web loop can write freely.
Retention is enforced lazily (every N writes) to avoid unbounded growth on a
Raspberry Pi.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from onshape_export_manager.core.database import Database, EventRecord, TelemetryPoint
from onshape_export_manager.core.events import (
    Event,
    EventBus,
    EventCategory,
    EventSeverity,
)
from onshape_export_manager.core.logger import AUDIT_LOGGER, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditService:
    """Persists events from the bus into the database and queries them back."""

    def __init__(
        self,
        database: Database,
        event_bus: EventBus,
        *,
        retention_days: int = 90,
        max_rows: int = 50_000,
        purge_every: int = 500,
    ) -> None:
        self.database = database
        self.event_bus = event_bus
        self.retention_days = retention_days
        self.max_rows = max_rows
        self.purge_every = max(1, purge_every)
        self.logger = get_logger(AUDIT_LOGGER)
        self._token: int | None = None
        self._writes_since_purge = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        """Subscribe to the bus so all future events are persisted (idempotent)."""
        if self._token is not None:
            return
        self._token = self.event_bus.subscribe(self._on_event)
        self.logger.info("Audit service subscribed to event bus")

    def stop(self) -> None:
        """Unsubscribe from the bus."""
        if self._token is not None:
            self.event_bus.unsubscribe(self._token)
            self._token = None

    def _on_event(self, event: Event) -> None:
        """Bus subscriber: write the event to durable storage."""
        try:
            self.record(event)
        except Exception:  # noqa: BLE001 - audit must never break the publisher
            self.logger.exception("Failed to persist event %s", event.type)

    def record(self, event: Event) -> int:
        """Persist a single event and enforce retention periodically."""
        record_id = self.database.add_event(
            EventRecord(
                event_id=event.id,
                timestamp=event.timestamp,
                type=str(event.type),
                category=str(event.category),
                severity=str(event.severity),
                message=event.message,
                source=event.source,
                actor=event.actor,
                data=event.data,
            )
        )
        self._maybe_purge()
        return record_id

    def _maybe_purge(self) -> None:
        with self._lock:
            self._writes_since_purge += 1
            if self._writes_since_purge < self.purge_every:
                return
            self._writes_since_purge = 0
        try:
            removed = self.database.purge_events(
                keep_days=self.retention_days, max_rows=self.max_rows
            )
            if removed:
                self.logger.info("Purged %s old audit events", removed)
        except Exception:  # noqa: BLE001 - retention is best-effort
            self.logger.exception("Audit retention purge failed")

    # -- Queries -----------------------------------------------------------

    def list_events(
        self,
        *,
        category: str | None = None,
        severity: str | None = None,
        event_type: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return persisted events as JSON-serializable dicts, newest first."""
        records = self.database.list_events(
            category=category,
            severity=severity,
            event_type=event_type,
            actor=actor,
            since=since,
            limit=limit,
            offset=offset,
        )
        return [serialize_event_record(record) for record in records]

    def summary(self) -> dict[str, Any]:
        """Return counts useful for dashboards (totals + by-severity warnings)."""
        return {
            "total": self.database.count_events(),
            "warnings": self.database.count_events(severity=str(EventSeverity.WARNING)),
            "errors": self.database.count_events(severity=str(EventSeverity.ERROR)),
            "critical": self.database.count_events(severity=str(EventSeverity.CRITICAL)),
        }

    def categories(self) -> list[str]:
        """Return the set of known event categories for UI filter dropdowns."""
        return [str(category) for category in EventCategory]


class TelemetryStore:
    """Records and reads back time-series metrics for historical charts."""

    def __init__(self, database: Database, *, retention_days: int = 30) -> None:
        self.database = database
        self.retention_days = retention_days
        self.logger = get_logger(AUDIT_LOGGER)
        self._writes = 0
        self._lock = threading.Lock()

    def record(self, metric: str, value: float, *, labels: dict[str, Any] | None = None) -> None:
        """Record one telemetry sample with an automatic UTC timestamp."""
        self.database.add_telemetry(
            TelemetryPoint(metric=metric, value=float(value), labels=labels or {})
        )
        self._maybe_purge()

    def record_many(self, samples: dict[str, float], *, labels: dict[str, Any] | None = None) -> None:
        """Record several metrics sharing one timestamp in a single transaction."""
        now = _utc_now()
        points = [
            TelemetryPoint(metric=metric, value=float(value), timestamp=now, labels=labels or {})
            for metric, value in samples.items()
        ]
        self.database.add_telemetry_batch(points)
        self._maybe_purge()

    def _maybe_purge(self) -> None:
        with self._lock:
            self._writes += 1
            if self._writes < 200:
                return
            self._writes = 0
        try:
            self.database.purge_telemetry(keep_days=self.retention_days)
        except Exception:  # noqa: BLE001 - retention is best-effort
            self.logger.exception("Telemetry retention purge failed")

    def series(self, metric: str, *, since: datetime | None = None, limit: int = 1000) -> dict[str, Any]:
        """Return a metric's samples as parallel timestamp/value arrays for charts."""
        points = self.database.query_telemetry(metric, since=since, limit=limit)
        return {
            "metric": metric,
            "timestamps": [p.timestamp.astimezone(timezone.utc).isoformat() for p in points],
            "values": [p.value for p in points],
            "count": len(points),
        }

    def metrics(self) -> list[str]:
        """Return the list of metric names that have recorded samples."""
        return self.database.distinct_metrics()


def serialize_event_record(record: EventRecord) -> dict[str, Any]:
    """Convert a stored :class:`EventRecord` into a JSON-serializable dict."""
    return {
        "id": record.id,
        "event_id": record.event_id,
        "timestamp": record.timestamp.astimezone(timezone.utc).isoformat(),
        "type": record.type,
        "category": record.category,
        "severity": record.severity,
        "message": record.message,
        "source": record.source,
        "actor": record.actor,
        "data": record.data,
    }
