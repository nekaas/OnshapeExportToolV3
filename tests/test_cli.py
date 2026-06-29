import unittest
from datetime import timezone

from onshape_export_manager.cli import export_window, parse_cli_datetime


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
