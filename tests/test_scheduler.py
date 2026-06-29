import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onshape_export_manager.core.database import Database
from onshape_export_manager.core.models import LabelDefinition
from onshape_export_manager.core.queue_manager import QueueManager
from onshape_export_manager.core.scheduler import (
    ScheduleInterval,
    SchedulerService,
    next_run_after,
    parse_interval,
)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)

    def advance(self, delta: timedelta) -> None:
        self.now += delta

    def __call__(self) -> datetime:
        return self.now


class SchedulerTests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_parse_interval_aliases(self) -> None:
        self.assertEqual(parse_interval("hourly"), ScheduleInterval.HOURLY)
        self.assertEqual(parse_interval("every_15_minutes"), ScheduleInterval.EVERY_15_MINUTES)

    def test_next_run_after(self) -> None:
        now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(next_run_after(now, ScheduleInterval.HOURLY), now + timedelta(hours=1))

    def test_sync_labels_creates_scheduler_jobs(self) -> None:
        clock = Clock()
        database = self.make_database()
        service = SchedulerService(database, QueueManager(database), now_fn=clock)
        label = LabelDefinition(
            friendly_name="Customer A",
            onshape_label_id="123456789012345678901234",
            assigned_accounts=[],
            export_location=Path("/tmp"),
            export_profile="STL",
            scheduler="hourly",
        )

        ids = service.sync_labels([label])
        jobs = database.list_scheduler_jobs()

        self.assertEqual(len(ids), 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].interval, "hourly")
        self.assertEqual(jobs[0].next_run_at, clock.now)

    def test_tick_enqueues_due_jobs_and_advances_schedule(self) -> None:
        clock = Clock()
        database = self.make_database()
        queue = QueueManager(database, now_fn=clock)
        service = SchedulerService(database, queue, now_fn=clock)
        label = LabelDefinition(
            friendly_name="Customer A",
            onshape_label_id="123456789012345678901234",
            assigned_accounts=[],
            export_location=Path("/tmp"),
            export_profile="STL",
            scheduler="hourly",
        )
        service.sync_labels([label])

        result = service.tick()
        jobs = database.list_scheduler_jobs()
        queue_jobs = database.list_queue()

        self.assertEqual(len(result.queued_job_ids), 1)
        self.assertEqual(len(queue_jobs), 1)
        self.assertEqual(queue_jobs[0].payload["queue_reason"], "scheduled")
        self.assertEqual(queue_jobs[0].profile_name, "STL")
        self.assertEqual(jobs[0].last_run_at, clock.now)
        self.assertEqual(jobs[0].next_run_at, clock.now + timedelta(hours=1))

    def test_start_stop_persists_running_state(self) -> None:
        database = self.make_database()
        service = SchedulerService(database, QueueManager(database))

        service.start()
        self.assertTrue(service.running)
        self.assertEqual(database.get_state("scheduler.running"), "true")

        service.stop()
        self.assertFalse(service.running)
        self.assertEqual(database.get_state("scheduler.running"), "false")


if __name__ == "__main__":
    unittest.main()
