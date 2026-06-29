import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core import remote_access, system_monitor
from onshape_export_manager.core.backup import BackupManager
from onshape_export_manager.core.configuration import ServerSettingsConfig
from onshape_export_manager.core.logger import shutdown_logging


class SystemMonitorTests(unittest.TestCase):
    def test_snapshot_has_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snap = system_monitor.system_snapshot(Path(tmp))
        for key in ("hostname", "cpu_percent", "memory", "disk", "uptime_seconds", "is_raspberry_pi"):
            self.assertIn(key, snap)
        self.assertIsInstance(snap["cpu_percent"], float)

    def test_human_bytes_and_duration(self) -> None:
        self.assertEqual(system_monitor.human_bytes(0), "0 B")
        self.assertEqual(system_monitor.human_bytes(2048), "2.0 KB")
        self.assertEqual(system_monitor.human_duration(0), "0m")
        self.assertEqual(system_monitor.human_duration(3661), "1h 1m")
        self.assertEqual(system_monitor.human_duration(90000), "1d 1h")

    def test_disk_usage_returns_triple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            usage = system_monitor.disk_usage(Path(tmp))
        self.assertIsNotNone(usage)
        self.assertGreater(usage.total, 0)
        self.assertGreaterEqual(usage.percent, 0.0)


class RemoteAccessTests(unittest.TestCase):
    def test_snapshot_shape(self) -> None:
        snap = remote_access.remote_access_snapshot(port=8080)
        self.assertIn("local_urls", snap)
        self.assertIn("tailscale", snap)
        self.assertIn("cloudflare", snap)
        self.assertIn("reverse_proxies", snap)
        self.assertTrue(any(":8080" in url for url in snap["local_urls"]))

    def test_local_urls_scheme(self) -> None:
        urls = remote_access.local_urls(9000, scheme="https")
        self.assertTrue(all(url.startswith("https://") for url in urls))
        self.assertTrue(any(":9000" in url for url in urls))


class ServerSettingsTests(unittest.TestCase):
    def test_default_mode_is_desktop(self) -> None:
        settings = ServerSettingsConfig()
        self.assertEqual(settings.mode, "desktop")
        self.assertEqual(settings.port, 8080)

    def test_invalid_mode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ServerSettingsConfig(mode="cloud")

    def test_config_exposes_server_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            config = app.config_manager.load()
            self.assertEqual(config.app.server.mode, "desktop")
            self.assertEqual(config.app.server.port, 8080)


class BackupTests(unittest.TestCase):
    def tearDown(self) -> None:
        # Backups log via the app logger, which opens files in the temp dir;
        # release the handles so Windows can delete the temp directory.
        shutdown_logging()

    def test_create_list_verify_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            manager = BackupManager(app.paths)

            info = manager.create_backup()
            self.assertTrue(info.path.exists())
            self.assertGreater(info.entry_count, 0)

            backups = manager.list_backups()
            self.assertEqual(len(backups), 1)
            self.assertTrue(manager.verify_backup(info.name))

            restored = manager.restore_backup(info.name)
            self.assertGreater(restored, 0)
            shutdown_logging()

    def test_prune_keeps_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            manager = BackupManager(app.paths)
            for index in range(3):
                manager.create_backup(label=f"b{index}")
            removed = manager.prune_backups(keep=1)
            self.assertEqual(len(manager.list_backups()), 1)
            self.assertEqual(len(removed), 2)
            shutdown_logging()


if __name__ == "__main__":
    unittest.main()
