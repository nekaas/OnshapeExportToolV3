import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.database import (
    Database,
    ExportHistoryEntry,
    QueueEntry,
    SCHEMA_VERSION,
    SchedulerJobEntry,
)
from onshape_export_manager.core.jobs import JobStatus


class DatabaseTests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_initialize_creates_schema(self) -> None:
        database = self.make_database()

        self.assertEqual(database.schema_version(), SCHEMA_VERSION)
        self.assertEqual(database.get_state("schema_version"), str(SCHEMA_VERSION))

    def test_export_history_round_trip(self) -> None:
        database = self.make_database()
        entry_id = database.add_export_history(
            ExportHistoryEntry(
                account_name="prod",
                label_name="Customer A",
                export_profile="STL",
                exported_files=["a.stl", "b.stl"],
                duration_seconds=2.5,
                success=True,
                failures=[],
                retry_count=1,
            )
        )

        rows = database.list_export_history(label_name="Customer A")

        self.assertEqual(entry_id, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].exported_files, ["a.stl", "b.stl"])
        self.assertTrue(rows[0].success)
        self.assertEqual(rows[0].retry_count, 1)

    def test_queue_round_trip_and_status_update(self) -> None:
        database = self.make_database()
        job_id = database.enqueue(
            QueueEntry(
                label_name="Customer A",
                profile_name="STL",
                payload={"start_iso": "2026-06-01T00:00:00+00:00"},
            )
        )

        database.update_queue_status(
            job_id,
            JobStatus.FAILED,
            retry_count=2,
            last_error="rate limited",
        )
        rows = database.list_queue(status=JobStatus.FAILED)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, job_id)
        self.assertEqual(rows[0].retry_count, 2)
        self.assertEqual(rows[0].last_error, "rate limited")

    def test_scheduler_and_state_round_trip(self) -> None:
        database = self.make_database()
        database.upsert_scheduler_job(
            SchedulerJobEntry(
                name="Customer A hourly",
                label_name="Customer A",
                interval="hourly",
            )
        )
        database.set_state("last_scheduler_tick", "2026-06-25T00:00:00+00:00")

        jobs = database.list_scheduler_jobs(enabled=True)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "Customer A hourly")
        self.assertEqual(
            database.get_state("last_scheduler_tick"),
            "2026-06-25T00:00:00+00:00",
        )

    def test_app_bootstrap_initializes_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))

            self.assertTrue(app.paths.database_file.exists())
            self.assertEqual(app.database.schema_version(), SCHEMA_VERSION)

    def test_status_returns_table_counts(self) -> None:
        database = self.make_database()
        database.enqueue(
            QueueEntry(label_name="Customer A", profile_name="STL", payload={})
        )

        status = database.status()

        self.assertEqual(status["schema_version"], SCHEMA_VERSION)
        self.assertEqual(status["export_queue"], 1)


if __name__ == "__main__":
    unittest.main()
