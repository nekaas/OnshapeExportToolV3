"""Export queue service with retry and backoff behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from onshape_export_manager.core.database import Database, QueueEntry, utc_now
from onshape_export_manager.core.jobs import JobStatus
from onshape_export_manager.core.logger import QUEUE_LOGGER, get_logger
from onshape_export_manager.core.retry import RetryPolicy


@dataclass(frozen=True, slots=True)
class QueueRetryPolicy(RetryPolicy):
    """Retry behavior for queued jobs."""


@dataclass(frozen=True, slots=True)
class QueueStats:
    """Queue counts by state."""

    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0

    @property
    def total(self) -> int:
        return self.pending + self.running + self.completed + self.failed + self.cancelled


class QueueManager:
    """Coordinates delayed and retryable export jobs."""

    def __init__(
        self,
        database: Database,
        *,
        retry_policy: QueueRetryPolicy | None = None,
        now_fn=utc_now,
    ) -> None:
        self.database = database
        self.retry_policy = retry_policy or QueueRetryPolicy()
        self._now_fn = now_fn
        self.logger = get_logger(QUEUE_LOGGER)

    def enqueue(
        self,
        *,
        label_name: str,
        profile_name: str,
        payload: dict[str, Any],
        reason: str = "",
        next_run_at: datetime | None = None,
    ) -> str:
        """Queue an export job."""
        job = QueueEntry(
            label_name=label_name,
            profile_name=profile_name,
            payload={**payload, "queue_reason": reason} if reason else dict(payload),
            next_run_at=normalize_datetime(next_run_at) if next_run_at else None,
        )
        job_id = self.database.enqueue(job)
        self.logger.info(
            "Queued export job id=%s label=%s profile=%s reason=%s",
            job_id,
            label_name,
            profile_name,
            reason,
        )
        return job_id

    def due_jobs(self, *, limit: int = 100) -> list[QueueEntry]:
        """Return pending jobs ready to run."""
        return self.database.list_due_queue(now=self._now(), limit=limit)

    def claim_next(self) -> QueueEntry | None:
        """Mark the oldest due pending job as running and return it."""
        due = self.due_jobs(limit=1)
        if not due:
            return None
        job = due[0]
        self.database.update_queue_status(job.id, JobStatus.RUNNING)
        self.logger.info("Claimed queue job id=%s", job.id)
        claimed = self.database.get_queue_entry(job.id)
        return claimed or job

    def mark_completed(self, job_id: str) -> None:
        """Mark a job complete."""
        self.database.update_queue_status(job_id, JobStatus.COMPLETED)
        self.logger.info("Completed queue job id=%s", job_id)

    def mark_failed(self, job_id: str, error: str) -> JobStatus:
        """Record failure and either retry later or mark permanently failed."""
        job = self.database.get_queue_entry(job_id)
        if job is None:
            raise KeyError(f"Unknown queue job: {job_id}")
        retry_count = job.retry_count + 1
        if retry_count >= self.retry_policy.max_attempts:
            self.database.update_queue_status(
                job_id,
                JobStatus.FAILED,
                retry_count=retry_count,
                last_error=error,
            )
            self.logger.error("Queue job permanently failed id=%s error=%s", job_id, error)
            return JobStatus.FAILED

        next_run_at = self._now() + self.retry_policy.delay_for_retry(retry_count)
        self.database.update_queue_status(
            job_id,
            JobStatus.PENDING,
            retry_count=retry_count,
            last_error=error,
            next_run_at=next_run_at,
        )
        self.logger.warning(
            "Queue job scheduled for retry id=%s retry_count=%s next_run_at=%s error=%s",
            job_id,
            retry_count,
            next_run_at.isoformat(),
            error,
        )
        return JobStatus.PENDING

    def cancel(self, job_id: str, reason: str = "cancelled") -> None:
        """Cancel a queued job."""
        self.database.update_queue_status(job_id, JobStatus.CANCELLED, last_error=reason)
        self.logger.info("Cancelled queue job id=%s reason=%s", job_id, reason)

    def requeue(self, job_id: str, *, next_run_at: datetime | None = None) -> None:
        """Move a failed/cancelled/running job back to pending."""
        self.database.update_queue_status(
            job_id,
            JobStatus.PENDING,
            last_error="",
            next_run_at=normalize_datetime(next_run_at) if next_run_at else self._now(),
        )

    def stats(self) -> QueueStats:
        """Return queue counts by status."""
        counts = {
            status: len(self.database.list_queue(status=status, limit=10_000))
            for status in JobStatus
        }
        return QueueStats(
            pending=counts[JobStatus.PENDING],
            running=counts[JobStatus.RUNNING],
            completed=counts[JobStatus.COMPLETED],
            failed=counts[JobStatus.FAILED],
            cancelled=counts[JobStatus.CANCELLED],
        )

    def _now(self) -> datetime:
        return normalize_datetime(self._now_fn())


def normalize_datetime(value: datetime) -> datetime:
    """Normalize datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
