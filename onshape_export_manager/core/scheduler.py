"""Scheduler service for automatic exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from onshape_export_manager.core.database import Database, SchedulerJobEntry
from onshape_export_manager.core.logger import SCHEDULER_LOGGER, get_logger
from onshape_export_manager.core.models import LabelDefinition
from onshape_export_manager.core.queue_manager import QueueManager


class ScheduleInterval(StrEnum):
    """Supported scheduler intervals."""

    EVERY_15_MINUTES = "15_minutes"
    EVERY_30_MINUTES = "30_minutes"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class SchedulerTickResult:
    """Summary from one scheduler tick."""

    queued_job_ids: list[str]
    scheduler_job_ids: list[str]


class SchedulerService:
    """Coordinates scheduled export jobs and queue insertion."""

    def __init__(
        self,
        database: Database,
        queue_manager: QueueManager,
        *,
        now_fn=None,
    ) -> None:
        self.database = database
        self.queue_manager = queue_manager
        self._now_fn = now_fn or utc_now
        self._running = False
        self.logger = get_logger(SCHEDULER_LOGGER)

    def start(self) -> None:
        """Mark the scheduler as running.

        A real background loop is added when the web/TUI service process exists.
        """
        self._running = True
        self.database.set_state("scheduler.running", "true")
        self.logger.info("Scheduler started")

    def stop(self) -> None:
        """Mark the scheduler as stopped."""
        self._running = False
        self.database.set_state("scheduler.running", "false")
        self.logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._running

    def sync_labels(self, labels: list[LabelDefinition]) -> list[str]:
        """Create/update scheduler jobs from enabled labels with schedules."""
        now = self._now()
        job_ids: list[str] = []
        for label in labels:
            if not label.enabled or not label.scheduler:
                continue
            interval = parse_interval(label.scheduler)
            existing = find_scheduler_job(
                self.database.list_scheduler_jobs(),
                scheduler_job_name(label.friendly_name),
            )
            entry = SchedulerJobEntry(
                id=existing.id if existing else scheduler_job_id(label.friendly_name),
                name=scheduler_job_name(label.friendly_name),
                label_name=label.friendly_name,
                interval=interval.value,
                enabled=True,
                next_run_at=existing.next_run_at if existing and existing.next_run_at else now,
                last_run_at=existing.last_run_at if existing else None,
                created_at=existing.created_at if existing else now,
                updated_at=now,
            )
            job_ids.append(self.database.upsert_scheduler_job(entry))
            self.database.set_state(f"scheduler.profile.{entry.id}", label.export_profile)
            self.logger.info(
                "Synced scheduler job id=%s label=%s interval=%s profile=%s",
                entry.id,
                label.friendly_name,
                interval.value,
                label.export_profile,
            )
        return job_ids

    def due_jobs(self) -> list[SchedulerJobEntry]:
        """Return enabled scheduler jobs whose next run time has arrived."""
        now = self._now()
        return [
            job
            for job in self.database.list_scheduler_jobs(enabled=True)
            if job.next_run_at is None or normalize_datetime(job.next_run_at) <= now
        ]

    def tick(self) -> SchedulerTickResult:
        """Queue export work for due scheduler jobs and advance their next run."""
        now = self._now()
        queued_job_ids: list[str] = []
        scheduler_job_ids: list[str] = []
        for job in self.due_jobs():
            interval = parse_interval(job.interval)
            start_at = job.last_run_at or previous_window_start(now, interval)
            profile_name = self.database.get_state(f"scheduler.profile.{job.id}", "") or ""
            payload = {
                "label_name": job.label_name,
                "profile_name": profile_name,
                "start_iso": normalize_datetime(start_at).isoformat(),
                "end_iso": now.isoformat(),
                "scheduler_job_id": job.id,
            }
            queued_id = self.queue_manager.enqueue(
                label_name=job.label_name,
                profile_name=profile_name,
                payload=payload,
                reason="scheduled",
            )
            queued_job_ids.append(queued_id)
            scheduler_job_ids.append(job.id)
            self.logger.info(
                "Queued scheduled export scheduler_job_id=%s queue_job_id=%s label=%s",
                job.id,
                queued_id,
                job.label_name,
            )
            updated = SchedulerJobEntry(
                id=job.id,
                name=job.name,
                label_name=job.label_name,
                interval=job.interval,
                enabled=job.enabled,
                next_run_at=next_run_after(now, interval),
                last_run_at=now,
                created_at=job.created_at,
                updated_at=now,
            )
            self.database.upsert_scheduler_job(updated)
        return SchedulerTickResult(
            queued_job_ids=queued_job_ids,
            scheduler_job_ids=scheduler_job_ids,
        )

    def _now(self) -> datetime:
        return normalize_datetime(self._now_fn())


def parse_interval(value: str | ScheduleInterval) -> ScheduleInterval:
    """Parse user/config interval strings."""
    if isinstance(value, ScheduleInterval):
        return value
    normalized = value.strip().lower().replace("every_", "")
    aliases = {
        "15_minutes": ScheduleInterval.EVERY_15_MINUTES,
        "15 minutes": ScheduleInterval.EVERY_15_MINUTES,
        "30_minutes": ScheduleInterval.EVERY_30_MINUTES,
        "30 minutes": ScheduleInterval.EVERY_30_MINUTES,
        "hour": ScheduleInterval.HOURLY,
        "hourly": ScheduleInterval.HOURLY,
        "day": ScheduleInterval.DAILY,
        "daily": ScheduleInterval.DAILY,
        "week": ScheduleInterval.WEEKLY,
        "weekly": ScheduleInterval.WEEKLY,
        "month": ScheduleInterval.MONTHLY,
        "monthly": ScheduleInterval.MONTHLY,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported schedule interval: {value}") from exc


def interval_delta(interval: ScheduleInterval) -> timedelta:
    """Return fixed interval duration."""
    if interval == ScheduleInterval.EVERY_15_MINUTES:
        return timedelta(minutes=15)
    if interval == ScheduleInterval.EVERY_30_MINUTES:
        return timedelta(minutes=30)
    if interval == ScheduleInterval.HOURLY:
        return timedelta(hours=1)
    if interval == ScheduleInterval.DAILY:
        return timedelta(days=1)
    if interval == ScheduleInterval.WEEKLY:
        return timedelta(days=7)
    if interval == ScheduleInterval.MONTHLY:
        return timedelta(days=30)
    raise ValueError(f"Unsupported schedule interval: {interval}")


def next_run_after(value: datetime, interval: ScheduleInterval) -> datetime:
    """Compute the next run time after value."""
    return normalize_datetime(value) + interval_delta(interval)


def previous_window_start(value: datetime, interval: ScheduleInterval) -> datetime:
    """Compute the first-run export window start."""
    return normalize_datetime(value) - interval_delta(interval)


def scheduler_job_name(label_name: str) -> str:
    return f"{label_name} export"


def scheduler_job_id(label_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in label_name.lower()).strip("-")
    return f"schedule-{safe or 'label'}"


def find_scheduler_job(
    jobs: list[SchedulerJobEntry],
    name: str,
) -> SchedulerJobEntry | None:
    for job in jobs:
        if job.name == name:
            return job
    return None


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
