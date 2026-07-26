import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from onshape_export_manager.core.folder_manager import (
    FolderManager,
    sanitize_filename,
    unique_path,
)
from onshape_export_manager.core.models import ExportFormat


class FolderManagerTests(unittest.TestCase):
    def test_sanitize_filename_removes_unsafe_characters(self) -> None:
        self.assertEqual(sanitize_filename('A/B:C* "Name"'), "ABC_Name")
        self.assertEqual(sanitize_filename(''), "untitled")

    def test_unique_path_adds_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.stl"
            path.write_text("first", encoding="utf-8")

            self.assertEqual(unique_path(path), Path(tmp) / "file_2.stl")

    def test_create_export_folder_never_overwrites_same_timestamp(self) -> None:
        now = datetime(2026, 6, 25, 12, 30, 0)
        manager = FolderManager(now_fn=lambda: now)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = manager.create_export_folder(root, "MyOrg", "Customer A")
            second = manager.create_export_folder(root, "MyOrg", "Customer A")

            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertEqual(second.name, f"{first.name}_2")

    def test_export_folder_structure(self) -> None:
        """Export folder is org/label/date with no format subfolder."""
        now = datetime(2026, 7, 10, 12, 0, 0)
        manager = FolderManager(now_fn=lambda: now)
        with tempfile.TemporaryDirectory() as tmp:
            folder = manager.create_export_folder(Path(tmp), "Acme", "Widgets")
            self.assertTrue(folder.exists())
            # Structure: tmp/Acme/Widgets/2026-07-10
            self.assertEqual(folder.parent.name, "Widgets")
            self.assertEqual(folder.parent.parent.name, "Acme")
            self.assertEqual(folder.name, "2026-07-10")


if __name__ == "__main__":
    unittest.main()
