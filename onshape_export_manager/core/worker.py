"""Background export worker.

This is the *pump* that the rest of the system was already built around. The
:class:`~onshape_export_manager.core.queue_manager.QueueManager` and
:class:`~onshape_export_manager.core.scheduler.SchedulerService` provide every
primitive needed to schedule and drain export work, but nothing drove them in a
long-running process. :class:`BackgroundWorker` ties them together:

* On each tick it advances the scheduler (enqueuing due scheduled exports) and
  then claims and runs due queued jobs through the existing
  :class:`~onshape_export_manager.core.export_engine.ExportEngine`.
* Completion, retry, and permanent-failure bookkeeping is delegated back to the
  :class:`QueueManager` so retry/backoff semantics stay in one place.
* It runs on a daemon thread with its own asyncio loop, so it integrates with
  the FastAPI/uvicorn process without blocking the request event loop, and runs
  equally well under the CLI or in tests via :meth:`run_once`.

State (running flag, last tick time, counters, last error) is mirrored into the
``application_state`` table via :meth:`Database.set_state` so the dashboard can
report worker health and survive restarts.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from onshape_export_manager.core.database import QueueEntry
from onshape_export_manager.core.events import EventSeverity, EventType
from onshape_export_manager.core.logger import WORKER_LOGGER, get_logger
from onshape_export_manager.core.models import ExportJobRequest

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.app import Application


# State keys persisted in the application_state table.
STATE_RUNNING = "worker.running"
STATE_LAST_TICK = "worker.last_tick_at"
STATE_LAST_ERROR = "worker.last_error"
STATE_PROCESSED = "worker.jobs_processed"
STATE_FAILED = "worker.jobs_failed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class WorkerStatus:
    """Thread-safe snapshot of the worker's runtime state."""

    running: bool = False
    enabled: bool = False
    poll_interval_seconds: float = 5.0
    last_tick_at: str | None = None
    last_job_at: str | None = None
    last_error: str = ""
    jobs_processed: int = 0
    jobs_failed: int = 0
    active_job_id: str | None = None
    active_label: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class TickResult:
    """Outcome of a single worker tick (one scheduler advance + queue drain)."""

    scheduled_enqueued: int = 0
    jobs_run: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    errors: list[str] = field(default_factory=list)


class BackgroundWorker:
    """Drives scheduled and queued exports in a background thread.

    Parameters
    ----------
    application:
        The shared :class:`~onshape_export_manager.app.Application` container.
        The worker reads ``queue_manager``, ``scheduler``, ``database``, and
        ``config_manager`` from it and builds an export engine on demand.
    poll_interval_seconds:
        How long to sleep between ticks when idle.
    max_jobs_per_tick:
        Safety cap so a large backlog cannot starve the scheduler tick.
    """

    def __init__(
        self,
        application: "Application",
        *,
        poll_interval_seconds: float = 5.0,
        max_jobs_per_tick: int = 25,
    ) -> None:
        self.application = application
        self.database = application.database
        self.poll_interval_seconds = max(0.5, float(poll_interval_seconds))
        self.max_jobs_per_tick = max(1, int(max_jobs_per_tick))
        self.logger = get_logger(WORKER_LOGGER)

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._status = WorkerStatus(poll_interval_seconds=self.poll_interval_seconds)

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start the background worker thread (idempotent)."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if self.application.queue_manager is None:
                self.logger.warning("Worker not started: queue manager unavailable")
                return
            self._stop.clear()
            self._status.running = True
            self._status.enabled = True
            self._status.last_error = ""
            thread = threading.Thread(
                target=self._run_loop,
                name="oem-export-worker",
                daemon=True,
            )
            self._thread = thread
        self.database.set_state(STATE_RUNNING, "true")
        if self.application.scheduler is not None:
            self._sync_scheduler_jobs()
            self.application.scheduler.start()
        thread.start()
        self.logger.info(
            "Background worker started (poll=%ss, max_jobs_per_tick=%s)",
            self.poll_interval_seconds,
            self.max_jobs_per_tick,
        )
        self._emit(
            EventType.WORKER_STARTED,
            "Background export worker started",
            data={"poll_interval_seconds": self.poll_interval_seconds},
        )

    def stop(self, *, timeout: float = 10.0) -> None:
        """Signal the worker to stop and wait for the thread to exit."""
        with self._lock:
            thread = self._thread
            self._status.running = False
            self._status.enabled = False
        self._stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        with self._lock:
            self._thread = None
        self.database.set_state(STATE_RUNNING, "false")
        if self.application.scheduler is not None:
            self.application.scheduler.stop()
        self.logger.info("Background worker stopped")
        self._emit(EventType.WORKER_STOPPED, "Background export worker stopped")

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def status(self) -> WorkerStatus:
        """Return a copy of the current worker status."""
        with self._lock:
            snapshot = WorkerStatus(**self._status.to_dict())  # type: ignore[arg-type]
        snapshot.running = self.running
        return snapshot

    # -- Loop --------------------------------------------------------------

    def _run_loop(self) -> None:
        """Thread target: own asyncio loop, tick until stopped."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while not self._stop.is_set():
                try:
                    loop.run_until_complete(self._tick_async())
                except Exception as exc:  # noqa: BLE001 - keep the loop alive
                    self.logger.exception("Worker tick crashed: %s", exc)
                    self._record_error(str(exc))
                # Interruptible sleep so stop() returns promptly.
                self._stop.wait(self.poll_interval_seconds)
        finally:
            loop.close()

    def run_once(self) -> TickResult:
        """Run a single tick synchronously. Used by the CLI and tests."""
        return asyncio.run(self._tick_async())

    async def _tick_async(self) -> TickResult:
        result = TickResult()
        result.scheduled_enqueued = self._advance_scheduler()
        await self._drain_queue(result)
        with self._lock:
            self._status.last_tick_at = _utc_now().isoformat()
        self.database.set_state(STATE_LAST_TICK, _utc_now().isoformat())
        queue_depth = self._queue_depth()
        # Only record telemetry and emit a tick event when work happened, so the
        # audit log, live feed, and (crucially on a Pi's SD card) the telemetry
        # table are not flooded with idle heartbeats every poll interval.
        if result.jobs_run or result.scheduled_enqueued or queue_depth:
            self._record_tick_telemetry(result, queue_depth)
        if result.jobs_run or result.scheduled_enqueued:
            self._emit(
                EventType.WORKER_TICK,
                f"Worker tick: ran {result.jobs_run}, scheduled {result.scheduled_enqueued}",
                severity=EventSeverity.DEBUG,
                data={
                    "jobs_run": result.jobs_run,
                    "jobs_succeeded": result.jobs_succeeded,
                    "jobs_failed": result.jobs_failed,
                    "scheduled_enqueued": result.scheduled_enqueued,
                    "queue_depth": queue_depth,
                },
            )
        return result

    def _queue_depth(self) -> int:
        """Return the number of pending jobs, or 0 if the queue is unavailable."""
        queue = self.application.queue_manager
        if queue is None:
            return 0
        try:
            return queue.stats().pending
        except Exception:  # noqa: BLE001 - depth is informational only
            return 0

    # -- Scheduler ---------------------------------------------------------

    def _sync_scheduler_jobs(self) -> None:
        """Rebuild scheduler jobs from the current labels configuration."""
        scheduler = self.application.scheduler
        if scheduler is None:
            return
        try:
            config = self.application.config_manager.load()
            labels = config.runtime_labels(self.application.paths.package_dir)
            scheduler.sync_labels(labels)
        except Exception as exc:  # noqa: BLE001 - config may be incomplete
            self.logger.warning("Scheduler sync skipped: %s", exc)

    def _advance_scheduler(self) -> int:
        scheduler = self.application.scheduler
        if scheduler is None or not scheduler.running:
            return 0
        try:
            tick = scheduler.tick()
            return len(tick.queued_job_ids)
        except Exception as exc:  # noqa: BLE001 - never let scheduling kill the loop
            self.logger.warning("Scheduler tick failed: %s", exc)
            return 0

    # -- Queue draining ----------------------------------------------------

    async def _drain_queue(self, result: TickResult) -> None:
        queue = self.application.queue_manager
        if queue is None:
            return
        for _ in range(self.max_jobs_per_tick):
            if self._stop.is_set():
                break
            job = queue.claim_next()
            if job is None:
                break
            result.jobs_run += 1
            await self._run_job(job, result)

    async def _run_job(self, job: QueueEntry, result: TickResult) -> None:
        queue = self.application.queue_manager
        assert queue is not None
        with self._lock:
            self._status.active_job_id = job.id
            self._status.active_label = job.label_name
        self.logger.info(
            "Running queued export id=%s label=%s profile=%s",
            job.id,
            job.label_name,
            job.profile_name,
        )
        job_data = {
            "job_id": job.id,
            "label": job.label_name,
            "profile": job.profile_name,
            "retry_count": job.retry_count,
        }
        self._emit(
            EventType.JOB_STARTED,
            f"Export started for {job.label_name}",
            data=job_data,
        )
        started = _utc_now()
        try:
            request = self._build_request(job)
            engine = self.application.create_export_engine(resolve_env=True)
            export = await engine.run_manual_export(request)
            duration = (_utc_now() - started).total_seconds()
            if export.success:
                queue.mark_completed(job.id)
                result.jobs_succeeded += 1
                self._record_success()
                self._emit(
                    EventType.JOB_COMPLETED,
                    f"Export completed for {job.label_name}",
                    severity=EventSeverity.SUCCESS,
                    data={
                        **job_data,
                        "duration_seconds": round(duration, 2),
                        "files": len(export.exported_files),
                    },
                )
                self._record_job_telemetry(duration, len(export.exported_files), success=True)
            else:
                error = "; ".join(export.failed_items) or "export reported failure"
                queue.mark_failed(job.id, error[:500])
                result.jobs_failed += 1
                result.errors.append(error)
                self._record_error(error)
                self._emit(
                    EventType.JOB_FAILED,
                    f"Export failed for {job.label_name}",
                    severity=EventSeverity.ERROR,
                    data={**job_data, "error": error[:500], "duration_seconds": round(duration, 2)},
                )
                self._record_job_telemetry(duration, 0, success=False)
        except Exception as exc:  # noqa: BLE001 - failure is recorded, loop continues
            message = f"{type(exc).__name__}: {exc}"
            self.logger.exception("Queued export failed id=%s: %s", job.id, message)
            try:
                queue.mark_failed(job.id, message[:500])
            except Exception:  # noqa: BLE001 - job may have been deleted
                pass
            result.jobs_failed += 1
            result.errors.append(message)
            self._record_error(message)
            self._emit(
                EventType.JOB_FAILED,
                f"Export crashed for {job.label_name}",
                severity=EventSeverity.ERROR,
                data={**job_data, "error": message[:500]},
            )
        finally:
            with self._lock:
                self._status.active_job_id = None
                self._status.active_label = None
                self._status.last_job_at = _utc_now().isoformat()

    def _build_request(self, job: QueueEntry) -> ExportJobRequest:
        """Resolve a queue entry into an ExportJobRequest.

        Mirrors the CLI's resolution (:func:`cli.run_export_from_args`): labels
        and profiles come from validated runtime configuration, the export
        window from the job payload, and an optional destination override.
        """
        config = self.application.config_manager.load()
        labels = {
            label.friendly_name: label
            for label in config.runtime_labels(self.application.paths.package_dir)
            if label.enabled
        }
        label = labels.get(job.label_name)
        if label is None:
            raise ValueError(f"unknown or disabled label '{job.label_name}'")

        profiles = {
            profile.name: profile
            for profile in config.runtime_export_profiles()
            if profile.enabled
        }
        profile_name = job.profile_name or label.export_profile
        profile = profiles.get(profile_name)
        if profile is None:
            raise ValueError(f"unknown or disabled export profile '{profile_name}'")

        payload = job.payload or {}
        start_iso, end_iso = _export_window(payload)
        destination = None
        raw_destination = payload.get("destination")
        if raw_destination:
            destination = Path(str(raw_destination)).expanduser()

        return ExportJobRequest(
            label=label,
            profile=profile,
            start_iso=start_iso,
            end_iso=end_iso,
            destination=destination,
        )

    # -- Event bus & telemetry --------------------------------------------

    def _emit(
        self,
        event_type: EventType,
        message: str,
        *,
        severity: EventSeverity = EventSeverity.INFO,
        data: dict[str, object] | None = None,
    ) -> None:
        """Publish an event onto the shared bus if one is configured."""
        bus = getattr(self.application, "event_bus", None)
        if bus is None:
            return
        try:
            bus.emit(
                event_type,
                message,
                severity=severity,
                data=dict(data or {}),
                source="worker",
                actor="worker",
            )
        except Exception:  # noqa: BLE001 - event emission must never break the worker
            self.logger.exception("Failed to emit worker event %s", event_type)

    def _record_job_telemetry(self, duration: float, files: int, *, success: bool) -> None:
        """Record per-job telemetry (duration, file count, success flag)."""
        telemetry = getattr(self.application, "telemetry", None)
        if telemetry is None:
            return
        try:
            telemetry.record_many(
                {
                    "export.duration_seconds": float(duration),
                    "export.files": float(files),
                    "export.success": 1.0 if success else 0.0,
                }
            )
        except Exception:  # noqa: BLE001 - telemetry is best-effort
            self.logger.exception("Failed to record job telemetry")

    def _record_tick_telemetry(self, result: TickResult, queue_depth: int) -> None:
        """Record queue/throughput telemetry samples for historical charts."""
        telemetry = getattr(self.application, "telemetry", None)
        if telemetry is None:
            return
        try:
            telemetry.record_many(
                {
                    "queue.depth": float(queue_depth),
                    "worker.jobs_run": float(result.jobs_run),
                    "worker.jobs_failed": float(result.jobs_failed),
                }
            )
        except Exception:  # noqa: BLE001 - telemetry is best-effort
            self.logger.exception("Failed to record worker telemetry")

    # -- State bookkeeping -------------------------------------------------

    def _record_success(self) -> None:
        with self._lock:
            self._status.jobs_processed += 1
            self._status.last_error = ""
            processed = self._status.jobs_processed
        self.database.set_state(STATE_PROCESSED, str(processed))
        self.database.set_state(STATE_LAST_ERROR, "")

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._status.jobs_failed += 1
            self._status.last_error = message
            failed = self._status.jobs_failed
        self.database.set_state(STATE_FAILED, str(failed))
        self.database.set_state(STATE_LAST_ERROR, message[:500])


def _export_window(payload: dict[str, object]) -> tuple[str, str]:
    """Derive (start_iso, end_iso) from a queue payload with sane defaults."""
    from datetime import timedelta

    start = payload.get("start_iso")
    end = payload.get("end_iso")
    if isinstance(start, str) and isinstance(end, str) and start and end:
        return start, end
    now = _utc_now()
    if isinstance(end, str) and end:
        end_dt = _parse_iso(end) or now
    else:
        end_dt = now
    if isinstance(start, str) and start:
        start_dt = _parse_iso(start) or (end_dt - timedelta(days=1))
    else:
        start_dt = end_dt - timedelta(days=1)
    return start_dt.isoformat(), end_dt.isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None
