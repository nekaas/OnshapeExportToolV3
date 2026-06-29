import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.events import Event, EventBus, EventSeverity, EventType
from onshape_export_manager.core.notifications import (
    ChannelSpec,
    NotificationService,
    _format_text,
)


class FakePoster:
    """Records HTTP POST calls instead of performing them."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fail = fail

    def __call__(self, url, *, json, timeout):  # noqa: A002 - matches sender signature
        if self.fail:
            raise RuntimeError("network down")
        self.calls.append((url, json))
        return {"ok": True}


def _spec(kind: str, **kw) -> ChannelSpec:
    base = dict(
        id="c1",
        name="Chan",
        kind=kind,
        enabled=True,
        target="https://example.com/hook",
        min_severity="info",
        categories=frozenset(),
        options={},
    )
    base.update(kw)
    return ChannelSpec(**base)  # type: ignore[arg-type]


class ChannelMatchingTests(unittest.TestCase):
    def test_severity_floor_filters_low_events(self) -> None:
        spec = _spec("webhook", min_severity="warning")
        info_event = Event(type=EventType.JOB_STARTED, severity=EventSeverity.INFO)
        warn_event = Event(type=EventType.JOB_FAILED, severity=EventSeverity.ERROR)
        self.assertFalse(spec.matches(info_event))
        self.assertTrue(spec.matches(warn_event))

    def test_category_allow_list(self) -> None:
        spec = _spec("webhook", categories=frozenset({"auth"}))
        auth_event = Event(type=EventType.AUTH_LOGIN_FAILED, severity=EventSeverity.WARNING)
        queue_event = Event(type=EventType.JOB_FAILED, severity=EventSeverity.ERROR)
        # category comes from the event type's default mapping
        self.assertTrue(spec.matches(auth_event))
        self.assertFalse(spec.matches(queue_event))

    def test_disabled_or_empty_target_never_matches(self) -> None:
        self.assertFalse(_spec("webhook", enabled=False).matches(Event(type=EventType.CUSTOM)))
        self.assertFalse(_spec("webhook", target="").matches(Event(type=EventType.CUSTOM)))


class SenderTests(unittest.TestCase):
    def make_service(self, poster: FakePoster) -> NotificationService:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = create_app(base_dir=Path(tmp.name))
        return NotificationService(app.config_manager, app.event_bus, http_post=poster)

    def test_each_webhook_kind_posts(self) -> None:
        for kind in ("discord", "slack", "teams", "webhook"):
            poster = FakePoster()
            service = self.make_service(poster)
            event = Event(type=EventType.EXPORT_COMPLETED, message="done", severity=EventSeverity.SUCCESS)
            result = service._deliver(_spec(kind), event)
            self.assertTrue(result.ok, kind)
            self.assertEqual(len(poster.calls), 1, kind)
            self.assertEqual(poster.calls[0][0], "https://example.com/hook")

    def test_webhook_sends_full_event(self) -> None:
        poster = FakePoster()
        service = self.make_service(poster)
        event = Event(type=EventType.JOB_FAILED, message="boom", data={"job_id": "x"})
        service._deliver(_spec("webhook"), event)
        _, payload = poster.calls[0]
        self.assertEqual(payload["type"], "queue.job_failed")
        self.assertEqual(payload["data"]["job_id"], "x")

    def test_delivery_failure_is_reported_not_raised(self) -> None:
        poster = FakePoster(fail=True)
        service = self.make_service(poster)
        result = service._deliver(_spec("discord"), Event(type=EventType.CUSTOM))
        self.assertFalse(result.ok)
        self.assertIn("network down", result.detail)

    def test_unknown_kind_is_reported(self) -> None:
        service = self.make_service(FakePoster())
        result = service._deliver(_spec("carrier-pigeon"), Event(type=EventType.CUSTOM))
        self.assertFalse(result.ok)
        self.assertIn("unknown kind", result.detail)

    def test_email_requires_smtp_host(self) -> None:
        service = self.make_service(FakePoster())
        spec = _spec("email", target="to@example.com", options={})
        result = service._deliver(spec, Event(type=EventType.CUSTOM))
        self.assertFalse(result.ok)
        self.assertIn("smtp_host", result.detail)

    def test_dispatch_via_bus_subscription(self) -> None:
        poster = FakePoster()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = create_app(base_dir=Path(tmp.name))
        # Inject a channel into config so dispatch finds it.
        from onshape_export_manager.core.configuration import read_json, write_json

        path = app.config_manager.config_file
        data = read_json(path)
        data.setdefault("notifications", {"enabled": True, "channels": []})["channels"] = [
            {
                "id": "c1",
                "name": "Hook",
                "kind": "webhook",
                "enabled": True,
                "target": "https://example.com/hook",
                "min_severity": "info",
                "categories": [],
                "options": {},
            }
        ]
        write_json(path, data)

        service = NotificationService(app.config_manager, app.event_bus, http_post=poster)
        results = service.dispatch(Event(type=EventType.EXPORT_COMPLETED, message="ok"))
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(len(poster.calls), 1)

    def test_meta_events_are_not_redelivered(self) -> None:
        """A NOTIFICATION_SENT meta-event must never itself be delivered, or
        delivery would loop forever feeding an all-categories channel."""
        from onshape_export_manager.core.notifications import _META_EVENT_TYPES

        spec = _spec("webhook", categories=frozenset())  # empty = all categories
        for meta_type in _META_EVENT_TYPES:
            self.assertFalse(spec.matches(Event(type=meta_type)))

    def test_enqueue_drops_meta_events(self) -> None:
        poster = FakePoster()
        service = self.make_service(poster)
        service.start()
        try:
            # Emitting a meta-event onto the bus must NOT enqueue it for delivery.
            service.event_bus.emit(EventType.NOTIFICATION_SENT, "meta")
            self.assertTrue(service._queue.empty())
        finally:
            service.stop()

    def test_format_text_includes_message(self) -> None:
        text = _format_text(Event(type=EventType.JOB_FAILED, message="it broke", severity=EventSeverity.ERROR))
        self.assertIn("it broke", text)
        self.assertIn("queue.job_failed", text)


if __name__ == "__main__":
    unittest.main()
