"""SQLite database layer for history, queue, scheduler jobs, and state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from onshape_export_manager.core.jobs import JobStatus


SCHEMA_VERSION = 3


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def serialize_dt(value: datetime | None) -> str | None:
    """Serialize an optional datetime for SQLite."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    """Parse an optional SQLite datetime string."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


def to_json(value: Any) -> str:
    """Serialize a JSON payload for SQLite storage."""
    return json.dumps(value, sort_keys=True, default=str)


def from_json(value: str | None, default: Any) -> Any:
    """Deserialize a JSON payload from SQLite storage."""
    if value is None:
        return default
    return json.loads(value)


@dataclass(slots=True)
class ExportHistoryEntry:
    """A completed or failed export run stored in history."""

    account_name: str
    label_name: str
    export_profile: str
    exported_files: list[str]
    duration_seconds: float
    success: bool
    failures: list[str]
    retry_count: int = 0
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class QueueEntry:
    """A queued export job."""

    label_name: str
    profile_name: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    next_run_at: datetime | None = None
    last_error: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class SchedulerJobEntry:
    """A configured scheduled export job."""

    name: str
    label_name: str
    interval: str
    id: str = field(default_factory=lambda: str(uuid4()))
    enabled: bool = True
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class EventRecord:
    """A persisted event / audit-log entry (schema v3).

    Mirrors :class:`onshape_export_manager.core.events.Event` but is storage-only
    so the database layer has no dependency on the event bus.
    """

    type: str
    category: str
    severity: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    actor: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True)
class TelemetryPoint:
    """A single time-series metric sample (schema v3)."""

    metric: str
    value: float
    timestamp: datetime = field(default_factory=utc_now)
    labels: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass(slots=True)
class Database:
    """Represents the application SQLite database."""

    path: Path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a SQLite connection with app defaults."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Initialize or migrate the database schema."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            self._ensure_migration_table(connection)
            applied = self._applied_migrations(connection)
            migrations = {
                1: self._apply_schema_v1,
                2: self._apply_schema_v2,
                3: self._apply_schema_v3,
            }
            for version in sorted(migrations):
                if version not in applied:
                    migrations[version](connection)
                    self._record_migration(connection, version)
            self.set_state("schema_version", str(SCHEMA_VERSION), connection=connection)

    def schema_version(self) -> int:
        """Return the latest applied schema version."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
            return int(row["version"] or 0)

    def add_export_history(self, entry: ExportHistoryEntry) -> int:
        """Insert an export history entry and return its database id."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO export_history (
                    started_at, finished_at, account_name, label_name,
                    export_profile, exported_files_json, duration_seconds,
                    success, failures_json, retry_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    serialize_dt(entry.started_at),
                    serialize_dt(entry.finished_at),
                    entry.account_name,
                    entry.label_name,
                    entry.export_profile,
                    to_json(entry.exported_files),
                    entry.duration_seconds,
                    int(entry.success),
                    to_json(entry.failures),
                    entry.retry_count,
                    serialize_dt(entry.created_at),
                ),
            )
            return int(cursor.lastrowid)

    def list_export_history(
        self,
        *,
        label_name: str | None = None,
        account_name: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[ExportHistoryEntry]:
        """List export history with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if label_name is not None:
            clauses.append("label_name = ?")
            params.append(label_name)
        if account_name is not None:
            clauses.append("account_name = ?")
            params.append(account_name)
        if success is not None:
            clauses.append("success = ?")
            params.append(int(success))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM export_history
                {where}
                ORDER BY started_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [history_from_row(row) for row in rows]

    def enqueue(self, entry: QueueEntry) -> str:
        """Insert or replace a queue entry and return its id."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO export_queue (
                    id, label_name, profile_name, payload_json, status,
                    retry_count, next_run_at, last_error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label_name = excluded.label_name,
                    profile_name = excluded.profile_name,
                    payload_json = excluded.payload_json,
                    status = excluded.status,
                    retry_count = excluded.retry_count,
                    next_run_at = excluded.next_run_at,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    entry.id,
                    entry.label_name,
                    entry.profile_name,
                    to_json(entry.payload),
                    entry.status.value,
                    entry.retry_count,
                    serialize_dt(entry.next_run_at),
                    entry.last_error,
                    serialize_dt(entry.created_at),
                    serialize_dt(entry.updated_at),
                ),
            )
            return entry.id

    def update_queue_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        retry_count: int | None = None,
        last_error: str | None = None,
        next_run_at: datetime | None = None,
    ) -> None:
        """Update queue status and retry metadata."""
        assignments = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status.value, serialize_dt(utc_now())]
        if retry_count is not None:
            assignments.append("retry_count = ?")
            params.append(retry_count)
        if last_error is not None:
            assignments.append("last_error = ?")
            params.append(last_error)
        if next_run_at is not None:
            assignments.append("next_run_at = ?")
            params.append(serialize_dt(next_run_at))
        params.append(job_id)

        with self.connect() as connection:
            connection.execute(
                f"UPDATE export_queue SET {', '.join(assignments)} WHERE id = ?",
                params,
            )

    def get_queue_entry(self, job_id: str) -> QueueEntry | None:
        """Return one queue entry by id."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM export_queue WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return queue_from_row(row)

    def list_queue(
        self,
        *,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[QueueEntry]:
        """List queued export jobs."""
        where = ""
        params: list[Any] = []
        if status is not None:
            where = "WHERE status = ?"
            params.append(status.value)
        params.append(limit)

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM export_queue
                {where}
                ORDER BY created_at ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [queue_from_row(row) for row in rows]

    def list_due_queue(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[QueueEntry]:
        """List pending queue jobs ready to run."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM export_queue
                WHERE status = ?
                  AND (next_run_at IS NULL OR next_run_at <= ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (JobStatus.PENDING.value, serialize_dt(now), limit),
            ).fetchall()
        return [queue_from_row(row) for row in rows]

    def upsert_scheduler_job(self, entry: SchedulerJobEntry) -> str:
        """Insert or update a scheduler job."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO scheduler_jobs (
                    id, name, label_name, interval, enabled, next_run_at,
                    last_run_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    label_name = excluded.label_name,
                    interval = excluded.interval,
                    enabled = excluded.enabled,
                    next_run_at = excluded.next_run_at,
                    last_run_at = excluded.last_run_at,
                    updated_at = excluded.updated_at
                """,
                (
                    entry.id,
                    entry.name,
                    entry.label_name,
                    entry.interval,
                    int(entry.enabled),
                    serialize_dt(entry.next_run_at),
                    serialize_dt(entry.last_run_at),
                    serialize_dt(entry.created_at),
                    serialize_dt(entry.updated_at),
                ),
            )
            return entry.id

    def list_scheduler_jobs(self, *, enabled: bool | None = None) -> list[SchedulerJobEntry]:
        """List scheduler jobs."""
        where = ""
        params: list[Any] = []
        if enabled is not None:
            where = "WHERE enabled = ?"
            params.append(int(enabled))

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM scheduler_jobs
                {where}
                ORDER BY name ASC
                """,
                params,
            ).fetchall()
        return [scheduler_job_from_row(row) for row in rows]

    def set_state(
        self,
        key: str,
        value: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Set an application state value."""
        now = serialize_dt(utc_now())
        params = (key, value, now)
        statement = """
            INSERT INTO application_state (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """
        if connection is not None:
            connection.execute(statement, params)
            return
        with self.connect() as own_connection:
            own_connection.execute(statement, params)

    def get_state(self, key: str, default: str | None = None) -> str | None:
        """Read an application state value."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM application_state WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    # -- Events / audit log (schema v3) ------------------------------------

    def add_event(self, event: EventRecord) -> int:
        """Persist an event/audit record and return its database id."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_id, timestamp, type, category, severity,
                    message, source, actor, data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    event.event_id,
                    serialize_dt(event.timestamp),
                    event.type,
                    event.category,
                    event.severity,
                    event.message,
                    event.source,
                    event.actor,
                    to_json(event.data),
                ),
            )
            return int(cursor.lastrowid)

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
    ) -> list[EventRecord]:
        """List events newest-first with optional filters and pagination."""
        clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity)
        if event_type is not None:
            clauses.append("type = ?")
            params.append(event_type)
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(serialize_dt(since))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM events
                {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return [event_from_row(row) for row in rows]

    def count_events(self, *, category: str | None = None, severity: str | None = None) -> int:
        """Count events with optional category/severity filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS n FROM events {where}", params
            ).fetchone()
        return int(row["n"])

    def purge_events(self, *, keep_days: int | None = None, max_rows: int | None = None) -> int:
        """Delete old events by age and/or row cap. Returns rows removed."""
        removed = 0
        with self.connect() as connection:
            if keep_days is not None:
                cutoff = serialize_dt(utc_now() - timedelta(days=keep_days))
                cursor = connection.execute(
                    "DELETE FROM events WHERE timestamp < ?", (cutoff,)
                )
                removed += cursor.rowcount or 0
            if max_rows is not None:
                cursor = connection.execute(
                    """
                    DELETE FROM events WHERE id NOT IN (
                        SELECT id FROM events ORDER BY id DESC LIMIT ?
                    )
                    """,
                    (max_rows,),
                )
                removed += cursor.rowcount or 0
        return removed

    # -- Telemetry time series (schema v3) ---------------------------------

    def add_telemetry(self, point: TelemetryPoint) -> int:
        """Record a single telemetry sample and return its database id."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry (metric, value, timestamp, labels_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    point.metric,
                    float(point.value),
                    serialize_dt(point.timestamp),
                    to_json(point.labels),
                ),
            )
            return int(cursor.lastrowid)

    def add_telemetry_batch(self, points: list[TelemetryPoint]) -> int:
        """Record many telemetry samples in one transaction. Returns count."""
        if not points:
            return 0
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO telemetry (metric, value, timestamp, labels_json)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        point.metric,
                        float(point.value),
                        serialize_dt(point.timestamp),
                        to_json(point.labels),
                    )
                    for point in points
                ],
            )
        return len(points)

    def query_telemetry(
        self,
        metric: str,
        *,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[TelemetryPoint]:
        """Return samples for *metric*, oldest-first, optionally since a time."""
        clauses = ["metric = ?"]
        params: list[Any] = [metric]
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(serialize_dt(since))
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM (
                    SELECT * FROM telemetry
                    WHERE {' AND '.join(clauses)}
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id ASC
                """,
                params,
            ).fetchall()
        return [telemetry_from_row(row) for row in rows]

    def distinct_metrics(self) -> list[str]:
        """Return the set of metric names that have telemetry samples."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT metric FROM telemetry ORDER BY metric ASC"
            ).fetchall()
        return [str(row["metric"]) for row in rows]

    def purge_telemetry(self, *, keep_days: int) -> int:
        """Delete telemetry samples older than *keep_days*. Returns rows removed."""
        cutoff = serialize_dt(utc_now() - timedelta(days=keep_days))
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM telemetry WHERE timestamp < ?", (cutoff,)
            )
            return cursor.rowcount or 0

    def status(self) -> dict[str, int]:
        """Return schema version and table counts."""
        with self.connect() as connection:
            counts = {
                "schema_version": self.schema_version(),
                "export_history": count_rows(connection, "export_history"),
                "export_queue": count_rows(connection, "export_queue"),
                "scheduler_jobs": count_rows(connection, "scheduler_jobs"),
                "application_state": count_rows(connection, "application_state"),
            }
            # Events/telemetry exist only after the v3 migration; guard for
            # databases mid-upgrade or older snapshots.
            if _table_exists(connection, "events"):
                counts["events"] = count_rows(connection, "events")
            if _table_exists(connection, "telemetry"):
                counts["telemetry"] = count_rows(connection, "telemetry")
            return counts

    def _ensure_migration_table(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

    def _applied_migrations(self, connection: sqlite3.Connection) -> set[int]:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
        return {int(row["version"]) for row in rows}

    def _record_migration(self, connection: sqlite3.Connection, version: int) -> None:
        connection.execute(
            """
            INSERT INTO schema_migrations (version, applied_at)
            VALUES (?, ?)
            """,
            (version, serialize_dt(utc_now())),
        )

    def _apply_schema_v1(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS export_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                account_name TEXT NOT NULL,
                label_name TEXT NOT NULL,
                export_profile TEXT NOT NULL,
                exported_files_json TEXT NOT NULL DEFAULT '[]',
                duration_seconds REAL NOT NULL DEFAULT 0,
                success INTEGER NOT NULL CHECK(success IN (0, 1)),
                failures_json TEXT NOT NULL DEFAULT '[]',
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_export_history_started_at
                ON export_history(started_at);
            CREATE INDEX IF NOT EXISTS idx_export_history_label
                ON export_history(label_name);
            CREATE INDEX IF NOT EXISTS idx_export_history_account
                ON export_history(account_name);
            CREATE INDEX IF NOT EXISTS idx_export_history_success
                ON export_history(success);

            CREATE TABLE IF NOT EXISTS export_queue (
                id TEXT PRIMARY KEY,
                label_name TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_run_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_export_queue_status
                ON export_queue(status);
            CREATE INDEX IF NOT EXISTS idx_export_queue_next_run_at
                ON export_queue(next_run_at);

            CREATE TABLE IF NOT EXISTS scheduler_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                label_name TEXT NOT NULL,
                interval TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
                next_run_at TEXT,
                last_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_enabled
                ON scheduler_jobs(enabled);
            CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_label
                ON scheduler_jobs(label_name);

            CREATE TABLE IF NOT EXISTS application_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    def _apply_schema_v2(self, connection: sqlite3.Connection) -> None:
        """Authentication: single-owner account and session tokens."""
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_owner (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0 CHECK(totp_enabled IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                remember INTEGER NOT NULL DEFAULT 0 CHECK(remember IN (0, 1)),
                user_agent TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires
                ON auth_sessions(expires_at);
            """
        )

    def _apply_schema_v3(self, connection: sqlite3.Connection) -> None:
        """Event/audit log and time-series telemetry (AI-ready foundation)."""
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'system',
                actor TEXT NOT NULL DEFAULT 'system',
                data_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
            CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
            CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);

            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                labels_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_telemetry_metric_time
                ON telemetry(metric, timestamp);
            CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp
                ON telemetry(timestamp);
            """
        )


def history_from_row(row: sqlite3.Row) -> ExportHistoryEntry:
    """Build an export history entry from a SQLite row."""
    return ExportHistoryEntry(
        id=int(row["id"]),
        started_at=parse_dt(row["started_at"]) or utc_now(),
        finished_at=parse_dt(row["finished_at"]),
        account_name=str(row["account_name"]),
        label_name=str(row["label_name"]),
        export_profile=str(row["export_profile"]),
        exported_files=list(from_json(row["exported_files_json"], [])),
        duration_seconds=float(row["duration_seconds"]),
        success=bool(row["success"]),
        failures=list(from_json(row["failures_json"], [])),
        retry_count=int(row["retry_count"]),
        created_at=parse_dt(row["created_at"]) or utc_now(),
    )


def queue_from_row(row: sqlite3.Row) -> QueueEntry:
    """Build a queue entry from a SQLite row."""
    return QueueEntry(
        id=str(row["id"]),
        label_name=str(row["label_name"]),
        profile_name=str(row["profile_name"]),
        payload=dict(from_json(row["payload_json"], {})),
        status=JobStatus(str(row["status"])),
        retry_count=int(row["retry_count"]),
        next_run_at=parse_dt(row["next_run_at"]),
        last_error=str(row["last_error"]),
        created_at=parse_dt(row["created_at"]) or utc_now(),
        updated_at=parse_dt(row["updated_at"]) or utc_now(),
    )


def scheduler_job_from_row(row: sqlite3.Row) -> SchedulerJobEntry:
    """Build a scheduler job entry from a SQLite row."""
    return SchedulerJobEntry(
        id=str(row["id"]),
        name=str(row["name"]),
        label_name=str(row["label_name"]),
        interval=str(row["interval"]),
        enabled=bool(row["enabled"]),
        next_run_at=parse_dt(row["next_run_at"]),
        last_run_at=parse_dt(row["last_run_at"]),
        created_at=parse_dt(row["created_at"]) or utc_now(),
        updated_at=parse_dt(row["updated_at"]) or utc_now(),
    )


def event_from_row(row: sqlite3.Row) -> EventRecord:
    """Build an event record from a SQLite row."""
    return EventRecord(
        id=int(row["id"]),
        event_id=str(row["event_id"]),
        timestamp=parse_dt(row["timestamp"]) or utc_now(),
        type=str(row["type"]),
        category=str(row["category"]),
        severity=str(row["severity"]),
        message=str(row["message"]),
        source=str(row["source"]),
        actor=str(row["actor"]),
        data=dict(from_json(row["data_json"], {})),
    )


def telemetry_from_row(row: sqlite3.Row) -> TelemetryPoint:
    """Build a telemetry point from a SQLite row."""
    return TelemetryPoint(
        id=int(row["id"]),
        metric=str(row["metric"]),
        value=float(row["value"]),
        timestamp=parse_dt(row["timestamp"]) or utc_now(),
        labels=dict(from_json(row["labels_json"], {})),
    )


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    """Count rows in a trusted internal table."""
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Return True if *table_name* exists in the SQLite schema."""
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None
