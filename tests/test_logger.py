import logging
import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.core.logger import (
    EXPORT_LOGGER,
    ExportLogContext,
    configure_logging,
    get_logger,
    log_export_summary,
)


class LoggerTests(unittest.TestCase):
    def test_configure_logging_creates_named_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            configure_logging(log_dir)

            get_logger(EXPORT_LOGGER).info("export hello")
            logging.getLogger("onshape_export_manager.test").error("boom")
            logging.shutdown()

            self.assertTrue((log_dir / "app.log").exists())
            self.assertTrue((log_dir / "export.log").exists())
            self.assertTrue((log_dir / "errors.log").exists())
            self.assertIn("export hello", (log_dir / "export.log").read_text(encoding="utf-8"))
            self.assertIn("boom", (log_dir / "errors.log").read_text(encoding="utf-8"))

    def test_export_log_context_message(self) -> None:
        context = ExportLogContext(
            label="Customer A",
            account="prod",
            export_profile="STL",
            files_exported=2,
            failed_files=1,
            retries=3,
            duration_seconds=1.23456,
        )

        self.assertIn("label=Customer A", context.to_message())
        self.assertIn("duration_seconds=1.235", context.to_message())

    def test_log_export_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            configure_logging(log_dir)
            log_export_summary(
                logging.INFO,
                ExportLogContext(label="A", account="prod", export_profile="STL"),
            )
            logging.shutdown()

            self.assertIn("profile=STL", (log_dir / "export.log").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
