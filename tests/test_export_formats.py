import unittest

from onshape_export_manager.core.export_formats import (
    default_options_for,
    list_format_definitions,
)
from onshape_export_manager.core.models import ExportFormat


class ExportFormatTests(unittest.TestCase):
    def test_part_studio_catalog_includes_common_export_formats(self) -> None:
        formats = [item.format for item in list_format_definitions(part_studio_only=True)]

        self.assertIn(ExportFormat.STL, formats)
        self.assertIn(ExportFormat.STEP, formats)
        self.assertIn(ExportFormat.OBJ, formats)
        self.assertIn(ExportFormat.IGES, formats)
        self.assertIn(ExportFormat.PARASOLID, formats)
        self.assertNotIn(ExportFormat.PDF, formats)
        self.assertNotIn(ExportFormat.CUSTOM, formats)

    def test_default_options_are_copied(self) -> None:
        options = default_options_for(ExportFormat.STEP)
        options["storeInDocument"] = True

        self.assertFalse(default_options_for(ExportFormat.STEP)["storeInDocument"])


if __name__ == "__main__":
    unittest.main()
