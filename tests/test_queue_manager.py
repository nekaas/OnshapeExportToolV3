import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onshape_export_manager.core.database import Database
from onshape_export_manager.core.jobs import JobStatus
from onshape_export_manager.core.queue_manager import QueueManager, QueueRetryPolicy


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)

    def advance(self, delta: timedelta) -> None:
        self.now += delta

    def __call__(self) -> datetime:
        return self.now


class QueueManagerTests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_enqueue_and_claim_due_job(self) -> None:
        database = self.make_database()
        manager = QueueManager(database)
        job_id = manager.enqueue(
            label_name="Customer A",
            profile_name="STL",
            payload={"start_iso": "2026-06-25T00:00:00+00:00"},
            reason="rate limited",
        )

        claimed = manager.claim_next()

        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.id, job_id)
        self.assertEqual(claimed.status, JobStatus.RUNNING)
        self.assertEqual(claimed.payload["queue_reason"], "rate limited")

    def test_future_job_is_not_due_until_time_passes(self) -> None:
        clock = Clock()
        database = self.make_database()
        manager = QueueManager(database, now_fn=clock)
        manager.enqueue(
            label_name="Customer A",
            profile_name="STL",
            payload={},
            next_run_at=clock.now + timedelta(minutes=10),
        )

        self.assertEqual(manager.due_jobs(), [])
        clock.advance(timedelta(minutes=11))
        self.assertEqual(len(manager.due_jobs()), 1)

    def test_failed_job_retries_with_backoff_then_fails_permanently(self) -> None:
        clock = Clock()
        database = self.make_database()
        manager = QueueManager(
            database,
            retry_policy=QueueRetryPolicy(
                max_attempts=3,
                backoff_base_seconds=2,
                backoff_max_seconds=10,
            ),
            now_fn=clock,
        )
        job_id = manager.enqueue(label_name="Customer A", profile_name="STL", payload={})
        claimed = manager.claim_next()
        assert claimed is not None

        status = manager.mark_failed(job_id, "timeout")
        job = database.get_queue_entry(job_id)
        assert job is not None
        self.assertEqual(status, JobStatus.PENDING)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.next_run_at, clock.now + timedelta(seconds=2))

        manager.mark_failed(job_id, "timeout again")
        status = manager.mark_failed(job_id, "final")
        job = database.get_queue_entry(job_id)
        assert job is not None
        self.assertEqual(status, JobStatus.FAILED)
        self.assertEqual(job.retry_count, 3)
        self.assertEqual(job.last_error, "final")

    def test_complete_cancel_requeue_and_stats(self) -> None:
        database = self.make_database()
        manager = QueueManager(database)
        completed = manager.enqueue(label_name="A", profile_name="STL", payload={})
        cancelled = manager.enqueue(label_name="B", profile_name="STL", payload={})

        manager.claim_next()
        manager.mark_completed(completed)
        manager.cancel(cancelled)
        manager.requeue(cancelled)
        stats = manager.stats()

        self.assertEqual(stats.completed, 1)
        self.assertEqual(stats.pending, 1)
        self.assertEqual(stats.total, 2)


if __name__ == "__main__":
    unittest.main()
