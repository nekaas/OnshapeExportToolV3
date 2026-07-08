"""Integration tests for CLI commands.

Tests every CLI command via ``subprocess.run()`` in isolated temporary
directories.  Each test creates a fresh app directory, initialises it,
then exercises one or more commands and verifies the exit code, stdout,
and filesystem/database state.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from onshape_export_manager.cli import export_window, parse_cli_datetime


class CliUnitTests(unittest.TestCase):
    """Pure-unit tests for CLI helper functions (no subprocess)."""

    def test_parse_cli_datetime_accepts_zulu_time(self) -> None:
        parsed = parse_cli_datetime("2026-06-25T12:00:00Z")
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.isoformat(), "2026-06-25T12:00:00+00:00")

    def test_export_window_rejects_reversed_dates(self) -> None:
        with self.assertRaises(ValueError):
            export_window(
                "2026-06-26T00:00:00+00:00",
                "2026-06-25T00:00:00+00:00",
            )


class CliIntegrationTests(unittest.TestCase):
    """Subprocess-based integration tests for every CLI command."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name)
        # The app creates its structure under cwd/onshape_export_manager/
        self.app_dir = self.cwd / "onshape_export_manager"

    # -- helpers ------------------------------------------------------------

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Invoke the CLI module inside the temporary directory."""
        env = {**os.environ, "PYTHONPATH": os.getcwd()}
        return subprocess.run(
            [sys.executable, "-m", "onshape_export_manager.cli", *args],
            capture_output=True,
            text=True,
            cwd=str(self.cwd),
            env=env,
        )

    def _init(self) -> None:
        """Bootstrap the application in the temp directory."""
        result = self._run("--init")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    # -- init / scaffold ----------------------------------------------------

    def test_init_creates_directories_and_default_configs(self) -> None:
        result = self._run("--init")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Initialized", result.stdout)
        # Verify expected directories exist under the app directory
        for sub in ("config", "exports", "logs", "database", "backups"):
            self.assertTrue(
                (self.app_dir / sub).is_dir(), f"missing dir: {sub}"
            )
        # Verify default config files exist
        for name in ("config.json", "accounts.json", "labels.json",
                     "export_profiles.json", "organizations.json"):
            self.assertTrue(
                (self.app_dir / "config" / name).is_file(),
                f"missing config: {name}",
            )

    def test_init_config_creates_missing_files_only(self) -> None:
        self._init()
        # Remove one config file and re-run
        (self.app_dir / "config" / "labels.json").unlink()
        result = self._run("--init-config")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue((self.app_dir / "config" / "labels.json").is_file())

    def test_init_db_creates_schema(self) -> None:
        self._init()
        result = self._run("--init-db")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Initialized database", result.stdout)
        db_path = self.app_dir / "database" / "exports.db"
        self.assertTrue(db_path.is_file())

    # -- validation ---------------------------------------------------------

    def test_validate_config_reports_valid(self) -> None:
        self._init()
        result = self._run("--validate-config")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Configuration valid", result.stdout)

    def test_validate_config_rejects_invalid(self) -> None:
        self._init()
        # Corrupt the config
        (self.app_dir / "config" / "config.json").write_text("{invalid")
        result = self._run("--validate-config")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid", result.stdout.lower())

    # -- status commands ----------------------------------------------------

    def test_database_status_shows_table_counts(self) -> None:
        self._init()
        self._run("--init-db")
        result = self._run("--database-status")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Schema version", result.stdout)
        self.assertIn("Export history rows", result.stdout)

    def test_accounts_status_reports_no_accounts(self) -> None:
        self._init()
        result = self._run("--accounts-status")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("No Onshape accounts configured", result.stdout)

    def test_queue_status_shows_zeroes(self) -> None:
        self._init()
        self._run("--init-db")
        result = self._run("--queue-status")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Pending: 0", result.stdout)

    def test_scheduler_status_reports(self) -> None:
        self._init()
        self._run("--init-db")
        result = self._run("--scheduler-status")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Scheduler running", result.stdout)

    # -- list commands ------------------------------------------------------

    def test_list_export_formats(self) -> None:
        self._init()
        result = self._run("--list-export-formats")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("stl:", result.stdout.lower())
        self.assertIn("step:", result.stdout.lower())

    def test_list_export_profiles(self) -> None:
        self._init()
        result = self._run("--list-export-profiles")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("STL:", result.stdout)
        self.assertIn("STEP:", result.stdout)

    # -- profile management -------------------------------------------------

    def test_add_export_profile_requires_formats(self) -> None:
        self._init()
        result = self._run("--add-export-profile", "TestProfile")
        self.assertNotEqual(result.returncode, 0)

    def test_add_export_profile_creates_profile(self) -> None:
        self._init()
        result = self._run(
            "--add-export-profile", "Custom STL",
            "--formats", "stl",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Saved export profile", result.stdout)
        # Verify it appears in the list
        list_result = self._run("--list-export-profiles")
        self.assertIn("Custom STL:", list_result.stdout)

    # -- worker commands ----------------------------------------------------

    def test_drain_once_does_not_crash(self) -> None:
        self._init()
        self._run("--init-db")
        result = self._run("--drain-once")
        # Worker tick on empty queue should succeed
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Worker tick complete", result.stdout)

    # -- version ------------------------------------------------------------

    def test_version(self) -> None:
        result = self._run("--version")
        # argparse --version prints and exits 0
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.1.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
