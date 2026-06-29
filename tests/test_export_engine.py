import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any

from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core.database import Database
from onshape_export_manager.core.export_engine import ExportEngine
from onshape_export_manager.core.models import (
    ExportFormat,
    ExportJobRequest,
    ExportProfile,
    LabelDefinition,
    OnshapeAccount,
)


class FakeExportClient:
    def __init__(self) -> None:
        self.calls: list[tuple[ExportFormat, Path, dict[str, Any] | None]] = []

    def fetch_documents_by_label(self, label_id: str, start_iso: str, end_iso: str):
        return [
            {
                "id": "doc-1",
                "name": "Bracket",
                "defaultWorkspace": {"id": "wid-1"},
            }
        ]

    def get_default_workspace_id(self, document: dict[str, Any]) -> str:
        return "wid-1"

    def list_part_studios(self, doc_id: str, workspace_id: str):
        return [{"id": "eid-1", "name": "Main", "elementType": "PARTSTUDIO"}]

    def export_part_studio(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        save_path: Path,
        *,
        export_format: ExportFormat,
        options: dict[str, Any] | None = None,
    ) -> Path:
        self.calls.append((export_format, save_path, options))
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(f"{export_format.value} data".encode())
        return save_path


class ExportEngineTests(unittest.TestCase):
    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_manual_export_writes_multiple_formats_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "exports"
            database = self.make_database()
            account = OnshapeAccount(name="prod", access_key="a", secret_key="s")
            pool = ApiPool([account])
            fake_client = FakeExportClient()
            engine = ExportEngine(
                api_pool=pool,
                database=database,
                client_factory=lambda _: fake_client,  # type: ignore[arg-type]
            )
            request = ExportJobRequest(
                label=LabelDefinition(
                    friendly_name="Customer A",
                    onshape_label_id="123456789012345678901234",
                    assigned_accounts=["prod"],
                    export_location=destination,
                    export_profile="Multi Format",
                ),
                profile=ExportProfile(
                    name="Multi Format",
                    formats=[
                        ExportFormat.STL,
                        ExportFormat.STEP,
                        ExportFormat.OBJ,
                        ExportFormat.IGES,
                    ],
                    options={"mode": "binary", "step": {"stepVersionString": "AP242"}},
                ),
                start_iso="2026-06-25T00:00:00+00:00",
                end_iso="2026-06-25T23:59:59+00:00",
            )

            result = asyncio.run(engine.run_manual_export(request))

            self.assertTrue(result.success)
            self.assertEqual(len(result.exported_files), 4)
            self.assertEqual(
                [call[0] for call in fake_client.calls],
                [ExportFormat.STL, ExportFormat.STEP, ExportFormat.OBJ, ExportFormat.IGES],
            )
            self.assertTrue((result.export_folder / "STL").exists())
            self.assertTrue((result.export_folder / "STEP").exists())
            self.assertTrue((result.export_folder / "IGES").exists())
            history = database.list_export_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(len(history[0].exported_files), 4)
            self.assertTrue(history[0].success)

    def test_manual_export_records_part_studio_failure(self) -> None:
        class NoPartStudioClient(FakeExportClient):
            def list_part_studios(self, doc_id: str, workspace_id: str):
                return []

        with tempfile.TemporaryDirectory() as tmp:
            database = self.make_database()
            account = OnshapeAccount(name="prod", access_key="a", secret_key="s")
            engine = ExportEngine(
                api_pool=ApiPool([account]),
                database=database,
                client_factory=lambda _: NoPartStudioClient(),  # type: ignore[arg-type]
            )
            request = ExportJobRequest(
                label=LabelDefinition(
                    friendly_name="Customer A",
                    onshape_label_id="123456789012345678901234",
                    assigned_accounts=["prod"],
                    export_location=Path(tmp),
                    export_profile="STL",
                ),
                profile=ExportProfile(name="STL", formats=[ExportFormat.STL]),
                start_iso="2026-06-25T00:00:00+00:00",
                end_iso="2026-06-25T23:59:59+00:00",
            )

            result = asyncio.run(engine.run_manual_export(request))

            self.assertFalse(result.success)
            self.assertIn("no Part Studios", result.failed_items[0])


if __name__ == "__main__":
    unittest.main()
