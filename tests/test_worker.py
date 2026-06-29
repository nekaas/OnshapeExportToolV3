import json
import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.export_engine import ExportResult
from onshape_export_manager.core.jobs import JobStatus
from onshape_export_manager.core.worker import BackgroundWorker


class StubEngine:
    """Stand-in for ExportEngine that records requests and returns a result."""

    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.requests: list = []

    async def run_manual_export(self, request):
        self.requests.append(request)
        return ExportResult(
            success=self.success,
            account_name="acct",
            failed_items=[] if self.success else ["boom"],
        )


def _seed_config(base_dir: Path) -> None:
    """Write a minimal but valid account + label + profile set."""
    config_dir = base_dir / "onshape_export_manager" / "config"
    (config_dir / "accounts.json").write_text(
        json.dumps({"accounts": [{"name": "acct", "access_key": "a", "secret_key": "s"}]}),
        encoding="utf-8",
    )
    (config_dir / "labels.json").write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "friendly_name": "Customer A",
                        "onshape_label_id": "123456789012345678901234",
                        "assigned_accounts": ["acct"],
                        "export_location": "exports",
                        "export_profile": "STL",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class WorkerTests(unittest.TestCase):
    def make_app(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        app = create_app(base_dir=base)  # creates dirs + default config + db
        _seed_config(base)
        return app

    def test_run_once_completes_a_queued_job(self) -> None:
        app = self.make_app()
        stub = StubEngine(success=True)
        app.create_export_engine = lambda *a, **k: stub  # type: ignore[assignment]
        worker = BackgroundWorker(app)

        job_id = app.queue_manager.enqueue(
            label_name="Customer A",
            profile_name="STL",
            payload={"start_iso": "2026-06-25T00:00:00+00:00", "end_iso": "2026-06-26T00:00:00+00:00"},
            reason="manual",
        )

        result = worker.run_once()

        self.assertEqual(result.jobs_run, 1)
        self.assertEqual(result.jobs_succeeded, 1)
        self.assertEqual(len(stub.requests), 1)
        entry = app.database.get_queue_entry(job_id)
        assert entry is not None
        self.assertEqual(entry.status, JobStatus.COMPLETED)
        self.assertEqual(worker.status().jobs_processed, 1)

    def test_run_once_retries_a_failed_job(self) -> None:
        app = self.make_app()
        stub = StubEngine(success=False)
        app.create_export_engine = lambda *a, **k: stub  # type: ignore[assignment]
        worker = BackgroundWorker(app)

        job_id = app.queue_manager.enqueue(
            label_name="Customer A", profile_name="STL", payload={}, reason="manual"
        )

        result = worker.run_once()

        self.assertEqual(result.jobs_failed, 1)
        entry = app.database.get_queue_entry(job_id)
        assert entry is not None
        # First failure schedules a retry (PENDING), not permanent failure.
        self.assertEqual(entry.status, JobStatus.PENDING)
        self.assertGreaterEqual(entry.retry_count, 1)

    def test_unknown_label_marks_job_failed(self) -> None:
        app = self.make_app()
        worker = BackgroundWorker(app)
        job_id = app.queue_manager.enqueue(
            label_name="Nonexistent", profile_name="STL", payload={}, reason="manual"
        )

        result = worker.run_once()

        self.assertEqual(result.jobs_failed, 1)
        entry = app.database.get_queue_entry(job_id)
        assert entry is not None
        self.assertIn(entry.status, {JobStatus.PENDING, JobStatus.FAILED})
        self.assertTrue(entry.last_error)


if __name__ == "__main__":
    unittest.main()
