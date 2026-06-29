import asyncio
import unittest

from onshape_export_manager.core.events import (
    Event,
    EventBus,
    EventCategory,
    EventSeverity,
    EventType,
)


class EventBusTests(unittest.TestCase):
    def test_emit_publishes_to_subscriber(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        bus.subscribe(received.append)

        event = bus.emit(EventType.JOB_STARTED, "started", data={"job_id": "x"})

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], event)
        self.assertEqual(received[0].type, EventType.JOB_STARTED)
        self.assertEqual(received[0].category, EventCategory.QUEUE)
        self.assertEqual(received[0].data["job_id"], "x")

    def test_type_filter_only_receives_matching_events(self) -> None:
        bus = EventBus()
        got: list[Event] = []
        bus.subscribe(got.append, types=[EventType.JOB_FAILED])

        bus.emit(EventType.JOB_STARTED, "a")
        bus.emit(EventType.JOB_FAILED, "b")

        self.assertEqual([e.type for e in got], [EventType.JOB_FAILED])

    def test_category_filter(self) -> None:
        bus = EventBus()
        got: list[Event] = []
        bus.subscribe(got.append, categories=[EventCategory.AUTH])

        bus.emit(EventType.JOB_STARTED, "queue event")
        bus.emit(EventType.AUTH_LOGIN_SUCCEEDED, "auth event")

        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].category, EventCategory.AUTH)

    def test_unsubscribe_stops_delivery(self) -> None:
        bus = EventBus()
        got: list[Event] = []
        token = bus.subscribe(got.append)

        bus.emit(EventType.WORKER_TICK, "1")
        self.assertTrue(bus.unsubscribe(token))
        bus.emit(EventType.WORKER_TICK, "2")

        self.assertEqual(len(got), 1)

    def test_raising_subscriber_does_not_break_publish(self) -> None:
        bus = EventBus()
        good: list[Event] = []

        def boom(_event: Event) -> None:
            raise RuntimeError("subscriber failure")

        bus.subscribe(boom)
        bus.subscribe(good.append)

        bus.emit(EventType.SYSTEM_STARTUP, "ok")  # must not raise

        self.assertEqual(len(good), 1)

    def test_recent_ring_buffer_and_filters(self) -> None:
        bus = EventBus(history_size=10)
        for i in range(15):
            bus.emit(EventType.WORKER_TICK, f"tick {i}", severity=EventSeverity.DEBUG)
        bus.emit(EventType.JOB_FAILED, "fail", severity=EventSeverity.ERROR)

        recent = bus.recent(limit=100)
        self.assertEqual(len(recent), 10)  # capped by history_size

        errors = bus.recent(min_severity=EventSeverity.WARNING)
        self.assertEqual([e.type for e in errors], [EventType.JOB_FAILED])

        queue_only = bus.recent(categories=[EventCategory.QUEUE])
        self.assertTrue(all(e.category == EventCategory.QUEUE for e in queue_only))

    def test_async_subscriber_runs(self) -> None:
        bus = EventBus()
        seen: list[str] = []

        async def handler(event: Event) -> None:
            seen.append(event.message)

        bus.subscribe(handler)
        bus.emit(EventType.CUSTOM, "async-ok")  # no running loop → runs to completion

        self.assertEqual(seen, ["async-ok"])

    def test_to_dict_is_json_serializable(self) -> None:
        import json

        bus = EventBus()
        event = bus.emit(EventType.EXPORT_COMPLETED, "done", data={"files": 3})
        payload = event.to_dict()
        text = json.dumps(payload)  # must not raise
        self.assertIn("export.completed", text)
        self.assertEqual(payload["severity"], "info")
        self.assertIsInstance(payload["timestamp"], str)

    def test_async_subscriber_on_running_loop(self) -> None:
        bus = EventBus()
        seen: list[str] = []

        async def handler(event: Event) -> None:
            seen.append(event.message)

        async def main() -> None:
            bus.subscribe(handler)
            bus.emit(EventType.CUSTOM, "loop-ok")
            await asyncio.sleep(0)  # let the scheduled task run

        asyncio.run(main())
        self.assertEqual(seen, ["loop-ok"])


if __name__ == "__main__":
    unittest.main()
