"""Export folder creation and filename helpers."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from onshape_export_manager.core.models import ExportFormat


def sanitize_filename(value: str) -> str:
    """Return a filesystem-safe name."""
    safe = re.sub(r'[\\/*?:"<>|]', "", value).strip().replace(" ", "_")
    return safe or "untitled"


def unique_path(path: Path) -> Path:
    """Return a non-existing path by appending a numeric suffix if needed."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class FolderManager:
    """Creates timestamped export folders without overwriting prior exports."""

    def __init__(
        self,
        timestamp_format: str = "%Y-%m-%d_%H%M%S",
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.timestamp_format = timestamp_format
        self._now_fn = now_fn or datetime.now

    def create_export_folder(self, destination: Path, label_name: str) -> Path:
        """Create a unique timestamped folder for one export run."""
        stamp = self._now_fn().strftime(self.timestamp_format)
        folder = destination / sanitize_filename(label_name) / stamp
        folder = unique_path(folder)
        folder.mkdir(parents=True, exist_ok=False)
        return folder

    def create_format_folder(self, export_folder: Path, export_format: ExportFormat) -> Path:
        """Create or return the subfolder for an export format."""
        folder = export_folder / format_folder_name(export_format)
        folder.mkdir(parents=True, exist_ok=True)
        return folder


def format_folder_name(export_format: ExportFormat) -> str:
    """Return the folder name used for a given export format."""
    return export_format.value.upper().replace("-", "_")
