"""Export orchestration service."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core.database import Database, ExportHistoryEntry
from onshape_export_manager.core.export_formats import (
    default_options_for,
    get_format_definition,
)
from onshape_export_manager.core.folder_manager import FolderManager, sanitize_filename, unique_path
from onshape_export_manager.core.logger import EXPORT_LOGGER, ExportLogContext, get_logger, log_export_summary
from onshape_export_manager.core.models import ExportFormat, ExportJobRequest, OnshapeAccount
from onshape_export_manager.core.onshape_client import OnshapeClient, RequestRetryPolicy


class ExportEngineError(RuntimeError):
    """Base export engine error."""


class ExportFormatNotImplementedError(ExportEngineError):
    """Raised when a requested format does not yet have an export handler."""


@dataclass(slots=True)
class ExportResult:
    """Summary of a completed export request."""

    success: bool
    exported_files: list[Path] = field(default_factory=list)
    failed_items: list[str] = field(default_factory=list)
    skipped_items: list[str] = field(default_factory=list)
    export_folder: Path | None = None
    account_name: str | None = None
    history_id: int | None = None
    documents_seen: int = 0


ClientFactory = Callable[[OnshapeAccount], OnshapeClient]


class ExportEngine:
    """Coordinates account selection, document discovery, and file exports."""

    def __init__(
        self,
        *,
        api_pool: ApiPool,
        database: Database,
        base_url: str = "https://cad.onshape.com/api/v6",
        folder_manager: FolderManager | None = None,
        retry_policy: RequestRetryPolicy | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.api_pool = api_pool
        self.database = database
        self.base_url = base_url
        self.folder_manager = folder_manager or FolderManager()
        self.retry_policy = retry_policy or RequestRetryPolicy()
        self.client_factory = client_factory or self._default_client_factory
        self.logger = get_logger(EXPORT_LOGGER)

    async def run_manual_export(self, request: ExportJobRequest) -> ExportResult:
        """Run a manual export request.

        This method is async to fit the future queue/web/TUI execution model.
        Stage 6 performs the work synchronously underneath so the tested
        proof-of-concept behavior stays straightforward.
        """
        started_monotonic = time.monotonic()
        started_at = datetime.now(timezone.utc)
        lease = self.api_pool.lease(request.label.assigned_accounts)
        client = self.client_factory(lease.account)
        destination = request.destination or request.label.export_location
        result = ExportResult(success=False, account_name=lease.account.name)
        self.logger.info(
            "Starting manual export label=%s profile=%s account=%s",
            request.label.friendly_name,
            request.profile.name,
            lease.account.name,
        )

        try:
            documents = client.fetch_documents_by_label(
                request.label.onshape_label_id,
                request.start_iso,
                request.end_iso,
            )
            result.documents_seen = len(documents)
            if documents:
                result.export_folder = self.folder_manager.create_export_folder(
                    destination,
                    request.label.friendly_name,
                )
                self._export_documents(client, request, documents, result)

            result.success = not result.failed_items
            self.api_pool.record_success(lease.account.name)
        except Exception as exc:
            result.failed_items.append(str(exc))
            result.success = False
            self.api_pool.record_failure(lease.account.name, type(exc).__name__)
        finally:
            duration = time.monotonic() - started_monotonic
            log_export_summary(
                logging_level(result.success),
                ExportLogContext(
                    label=request.label.friendly_name,
                    account=lease.account.name,
                    export_profile=request.profile.name,
                    files_exported=len(result.exported_files),
                    failed_files=len(result.failed_items),
                    retries=lease.account.failure_count,
                    duration_seconds=duration,
                ),
            )
            result.history_id = self.database.add_export_history(
                ExportHistoryEntry(
                    account_name=lease.account.name,
                    label_name=request.label.friendly_name,
                    export_profile=request.profile.name,
                    exported_files=[str(path) for path in result.exported_files],
                    duration_seconds=duration,
                    success=result.success,
                    failures=result.failed_items,
                    retry_count=lease.account.failure_count,
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                )
            )

        return result

    def _export_documents(
        self,
        client: OnshapeClient,
        request: ExportJobRequest,
        documents: list[dict[str, Any]],
        result: ExportResult,
    ) -> None:
        assert result.export_folder is not None
        for document in documents:
            doc_id = str(document.get("id") or "")
            doc_name = sanitize_filename(str(document.get("name") or doc_id or "document"))
            if not doc_id:
                result.failed_items.append(f"{doc_name}: missing document id")
                continue

            try:
                workspace_id = client.get_default_workspace_id(document)
                part_studios = client.list_part_studios(doc_id, workspace_id)
                if not part_studios:
                    result.failed_items.append(f"{doc_name}: no Part Studios found")
                    continue

                # Preserve proof-of-concept behavior: export the first Part Studio.
                element = part_studios[0]
                element_id = str(element.get("id") or "")
                element_name = sanitize_filename(str(element.get("name") or element_id))
                if not element_id:
                    result.failed_items.append(f"{doc_name}: Part Studio is missing id")
                    continue

                for export_format in request.profile.formats:
                    try:
                        path = self._export_part_studio_format(
                            client,
                            request,
                            export_format,
                            doc_id,
                            workspace_id,
                            element_id,
                            doc_name,
                            element_name,
                            result.export_folder,
                        )
                    except ExportFormatNotImplementedError as exc:
                        result.skipped_items.append(str(exc))
                    except Exception as exc:
                        result.failed_items.append(
                            f"{doc_name}/{element_name}/{export_format.value}: {exc}"
                        )
                    else:
                        if path is not None:
                            result.exported_files.append(path)
            except Exception as exc:
                result.failed_items.append(f"{doc_name}: {exc}")

    def _export_part_studio_format(
        self,
        client: OnshapeClient,
        request: ExportJobRequest,
        export_format: ExportFormat,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        doc_name: str,
        element_name: str,
        export_folder: Path,
    ) -> Path | None:
        definition = get_format_definition(export_format)
        if export_format == ExportFormat.CUSTOM:
            raise ExportFormatNotImplementedError(
                "Custom export needs a configured plugin or explicit handler."
            )
        if not definition.supports_part_studio:
            raise ExportFormatNotImplementedError(
                f"{definition.display_name} export is not a Part Studio export."
            )
        format_folder = self.folder_manager.create_format_folder(export_folder, export_format)
        filename = f"{doc_name}__{element_name}{definition.default_extension}"
        save_path = unique_path(format_folder / filename)
        options = default_options_for(export_format)
        options.update(format_options_for(request.profile.options, export_format))
        return client.export_part_studio(
            doc_id,
            workspace_id,
            element_id,
            save_path,
            export_format=export_format,
            options=options,
        )

    def _default_client_factory(self, account: OnshapeAccount) -> OnshapeClient:
        return OnshapeClient(
            account=account,
            base_url=self.base_url,
            retry_policy=self.retry_policy,
            api_pool=self.api_pool,
        )


def format_options_for(options: dict[str, object], export_format: ExportFormat) -> dict[str, object]:
    """Extract options relevant to one format from a profile's option map."""
    per_format = options.get(export_format.value)
    merged: dict[str, object] = {}
    if isinstance(per_format, dict):
        merged.update(per_format)
    for key, value in options.items():
        if key not in {item.value for item in ExportFormat}:
            merged.setdefault(key, value)
    return merged


def logging_level(success: bool) -> int:
    import logging

    return logging.INFO if success else logging.ERROR
