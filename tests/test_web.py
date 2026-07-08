import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.web import build_dashboard_context


class WebTests(unittest.TestCase):
    def test_dashboard_context_uses_application_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))

            context = build_dashboard_context(app)

            self.assertEqual(context["counts"]["accounts"], 0)
            self.assertEqual(context["counts"]["labels"], 0)
            self.assertEqual(context["counts"]["export_profiles"], 8)
            self.assertEqual(context["counts"]["queue_size"], 0)
            self.assertIn("database", context)
            self.assertIn("profiles", context)
            self.assertIn("available_formats", context)
            self.assertIn(
                "step",
                [item.format.value for item in context["available_formats"]],
            )


if __name__ == "__main__":
    unittest.main()
