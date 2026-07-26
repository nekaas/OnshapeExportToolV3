import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.profile_manager import (
    ExportProfileManager,
    ExportProfileManagerError,
    parse_format_list,
)


class ExportProfileManagerTests(unittest.TestCase):
    def test_parse_format_list_accepts_commas_and_spaces(self) -> None:
        formats = parse_format_list("stl, step 3mf")

        self.assertEqual([item.value for item in formats], ["stl", "step", "3mf"])

    def test_parse_format_list_rejects_unknown_format(self) -> None:
        with self.assertRaises(ExportProfileManagerError):
            parse_format_list("pdf")

    def test_add_profile_writes_valid_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            manager = ExportProfileManager(app.config_manager)

            profile = manager.add_profile("Shop Bundle", parse_format_list("stl,step,3mf"))
            config = app.config_manager.load()

            self.assertEqual(profile["formats"], ["stl", "step", "3mf"])
            self.assertIn(
                "Shop Bundle",
                [item.name for item in config.export_profiles.profiles],
            )

    def test_add_profile_requires_replace_for_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            manager = ExportProfileManager(app.config_manager)

            # "3MF" already exists in defaults, so adding without replace should fail
            with self.assertRaises(ExportProfileManagerError):
                manager.add_profile("3MF", parse_format_list("stl"))

            manager.add_profile("3MF", parse_format_list("stl,step"), replace=True)
            config = app.config_manager.load()
            mf3_profile = next(
                item for item in config.export_profiles.profiles if item.name == "3MF"
            )
            self.assertEqual([item.value for item in mf3_profile.formats], ["stl", "step"])


if __name__ == "__main__":
    unittest.main()
