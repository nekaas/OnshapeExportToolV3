import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from onshape_export_manager.app import create_app
from onshape_export_manager.core.configuration import (
    AccountsConfig,
    ConfigError,
    ConfigManager,
    resolve_secret_value,
    write_json,
)
from onshape_export_manager.core.settings import AppPaths


class ConfigurationTests(unittest.TestCase):
    def test_default_config_files_are_created_and_loadable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            config = app.config_manager.load()

            self.assertTrue(app.config_manager.config_file.exists())
            self.assertTrue(app.config_manager.accounts_file.exists())
            self.assertTrue(app.config_manager.labels_file.exists())
            self.assertTrue(app.config_manager.export_profiles_file.exists())
            self.assertEqual(config.app.worker_count, 4)
            self.assertEqual(len(config.export_profiles.profiles), 9)

    def test_duplicate_account_names_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AccountsConfig.model_validate(
                {
                    "accounts": [
                        {"name": "prod", "access_key": "a", "secret_key": "s"},
                        {"name": "prod", "access_key": "a2", "secret_key": "s2"},
                    ]
                }
            )

    def test_label_references_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = AppPaths.from_base_dir(Path(tmp))
            manager = ConfigManager(paths)
            manager.ensure_default_files()
            write_json(
                manager.labels_file,
                {
                    "labels": [
                        {
                            "friendly_name": "Customer A",
                            "onshape_label_id": "123456789012345678901234",
                            "assigned_accounts": ["missing"],
                            "export_location": "exports",
                            "export_profile": "STL",
                            "scheduler": None,
                            "enabled": True,
                        }
                    ]
                },
            )

            with self.assertRaises(ConfigError):
                manager.load()

    def test_env_secret_references_resolve(self) -> None:
        self.assertEqual(resolve_secret_value("plain"), "plain")

    def test_default_json_is_human_editable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            data = json.loads(app.config_manager.config_file.read_text(encoding="utf-8"))

            self.assertIn("retry", data)
            self.assertIn("logging", data)

    def test_app_bootstrap_survives_invalid_config_for_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            write_json(app.config_manager.config_file, {"worker_count": 0})

            reloaded = create_app(Path(tmp))

            self.assertIsNone(reloaded.api_pool)


if __name__ == "__main__":
    unittest.main()
