"""Job status and state machine for export jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4


def generate_id() -> str:
    """Return a 32-character hex UUID suitable for primary keys.

    Uses ``uuid4().hex`` (no dashes) for compact, index-friendly database
    storage.  Prefer this over ``str(uuid4())`` when creating new IDs.
    """
    return uuid4().hex


class JobStatus(StrEnum):
    """Possible states for an export job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid transitions enforced by the queue manager.
# Retries (FAILED → PENDING) move jobs back to pending for re-claim.
# Admin operations (cancel, requeue) are more permissive.
# PENDING → FAILED is valid when retries are exhausted without re-claim.
VALID_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.FAILED: {JobStatus.PENDING},  # retry / requeue
    JobStatus.COMPLETED: set(),  # terminal
    JobStatus.CANCELLED: {JobStatus.PENDING},  # requeue
}


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    """Return True if transitioning from *current* to *target* is valid."""
    return target in VALID_TRANSITIONS.get(current, set())


@dataclass(slots=True)
class ExportJob:
    """Database-friendly export job metadata."""

    label_name: str
    profile_name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
