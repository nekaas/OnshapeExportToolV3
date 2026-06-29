import shutil
import tempfile
import unittest
from pathlib import Path

import onshape_export_manager
from onshape_export_manager.core.logger import shutdown_logging
from onshape_export_manager.web import create_web_app

try:
    from fastapi.testclient import TestClient

    HAS_TESTCLIENT = True
except ModuleNotFoundError:  # pragma: no cover - optional in minimal envs
    HAS_TESTCLIENT = False

PACKAGE_UI = Path(onshape_export_manager.__file__).parent / "ui"


@unittest.skipUnless(HAS_TESTCLIENT, "fastapi TestClient not installed")
class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        # Templates/static live in the installed package; copy them into the
        # isolated base dir so the web app can render without touching the
        # developer's working tree.
        shutil.copytree(PACKAGE_UI, Path(self._tmp.name) / "onshape_export_manager" / "ui")
        self.client = TestClient(create_web_app(Path(self._tmp.name)))

    def tearDown(self) -> None:
        self.client.close()
        shutdown_logging()
        self._tmp.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_metrics_endpoint(self) -> None:
        data = self.client.get("/api/metrics").json()
        self.assertEqual(data["summary"]["export_profiles"], 9)
        self.assertIn("activity", data["exports"])

    def test_summary_endpoint(self) -> None:
        data = self.client.get("/api/summary").json()
        self.assertIn("queue_size", data)

    def test_resource_endpoints(self) -> None:
        self.assertEqual(self.client.get("/api/accounts").json(), {"accounts": []})
        self.assertEqual(self.client.get("/api/labels").json(), {"labels": []})
        self.assertEqual(len(self.client.get("/api/profiles").json()["profiles"]), 9)
        self.assertEqual(self.client.get("/api/queue").json(), {"items": []})
        self.assertIn("history", self.client.get("/api/history").json())

    def test_worker_status_endpoint(self) -> None:
        data = self.client.get("/api/worker").json()
        self.assertIn("running", data)
        self.assertIn("jobs_processed", data)

    def test_run_export_rejects_unknown_label(self) -> None:
        response = self.client.post("/api/exports/run", json={"label": "Nope"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_run_export_requires_label(self) -> None:
        response = self.client.post("/api/exports/run", json={})
        self.assertEqual(response.status_code, 400)

    def test_manual_export_preview_validates_and_estimates(self) -> None:
        self.client.post(
            "/api/labels",
            json={
                "friendly_name": "Preview Label",
                "onshape_label_id": "c" * 24,
                "export_profile": "STL",
            },
        )

        response = self.client.post(
            "/api/exports/preview",
            json={
                "label": "Preview Label",
                "start": "2026-06-25T00:00:00+00:00",
                "end": "2026-06-26T00:00:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["label"]["name"], "Preview Label")
        self.assertEqual(data["profile"]["name"], "STL")
        self.assertEqual(data["window"]["duration_hours"], 24)
        self.assertEqual(data["formats"][0]["format"], "stl")
        self.assertIn("api_calls_label", data["estimates"])
        self.assertEqual(data["checks"][0]["status"], "ok")

    def test_manual_export_preview_rejects_bad_window(self) -> None:
        self.client.post(
            "/api/labels",
            json={
                "friendly_name": "Bad Window Label",
                "onshape_label_id": "d" * 24,
                "export_profile": "STL",
            },
        )

        response = self.client.post(
            "/api/exports/preview",
            json={
                "label": "Bad Window Label",
                "start": "2026-06-26T00:00:00+00:00",
                "end": "2026-06-25T00:00:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["valid"])

    def test_queue_action_missing_job_is_404(self) -> None:
        response = self.client.post("/api/queue/does-not-exist/cancel")
        self.assertEqual(response.status_code, 404)

    def test_system_endpoint_includes_worker(self) -> None:
        data = self.client.get("/api/system").json()
        self.assertIn("worker", data)
        self.assertIn("running", data["worker"])

    def test_formats_endpoint(self) -> None:
        formats = self.client.get("/api/formats").json()["formats"]
        self.assertIn("stl", [item["format"] for item in formats])

    def test_logs_endpoint(self) -> None:
        ok = self.client.get("/api/logs/app")
        self.assertEqual(ok.status_code, 200)
        self.assertIn("lines", ok.json())
        missing = self.client.get("/api/logs/does-not-exist")
        self.assertEqual(missing.status_code, 404)

    def test_search_endpoint(self) -> None:
        data = self.client.get("/api/search", params={"q": "stl"}).json()
        self.assertGreaterEqual(data["total"], 1)

    def test_pages_render(self) -> None:
        self.assertEqual(self.client.get("/").status_code, 200)
        for page in ("accounts", "labels", "export-profiles", "queue", "history", "logs", "settings"):
            self.assertEqual(self.client.get(f"/{page}").status_code, 200)

    def test_unknown_page_is_404(self) -> None:
        self.assertEqual(self.client.get("/totally-unknown").status_code, 404)

    def test_setup_wizard_flow(self) -> None:
        status = self.client.get("/api/setup/status").json()
        self.assertFalse(status["configured"])

        # Unconfigured dashboard redirects to the wizard.
        redirect = self.client.get("/", follow_redirects=False)
        self.assertEqual(redirect.status_code, 302)
        self.assertEqual(redirect.headers["location"], "/setup")
        self.assertEqual(self.client.get("/setup").status_code, 200)

        # Owner creation, organization, credential, profile, label, complete.
        self.assertEqual(self.client.post("/api/setup/owner", json={"username": "admin", "password": "supersecret"}).status_code, 200)
        org_id = self.client.post("/api/organizations", json={"name": "School", "type": "school"}).json()["id"]
        self.assertEqual(self.client.post(f"/api/organizations/{org_id}/credentials", json={"name": "Primary", "access_key": "env:A", "secret_key": "env:S"}).status_code, 200)
        self.assertEqual(self.client.post("/api/profiles", json={"name": "Shop Bundle", "formats": "stl,step"}).status_code, 200)
        self.assertEqual(self.client.post("/api/labels", json={"friendly_name": "Customer A", "onshape_label_id": "a" * 24, "export_profile": "STL"}).status_code, 200)
        self.assertEqual(self.client.post("/api/setup/complete").json(), {"ok": True})

        # Once complete the wizard redirects to the dashboard.
        done = self.client.get("/setup", follow_redirects=False)
        self.assertEqual(done.status_code, 302)
        self.assertEqual(done.headers["location"], "/")

    def test_create_label_rejects_unknown_profile(self) -> None:
        # Owner must exist so the request is authorized via the session cookie.
        self.client.post("/api/setup/owner", json={"username": "admin", "password": "supersecret"})
        bad = self.client.post("/api/labels", json={"friendly_name": "X", "onshape_label_id": "b" * 24, "export_profile": "DoesNotExist"})
        self.assertEqual(bad.status_code, 400)

    # -- Events / audit / telemetry ----------------------------------------

    def test_events_endpoint_shape(self) -> None:
        data = self.client.get("/api/events").json()
        self.assertIn("events", data)
        self.assertIn("summary", data)
        self.assertIn("categories", data)
        self.assertIn("severities", data)

    def test_org_creation_records_an_event(self) -> None:
        self.client.post("/api/organizations", json={"name": "EventOrg", "type": "company"})
        events = self.client.get("/api/events", params={"category": "config"}).json()["events"]
        types = [e["type"] for e in events]
        self.assertIn("config.org_created", types)

    def test_events_recent_endpoint(self) -> None:
        self.client.post("/api/organizations", json={"name": "RecentOrg", "type": "company"})
        data = self.client.get("/api/events/recent").json()
        self.assertIn("events", data)
        self.assertGreaterEqual(len(data["events"]), 1)

    def test_telemetry_metrics_endpoint(self) -> None:
        data = self.client.get("/api/telemetry/metrics").json()
        self.assertIn("metrics", data)
        self.assertIsInstance(data["metrics"], list)

    def test_telemetry_series_endpoint(self) -> None:
        data = self.client.get("/api/telemetry/cpu.percent").json()
        self.assertEqual(data["metric"], "cpu.percent")
        self.assertIn("timestamps", data)
        self.assertIn("values", data)

    def test_activity_page_renders(self) -> None:
        self.assertEqual(self.client.get("/activity").status_code, 200)

    # -- Notifications ------------------------------------------------------

    def test_notifications_crud(self) -> None:
        listing = self.client.get("/api/notifications").json()
        self.assertEqual(listing["channels"], [])
        self.assertIn("discord", listing["kinds"])

        created = self.client.post(
            "/api/notifications",
            json={"name": "Team Hook", "kind": "webhook", "target": "https://example.com/h"},
        )
        self.assertEqual(created.status_code, 200)
        channel_id = created.json()["id"]

        after_create = self.client.get("/api/notifications").json()
        self.assertEqual(len(after_create["channels"]), 1)

        updated = self.client.put(
            f"/api/notifications/{channel_id}",
            json={"name": "Renamed", "kind": "webhook", "target": "https://example.com/h2"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Renamed")

        deleted = self.client.delete(f"/api/notifications/{channel_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/notifications").json()["channels"], [])

    def test_notifications_reject_bad_kind(self) -> None:
        bad = self.client.post(
            "/api/notifications", json={"name": "X", "kind": "telepathy", "target": "y"}
        )
        self.assertEqual(bad.status_code, 400)

    def test_notification_test_missing_channel(self) -> None:
        resp = self.client.post("/api/notifications/nope/test")
        self.assertEqual(resp.status_code, 404)

    def test_notifications_page_renders(self) -> None:
        self.assertEqual(self.client.get("/notifications").status_code, 200)

    def test_websocket_streams_emitted_events(self) -> None:
        # Setup-mode app is open, so the WS handshake is allowed without a cookie.
        with self.client.websocket_connect("/ws/events") as ws:
            # Trigger an event over HTTP; it should arrive on the socket.
            self.client.post("/api/organizations", json={"name": "WsOrg", "type": "company"})
            seen_types: list[str] = []
            # Replay buffer + the new event; read a few frames until we see it.
            for _ in range(25):
                payload = ws.receive_json()
                seen_types.append(payload["type"])
                if payload["type"] == "config.org_created":
                    break
            self.assertIn("config.org_created", seen_types)


if __name__ == "__main__":
    unittest.main()
