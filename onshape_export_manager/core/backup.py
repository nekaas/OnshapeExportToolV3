"""Backup and restore for configuration, database, history, and logs.

Creates compressed ZIP snapshots of the application's state (config JSON, the
SQLite database, and optionally logs) so a headless appliance can be backed up
and restored entirely from the Web UI. Supports retention pruning and integrity
verification.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from onshape_export_manager.core.logger import APP_LOGGER, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.core.settings import AppPaths

BACKUP_PREFIX = "oem-backup-"
BACKUP_SUFFIX = ".zip"


@dataclass(frozen=True, slots=True)
class BackupInfo:
    """Metadata describing one backup archive."""

    name: str
    path: Path
    size_bytes: int
    created_at: datetime
    entry_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_human": _human_bytes(self.size_bytes),
            "created_at": self.created_at.isoformat(),
            "entry_count": self.entry_count,
        }


class BackupError(RuntimeError):
    """Raised when a backup or restore operation fails."""


class BackupManager:
    """Creates, lists, restores, and prunes application backups."""

    def __init__(self, paths: "AppPaths") -> None:
        self.paths = paths
        self.backups_dir = getattr(paths, "backups_dir", paths.package_dir / "backups")
        self.logger = get_logger(APP_LOGGER)

    def create_backup(self, *, include_logs: bool = False, label: str = "") -> BackupInfo:
        """Create a compressed backup archive and return its metadata."""
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        suffix = f"-{_safe_label(label)}" if label else ""
        archive_path = self.backups_dir / f"{BACKUP_PREFIX}{stamp}{suffix}{BACKUP_SUFFIX}"

        sources = self._backup_sources(include_logs=include_logs)
        entry_count = 0
        try:
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for arcname, source in sources:
                    if source.is_dir():
                        for file in sorted(source.rglob("*")):
                            if file.is_file():
                                archive.write(file, f"{arcname}/{file.relative_to(source).as_posix()}")
                                entry_count += 1
                    elif source.is_file():
                        archive.write(source, arcname)
                        entry_count += 1
        except OSError as exc:
            archive_path.unlink(missing_ok=True)
            raise BackupError(f"Failed to create backup: {exc}") from exc

        info = BackupInfo(
            name=archive_path.name,
            path=archive_path,
            size_bytes=archive_path.stat().st_size,
            created_at=datetime.now(timezone.utc),
            entry_count=entry_count,
        )
        self.logger.info("Created backup %s (%d entries, %s)", info.name, entry_count,
                         _human_bytes(info.size_bytes))
        return info

    def list_backups(self) -> list[BackupInfo]:
        """List available backups, newest first."""
        if not self.backups_dir.exists():
            return []
        infos: list[BackupInfo] = []
        for path in self.backups_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"):
            try:
                stat = path.stat()
                with zipfile.ZipFile(path) as archive:
                    entry_count = len(archive.namelist())
            except (OSError, zipfile.BadZipFile):
                continue
            infos.append(
                BackupInfo(
                    name=path.name,
                    path=path,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    entry_count=entry_count,
                )
            )
        return sorted(infos, key=lambda item: item.created_at, reverse=True)

    def verify_backup(self, name: str) -> bool:
        """Return True if the named backup archive is intact."""
        path = self._resolve(name)
        try:
            with zipfile.ZipFile(path) as archive:
                return archive.testzip() is None
        except (OSError, zipfile.BadZipFile):
            return False

    def restore_backup(self, name: str, *, restore_logs: bool = False) -> int:
        """Restore configuration and database from a backup. Returns entries restored.

        A safety snapshot of the current state is taken before overwriting so a
        failed restore can be undone.
        """
        path = self._resolve(name)
        if not self.verify_backup(name):
            raise BackupError(f"Backup '{name}' is corrupt or unreadable")

        # Safety net before we overwrite anything.
        self.create_backup(label="pre-restore")

        restored = 0
        try:
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if member.startswith("logs/") and not restore_logs:
                        continue
                    target = self._restore_target(member)
                    if target is None:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as src, target.open("wb") as dst:
                        dst.write(src.read())
                    restored += 1
        except (OSError, zipfile.BadZipFile) as exc:
            raise BackupError(f"Failed to restore backup: {exc}") from exc

        self.logger.warning("Restored %d entries from backup %s", restored, name)
        return restored

    def delete_backup(self, name: str) -> None:
        """Delete a backup archive."""
        self._resolve(name).unlink(missing_ok=True)
        self.logger.info("Deleted backup %s", name)

    def prune_backups(self, keep: int = 10) -> list[str]:
        """Keep the newest ``keep`` backups, deleting older ones."""
        removed: list[str] = []
        for info in self.list_backups()[keep:]:
            info.path.unlink(missing_ok=True)
            removed.append(info.name)
        if removed:
            self.logger.info("Pruned %d old backups", len(removed))
        return removed

    def _backup_sources(self, *, include_logs: bool) -> list[tuple[str, Path]]:
        sources: list[tuple[str, Path]] = [("config", self.paths.config_dir)]
        if self.paths.database_file.exists():
            sources.append((f"database/{self.paths.database_file.name}", self.paths.database_file))
        if include_logs:
            sources.append(("logs", self.paths.logs_dir))
        return sources

    def _restore_target(self, member: str) -> Path | None:
        if member.startswith("config/"):
            return self.paths.config_dir / member[len("config/"):]
        if member.startswith("database/"):
            return self.paths.database_dir / member[len("database/"):]
        if member.startswith("logs/"):
            return self.paths.logs_dir / member[len("logs/"):]
        return None

    def _resolve(self, name: str) -> Path:
        # Prevent path traversal: only accept a bare filename in the backups dir.
        safe = Path(name).name
        path = self.backups_dir / safe
        if not path.exists():
            raise BackupError(f"Backup '{safe}' not found")
        return path


def _safe_label(label: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label).strip("-") or "manual"


def _human_bytes(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
