"""Export folder creation and filename helpers.

Directory structure:
    exports/{organization}/{label}/{date_batch}/{file}.{ext}

No format subfolder — the file extension IS the format indicator.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path


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
    """Creates date-batched export folders: org/label/YYYY-MM-DD/."""

    def __init__(
        self,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def create_export_folder(
        self,
        destination: Path,
        organization: str,
        label_name: str,
    ) -> Path:
        """Create: {destination}/{org}/{label}/{YYYY-MM-DD}/ (unique, no overwrites).

        Returns the batch folder where all files for this export run land.
        """
        org_safe = sanitize_filename(organization)
        label_safe = sanitize_filename(label_name)
        date_str = self._now_fn().strftime("%Y-%m-%d")
        batch = destination / org_safe / label_safe / date_str
        batch = unique_path(batch)
        batch.mkdir(parents=True, exist_ok=False)
        return batch
