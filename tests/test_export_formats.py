import unittest

from onshape_export_manager.core.export_formats import (
    default_options_for,
    list_format_definitions,
)
from onshape_export_manager.core.models import ExportFormat


class ExportFormatTests(unittest.TestCase):
    def test_all_eight_formats_supported(self) -> None:
        formats = [item.format for item in list_format_definitions()]

        self.assertIn(ExportFormat.STL, formats)
        self.assertIn(ExportFormat.STEP, formats)
        self.assertIn(ExportFormat.MF3, formats)
        self.assertIn(ExportFormat.PARASOLID, formats)
        self.assertIn(ExportFormat.OBJ, formats)
        self.assertIn(ExportFormat.GLTF, formats)
        self.assertIn(ExportFormat.DXF, formats)
        self.assertEqual(len(formats), 8, "8 export formats supported")

    def test_default_options_are_copied(self) -> None:
        options = default_options_for(ExportFormat.STEP)
        options["storeInDocument"] = True

        self.assertFalse(default_options_for(ExportFormat.STEP)["storeInDocument"])


if __name__ == "__main__":
    unittest.main()
