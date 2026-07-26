"""Export orchestration service — lean, fast, flat output structure."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout, as_completed
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
from onshape_export_manager.core.provider import CredentialProvider


class ExportEngineError(RuntimeError):
    """Base export engine error."""


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
    timed_out: int = 0


ClientFactory = Callable[[OnshapeAccount], OnshapeClient]

# Per-format timeout in seconds (prevents hung exports)
FORMAT_TIMEOUTS: dict[ExportFormat, int] = {
    ExportFormat.STL: 120,
    ExportFormat.STEP: 180,
    ExportFormat.MF3: 120,
    ExportFormat.PARASOLID: 180,
    ExportFormat.OBJ: 120,
    ExportFormat.GLTF: 150,
    ExportFormat.DXF: 90,
    ExportFormat.NATIVE: 300,
}


class ExportEngine:
    """Fast parallel export engine with flat org/label/date output structure."""

    def __init__(
        self,
        *,
        api_pool: ApiPool | CredentialProvider,
        database: Database,
        base_url: str = "https://cad.onshape.com/api/v6",
        folder_manager: FolderManager | None = None,
        retry_policy: RequestRetryPolicy | None = None,
        client_factory: ClientFactory | None = None,
        max_workers: int = 4,
    ) -> None:
        self.api_pool = api_pool
        self.database = database
        self.base_url = base_url
        self.folder_manager = folder_manager or FolderManager()
        self.retry_policy = retry_policy or RequestRetryPolicy()
        self.client_factory = client_factory or self._default_client_factory
        self.max_workers = max_workers
        self.logger = get_logger(EXPORT_LOGGER)
        # Cache workspace IDs per document to avoid redundant API calls
        self._ws_cache: dict[str, str] = {}

    async def run_manual_export(self, request: ExportJobRequest) -> ExportResult:
        """Run a manual export — discover docs, then export all Part Studios in parallel."""
        started_monotonic = time.monotonic()
        started_at = datetime.now(timezone.utc)
        lease = self.api_pool.lease(request.label.assigned_accounts)
        client = self.client_factory(lease.account)
        destination = request.destination or request.label.export_location
        org = request.organization or "default"
        result = ExportResult(success=False, account_name=lease.account.name)
        self._ws_cache.clear()
        self.logger.info(
            "Export start org=%s label=%s profile=%s account=%s",
            org, request.label.friendly_name, request.profile.name, lease.account.name,
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
                    destination, org, request.label.friendly_name,
                )
                self._export_all(client, request, documents, result)

            result.success = not result.failed_items
            self.api_pool.record_success(lease.account.name)
        except Exception as exc:
            result.failed_items.append(str(exc))
            result.success = False
            self.api_pool.record_failure(lease.account.name, type(exc).__name__)
        finally:
            duration = time.monotonic() - started_monotonic
            log_export_summary(
                _log_level(result.success),
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

    def _export_all(
        self,
        client: OnshapeClient,
        request: ExportJobRequest,
        documents: list[dict[str, Any]],
        result: ExportResult,
    ) -> None:
        """Discover Part Studios across all documents, then export them in parallel."""
        assert result.export_folder is not None

        # Phase 1: collect all (doc, element, format) work items
        work_items: list[_ExportTask] = []
        for document in documents:
            doc_id = str(document.get("id") or "")
            doc_name = sanitize_filename(str(document.get("name") or doc_id or "document"))
            if not doc_id:
                result.failed_items.append(f"{doc_name}: missing document id")
                continue
            try:
                ws_id = self._get_workspace(client, document, doc_id)
                elements = client.list_part_studios(doc_id, ws_id)
                if not elements:
                    result.failed_items.append(f"{doc_name}: no Part Studios found")
                    continue
                for element in elements:
                    eid = str(element.get("id") or "")
                    ename = sanitize_filename(str(element.get("name") or eid))
                    if not eid:
                        result.failed_items.append(f"{doc_name}: Part Studio missing id")
                        continue
                    for fmt in request.profile.formats:
                        work_items.append(
                            _ExportTask(
                                doc_id=doc_id, doc_name=doc_name,
                                workspace_id=ws_id,
                                element_id=eid, element_name=ename,
                                export_format=fmt,
                            )
                        )
            except Exception as exc:
                result.failed_items.append(f"{doc_name}: {exc}")

        # Phase 2: export all work items in parallel
        self._run_parallel(client, request, work_items, result.export_folder, result)

    def _run_parallel(
        self,
        client: OnshapeClient,
        request: ExportJobRequest,
        tasks: list[_ExportTask],
        batch_folder: Path,
        result: ExportResult,
    ) -> None:
        """Export tasks in parallel using a thread pool, with per-format timeouts."""
        if not tasks:
            return

        workers = min(self.max_workers, len(tasks))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures: dict[Future, _ExportTask] = {
                pool.submit(self._export_one, client, request, task, batch_folder): task
                for task in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                timeout = FORMAT_TIMEOUTS.get(task.export_format, 180)
                try:
                    path = future.result(timeout=timeout)
                    if path is not None:
                        result.exported_files.append(path)
                except FutureTimeout:
                    result.timed_out += 1
                    result.failed_items.append(
                        f"{task.doc_name}/{task.element_name}/{task.export_format.value}: "
                        f"timed out after {timeout}s — file may be too large or API unresponsive"
                    )
                    future.cancel()
                except Exception as exc:
                    result.failed_items.append(
                        f"{task.doc_name}/{task.element_name}/{task.export_format.value}: {exc}"
                    )

    def _export_one(
        self,
        client: OnshapeClient,
        request: ExportJobRequest,
        task: _ExportTask,
        batch_folder: Path,
    ) -> Path | None:
        """Export a single Part Studio in a single format to the batch folder."""
        definition = get_format_definition(task.export_format)
        doc_suffix = task.doc_id[-8:] if len(task.doc_id) >= 8 else task.doc_id
        filename = (
            f"{task.doc_name}__{task.element_name}__{doc_suffix}"
            f"{definition.default_extension}"
        )
        save_path = unique_path(batch_folder / filename)
        options = default_options_for(task.export_format)
        options.update(_format_options_for(request.profile.options, task.export_format))
        return client.export_part_studio(
            task.doc_id, task.workspace_id, task.element_id,
            save_path,
            export_format=task.export_format,
            options=options,
        )

    def _get_workspace(
        self, client: OnshapeClient, document: dict[str, Any], doc_id: str,
    ) -> str:
        """Return cached workspace ID for a document."""
        if doc_id not in self._ws_cache:
            self._ws_cache[doc_id] = client.get_default_workspace_id(document)
        return self._ws_cache[doc_id]

    def _default_client_factory(self, account: OnshapeAccount) -> OnshapeClient:
        return OnshapeClient(
            account=account,
            base_url=self.base_url,
            retry_policy=self.retry_policy,
            api_pool=self.api_pool,
        )


# ── Internal helpers ────────────────────────────────────────────────────────

@dataclass(slots=True)
class _ExportTask:
    """A single (part studio, format) export to run."""
    doc_id: str
    doc_name: str
    workspace_id: str
    element_id: str
    element_name: str
    export_format: ExportFormat


def _format_options_for(options: dict[str, object], fmt: ExportFormat) -> dict[str, object]:
    """Extract options relevant to one format from a profile's option map."""
    per_format = options.get(fmt.value)
    merged: dict[str, object] = {}
    if isinstance(per_format, dict):
        merged.update(per_format)
    for key, value in options.items():
        if key not in {item.value for item in ExportFormat}:
            merged.setdefault(key, value)
    return merged


def _log_level(success: bool) -> int:
    import logging
    return logging.INFO if success else logging.ERROR
