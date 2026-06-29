import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from onshape_export_manager.core.audit import AuditService, TelemetryStore
from onshape_export_manager.core.database import Database, EventRecord, TelemetryPoint, utc_now
from onshape_export_manager.core.events import EventBus, EventSeverity, EventType


class DatabaseV3Tests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_schema_version_is_three(self) -> None:
        database = self.make_database()
        self.assertEqual(database.schema_version(), 3)

    def test_status_includes_events_and_telemetry(self) -> None:
        database = self.make_database()
        status = database.status()
        self.assertIn("events", status)
        self.assertIn("telemetry", status)
        self.assertEqual(status["events"], 0)

    def test_add_and_list_events_with_filters(self) -> None:
        database = self.make_database()
        database.add_event(EventRecord(type="queue.job_started", category="queue", severity="info", message="a"))
        database.add_event(EventRecord(type="queue.job_failed", category="queue", severity="error", message="b"))
        database.add_event(EventRecord(type="auth.login_succeeded", category="auth", severity="success", message="c"))

        all_events = database.list_events(limit=10)
        self.assertEqual(len(all_events), 3)
        # newest first
        self.assertEqual(all_events[0].message, "c")

        queue_events = database.list_events(category="queue")
        self.assertEqual(len(queue_events), 2)

        errors = database.list_events(severity="error")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].type, "queue.job_failed")

    def test_events_pagination(self) -> None:
        database = self.make_database()
        for i in range(10):
            database.add_event(EventRecord(type="custom", category="system", severity="info", message=f"e{i}"))
        page1 = database.list_events(limit=3, offset=0)
        page2 = database.list_events(limit=3, offset=3)
        self.assertEqual(len(page1), 3)
        self.assertEqual(len(page2), 3)
        self.assertNotEqual(page1[0].message, page2[0].message)

    def test_duplicate_event_id_ignored(self) -> None:
        database = self.make_database()
        rec = EventRecord(type="custom", category="system", severity="info", message="dup", event_id="fixed-id")
        database.add_event(rec)
        database.add_event(EventRecord(type="custom", category="system", severity="info", message="dup2", event_id="fixed-id"))
        self.assertEqual(database.count_events(), 1)

    def test_purge_events_by_age(self) -> None:
        database = self.make_database()
        old = EventRecord(type="custom", category="system", severity="info", message="old")
        old.timestamp = utc_now() - timedelta(days=200)
        database.add_event(old)
        database.add_event(EventRecord(type="custom", category="system", severity="info", message="new"))

        removed = database.purge_events(keep_days=90)
        self.assertEqual(removed, 1)
        self.assertEqual(database.count_events(), 1)

    def test_telemetry_record_and_query(self) -> None:
        database = self.make_database()
        database.add_telemetry(TelemetryPoint(metric="cpu", value=12.5))
        database.add_telemetry(TelemetryPoint(metric="cpu", value=30.0))
        database.add_telemetry(TelemetryPoint(metric="ram", value=55.0))

        cpu = database.query_telemetry("cpu", limit=10)
        self.assertEqual(len(cpu), 2)
        self.assertEqual([p.value for p in cpu], [12.5, 30.0])  # oldest-first
        self.assertEqual(set(database.distinct_metrics()), {"cpu", "ram"})

    def test_telemetry_batch_and_purge(self) -> None:
        database = self.make_database()
        n = database.add_telemetry_batch(
            [TelemetryPoint(metric="q.depth", value=float(i)) for i in range(5)]
        )
        self.assertEqual(n, 5)
        stale = TelemetryPoint(metric="q.depth", value=99.0)
        stale.timestamp = utc_now() - timedelta(days=60)
        database.add_telemetry(stale)
        removed = database.purge_telemetry(keep_days=30)
        self.assertEqual(removed, 1)


class AuditServiceTests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_audit_persists_bus_events(self) -> None:
        database = self.make_database()
        bus = EventBus()
        audit = AuditService(database, bus)
        audit.start()

        bus.emit(EventType.JOB_COMPLETED, "done", severity=EventSeverity.SUCCESS, data={"files": 2})

        events = audit.list_events(limit=10)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "queue.job_completed")
        self.assertEqual(events[0]["data"]["files"], 2)

    def test_audit_summary_counts_severities(self) -> None:
        database = self.make_database()
        bus = EventBus()
        audit = AuditService(database, bus)
        audit.start()

        bus.emit(EventType.JOB_STARTED, "a")
        bus.emit(EventType.JOB_FAILED, "b", severity=EventSeverity.ERROR)
        bus.emit(EventType.SYSTEM_HEALTH_WARNING, "c", severity=EventSeverity.WARNING)

        summary = audit.summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["warnings"], 1)

    def test_audit_stop_unsubscribes(self) -> None:
        database = self.make_database()
        bus = EventBus()
        audit = AuditService(database, bus)
        audit.start()
        audit.stop()
        bus.emit(EventType.JOB_STARTED, "after stop")
        self.assertEqual(audit.summary()["total"], 0)

    def test_telemetry_store_series(self) -> None:
        database = self.make_database()
        store = TelemetryStore(database)
        store.record("cpu", 10.0)
        store.record("cpu", 20.0)
        series = store.series("cpu")
        self.assertEqual(series["count"], 2)
        self.assertEqual(series["values"], [10.0, 20.0])
        self.assertEqual(len(series["timestamps"]), 2)


if __name__ == "__main__":
    unittest.main()
