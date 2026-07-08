import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.database import ExportHistoryEntry
from onshape_export_manager.core.metrics import (
    MetricsService,
    average_duration,
    export_activity,
    human_bytes,
    success_rate,
)


def _entry(success: bool, *, days_ago: int = 0, files: int = 1, duration: float = 5.0) -> ExportHistoryEntry:
    started = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return ExportHistoryEntry(
        account_name="acct",
        label_name="Customer A",
        export_profile="STL",
        exported_files=[f"f{i}.stl" for i in range(files)],
        duration_seconds=duration,
        success=success,
        failures=[] if success else ["boom"],
        started_at=started,
    )


class MetricsAggregationTests(unittest.TestCase):
    def test_success_rate(self) -> None:
        history = [_entry(True), _entry(True), _entry(False), _entry(True)]
        self.assertEqual(success_rate(history), 75.0)
        self.assertEqual(success_rate([]), 0.0)

    def test_average_duration(self) -> None:
        history = [_entry(True, duration=2), _entry(True, duration=4)]
        self.assertEqual(average_duration(history), 3.0)

    def test_export_activity_buckets(self) -> None:
        history = [_entry(True, days_ago=0), _entry(False, days_ago=1), _entry(True, days_ago=0)]
        activity = export_activity(history, days=7)
        self.assertEqual(len(activity["labels"]), 7)
        self.assertEqual(sum(activity["success"]), 2)
        self.assertEqual(sum(activity["failed"]), 1)

    def test_human_bytes(self) -> None:
        self.assertEqual(human_bytes(0), "0 B")
        self.assertEqual(human_bytes(1024), "1.0 KB")
        self.assertEqual(human_bytes(5 * 1024 * 1024), "5.0 MB")


class MetricsServiceTests(unittest.TestCase):
    def test_dashboard_snapshot_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            metrics = MetricsService(app)
            snapshot = metrics.dashboard_snapshot()

            self.assertEqual(snapshot["summary"]["export_profiles"], 8)
            self.assertIn("activity", snapshot["exports"])
            self.assertIn("counts", snapshot["queue"])
            self.assertIn("schema_version", snapshot["database"])
            self.assertEqual(snapshot["disk"]["total_bytes"], 0)

    def test_global_search_finds_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            metrics = MetricsService(app)

            results = metrics.global_search("bundle")
            titles = [
                item["title"]
                for group in results["groups"]
                for item in group["items"]
            ]
            self.assertTrue(any("Bundle" in title for title in titles))
            self.assertEqual(metrics.global_search("")["total"], 0)

    def test_summary_counts_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            app.database.add_export_history(_entry(False))
            metrics = MetricsService(app)

            counts = metrics.summary_counts()
            self.assertEqual(counts["total_exports"], 1)
            self.assertEqual(counts["failed_exports"], 1)


if __name__ == "__main__":
    unittest.main()
