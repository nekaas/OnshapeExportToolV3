"""Path and process settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Filesystem layout for the application."""

    base_dir: Path
    package_dir: Path
    config_dir: Path
    exports_dir: Path
    logs_dir: Path
    database_dir: Path
    database_file: Path
    ui_dir: Path
    backups_dir: Path

    @classmethod
    def from_base_dir(cls, base_dir: str | Path | None = None) -> "AppPaths":
        root = Path(base_dir) if base_dir is not None else Path.cwd()
        package_dir = root / "onshape_export_manager"
        return cls(
            base_dir=root,
            package_dir=package_dir,
            config_dir=package_dir / "config",
            exports_dir=package_dir / "exports",
            logs_dir=package_dir / "logs",
            database_dir=package_dir / "database",
            database_file=package_dir / "database" / "exports.db",
            ui_dir=package_dir / "ui",
            backups_dir=package_dir / "backups",
        )


def ensure_project_directories(paths: AppPaths) -> None:
    """Create runtime directories used by all interfaces."""
    for directory in (
        paths.config_dir,
        paths.exports_dir,
        paths.logs_dir,
        paths.database_dir,
        paths.backups_dir,
        paths.ui_dir / "templates",
        paths.ui_dir / "static",
    ):
        directory.mkdir(parents=True, exist_ok=True)
