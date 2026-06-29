"""Application bootstrap for Onshape Export Manager."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core.audit import AuditService, TelemetryStore
from onshape_export_manager.core.configuration import ConfigError, ConfigManager
from onshape_export_manager.core.database import Database
from onshape_export_manager.core.events import EventBus
from onshape_export_manager.core.export_engine import ExportEngine
from onshape_export_manager.core.folder_manager import FolderManager
from onshape_export_manager.core.logger import configure_logging
from onshape_export_manager.core.notifications import NotificationService
from onshape_export_manager.core.onshape_client import RequestRetryPolicy
from onshape_export_manager.core.queue_manager import QueueManager, QueueRetryPolicy
from onshape_export_manager.core.retry import retry_statuses_from_config
from onshape_export_manager.core.scheduler import SchedulerService
from onshape_export_manager.core.settings import AppPaths, ensure_project_directories


@dataclass
class Application:
    """Runtime container shared by CLI, web, and terminal entrypoints."""

    paths: AppPaths
    config_manager: ConfigManager
    database: Database
    api_pool: ApiPool | None = None
    queue_manager: QueueManager | None = None
    scheduler: SchedulerService | None = None
    event_bus: EventBus | None = None
    audit: AuditService | None = None
    telemetry: TelemetryStore | None = None
    notifications: NotificationService | None = None

    def bootstrap(self) -> "Application":
        """Create required directories and initialize process-wide services."""
        ensure_project_directories(self.paths)
        self.config_manager.ensure_default_files()
        self._configure_logging()
        self.database.initialize()
        # The event bus is the backbone for live updates, audit, and AI-readiness.
        # It is created unconditionally so every subsystem can publish even if
        # configuration is incomplete.
        self.event_bus = EventBus()
        self.audit = AuditService(self.database, self.event_bus)
        self.audit.start()
        self.telemetry = TelemetryStore(self.database)
        # Notifications subscribe to the same bus; channels are configured via
        # the browser. The delivery thread is started lazily by the web/CLI
        # entrypoint (start_notifications) so short-lived CLI invocations and
        # tests do not spawn a background thread they never use.
        self.notifications = NotificationService(self.config_manager, self.event_bus)
        try:
            self.queue_manager = self.create_queue_manager()
            self.scheduler = SchedulerService(self.database, self.queue_manager)
        except (ConfigError, ValidationError):
            self.queue_manager = None
            self.scheduler = None
        try:
            self.api_pool = self.create_api_pool()
        except (ConfigError, ValidationError):
            self.api_pool = None
        return self

    def _configure_logging(self) -> None:
        """Configure logging from validated config, falling back to defaults."""
        level = "INFO"
        try:
            config = self.config_manager.load()
            level = config.app.logging.level
        except (ConfigError, ValidationError):
            pass
        configure_logging(self.paths.logs_dir, level)

    def create_api_pool(self, *, resolve_env: bool = False) -> ApiPool:
        """Create an API pool from validated account configuration."""
        config = self.config_manager.load()
        return ApiPool(
            config.runtime_accounts(resolve_env=resolve_env),
            database=self.database,
        )

    def create_queue_manager(self) -> QueueManager:
        """Create the export queue manager from retry settings."""
        config = self.config_manager.load()
        return QueueManager(
            self.database,
            retry_policy=QueueRetryPolicy(
                max_attempts=config.app.retry.max_attempts,
                backoff_base_seconds=config.app.retry.backoff_base_seconds,
                backoff_max_seconds=config.app.retry.backoff_max_seconds,
                retry_http_statuses=retry_statuses_from_config(
                    config.app.retry.retry_http_statuses
                ),
            ),
        )

    def create_export_engine(self, *, resolve_env: bool = True) -> ExportEngine:
        """Create the export engine from validated runtime configuration."""
        config = self.config_manager.load()
        return ExportEngine(
            api_pool=self.create_api_pool(resolve_env=resolve_env),
            database=self.database,
            base_url=config.app.onshape_base_url,
            folder_manager=FolderManager(config.app.folders.timestamp_format),
            retry_policy=RequestRetryPolicy(
                max_attempts=config.app.retry.max_attempts,
                backoff_base_seconds=config.app.retry.backoff_base_seconds,
                backoff_max_seconds=config.app.retry.backoff_max_seconds,
                retry_http_statuses=retry_statuses_from_config(
                    config.app.retry.retry_http_statuses
                ),
                request_timeout_seconds=config.app.request_timeout_seconds,
                export_timeout_seconds=config.app.export_timeout_seconds,
            ),
        )


def create_app(base_dir: str | Path | None = None) -> Application:
    """Create the application container."""
    paths = AppPaths.from_base_dir(base_dir)
    return Application(
        paths=paths,
        config_manager=ConfigManager(paths),
        database=Database(paths.database_file),
    ).bootstrap()


def main() -> None:
    """Minimal app bootstrap entrypoint for Stage 1 verification."""
    app = create_app()
    print(f"Onshape Export Manager initialized at {app.paths.package_dir}")


if __name__ == "__main__":
    main()
