"""Structured, rotating, colorized logging for the application.

This module configures process-wide logging with:

- per-area log files (app, api, export, scheduler, queue, web, worker)
- size-based rotation so log files never grow without bound
- a dedicated ``errors.log`` capturing every WARNING/ERROR across the app
- optional JSON-structured output for machine ingestion
- ANSI-colorized console output when attached to a TTY
- lazy file handles (``delay=True``) so unused log files are never created
  and never hold OS file locks open

The handler set is fully rebuilt on each :func:`configure_logging` call and can
be torn down with :func:`shutdown_logging`, which keeps repeated bootstraps
(tests, embedded use) free of leaked file descriptors.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

APP_LOGGER = "onshape_export_manager"
API_LOGGER = "onshape_export_manager.api"
EXPORT_LOGGER = "onshape_export_manager.export"
SCHEDULER_LOGGER = "onshape_export_manager.scheduler"
QUEUE_LOGGER = "onshape_export_manager.queue"
WEB_LOGGER = "onshape_export_manager.web"
WORKER_LOGGER = "onshape_export_manager.worker"
EVENT_LOGGER = "onshape_export_manager.events"
AUDIT_LOGGER = "onshape_export_manager.audit"
NOTIFICATION_LOGGER = "onshape_export_manager.notifications"

# Each area logger writes to a dedicated file in addition to propagating to the
# root application log so a single tail shows everything.
AREA_LOG_FILES: dict[str, str] = {
    API_LOGGER: "api.log",
    EXPORT_LOGGER: "export.log",
    SCHEDULER_LOGGER: "scheduler.log",
    QUEUE_LOGGER: "queue.log",
    WEB_LOGGER: "web.log",
    WORKER_LOGGER: "worker.log",
    EVENT_LOGGER: "events.log",
    AUDIT_LOGGER: "audit.log",
    NOTIFICATION_LOGGER: "notifications.log",
}

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5

_MANAGED_HANDLERS: list[logging.Handler] = []

LEVEL_COLORS = {
    "DEBUG": "\033[38;5;244m",
    "INFO": "\033[38;5;39m",
    "WARNING": "\033[38;5;214m",
    "ERROR": "\033[38;5;203m",
    "CRITICAL": "\033[1;38;5;201m",
}
RESET = "\033[0m"
DIM = "\033[38;5;240m"


@dataclass(frozen=True, slots=True)
class ExportLogContext:
    """Structured metadata for export log summaries."""

    label: str
    account: str
    export_profile: str
    files_exported: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    retries: int = 0
    duration_seconds: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> str:
        base = (
            f"label={self.label} account={self.account} profile={self.export_profile} "
            f"files_exported={self.files_exported} failed_files={self.failed_files} "
            f"skipped_files={self.skipped_files} retries={self.retries} "
            f"duration_seconds={self.duration_seconds:.3f}"
        )
        if self.extra:
            extras = " ".join(f"{key}={value}" for key, value in sorted(self.extra.items()))
            return f"{base} {extras}"
        return base

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "label": self.label,
            "account": self.account,
            "export_profile": self.export_profile,
            "files_exported": self.files_exported,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "retries": self.retries,
            "duration_seconds": round(self.duration_seconds, 3),
        }
        payload.update(self.extra)
        return payload


class ColorFormatter(logging.Formatter):
    """Console formatter that adds ANSI color to the level name."""

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelname, "")
        timestamp = datetime.fromtimestamp(record.created).strftime(DATE_FORMAT)
        level = f"{color}{record.levelname:<8}{RESET}" if color else f"{record.levelname:<8}"
        name = f"{DIM}{record.name}{RESET}"
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return f"{DIM}{timestamp}{RESET} {level} {name} {message}"


class JsonFormatter(logging.Formatter):
    """Formatter that emits one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                payload[key[4:]] = value
        return json.dumps(payload, default=str)


def configure_logging(
    log_dir: Path,
    level: int | str = logging.INFO,
    *,
    json_logs: bool = False,
    console: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Configure process-wide application logging.

    Safe to call repeatedly: previously installed managed handlers are closed
    and replaced so file descriptors are never leaked.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    resolved_level = _resolve_level(level)
    shutdown_logging()

    file_formatter: logging.Formatter = (
        JsonFormatter() if json_logs else logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    )

    root = logging.getLogger()
    root.setLevel(resolved_level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    # Root application log captures everything that propagates upward.
    _attach(root, _rotating_handler(log_dir / "app.log", file_formatter, resolved_level, max_bytes, backup_count))

    # Dedicated errors log records WARNING and above from every logger.
    _attach(root, _rotating_handler(log_dir / "errors.log", file_formatter, logging.WARNING, max_bytes, backup_count))

    if console:
        stream = logging.StreamHandler(sys.stderr)
        stream.setLevel(resolved_level)
        stream.setFormatter(ColorFormatter() if _supports_color() else logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        _attach(root, stream)

    # Per-area loggers each own a dedicated rotating file and still propagate.
    for logger_name, filename in AREA_LOG_FILES.items():
        area_logger = logging.getLogger(logger_name)
        area_logger.setLevel(resolved_level)
        area_logger.propagate = True
        _attach(
            area_logger,
            _rotating_handler(log_dir / filename, file_formatter, resolved_level, max_bytes, backup_count),
        )


def shutdown_logging() -> None:
    """Detach and close every handler installed by :func:`configure_logging`."""
    for handler in _MANAGED_HANDLERS:
        for logger in _all_loggers():
            if handler in logger.handlers:
                logger.removeHandler(handler)
        try:
            handler.close()
        except (OSError, ValueError):  # pragma: no cover - defensive
            pass
    _MANAGED_HANDLERS.clear()


def get_logger(name: str = APP_LOGGER) -> logging.Logger:
    """Return an application logger."""
    return logging.getLogger(name)


def log_export_summary(level: int, context: ExportLogContext) -> None:
    """Write a structured export summary to the export log."""
    logger = get_logger(EXPORT_LOGGER)
    logger.log(
        level,
        context.to_message(),
        extra={f"ctx_{key}": value for key, value in context.to_dict().items()},
    )


def tail_log_file(path: Path, *, limit: int = 200) -> list[str]:
    """Return the last ``limit`` lines of a log file, newest last.

    Reads from the end of the file so large logs do not need to be fully loaded.
    """
    if not path.exists():
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            file_size = handle.tell()
            block = 8192
            data = b""
            newlines = 0
            position = file_size
            while position > 0 and newlines <= limit:
                read_size = min(block, position)
                position -= read_size
                handle.seek(position)
                chunk = handle.read(read_size)
                data = chunk + data
                newlines = data.count(b"\n")
            text = data.decode("utf-8", errors="replace")
    except OSError:  # pragma: no cover - defensive
        return []
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-limit:]


def _rotating_handler(
    path: Path,
    formatter: logging.Formatter,
    level: int,
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def _attach(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.addHandler(handler)
    _MANAGED_HANDLERS.append(handler)


def _all_loggers() -> list[logging.Logger]:
    loggers: list[logging.Logger] = [logging.getLogger()]
    manager = logging.getLogger().manager
    for logger in manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            loggers.append(logger)
    return loggers


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    resolved = logging.getLevelName(level.upper())
    return resolved if isinstance(resolved, int) else logging.INFO


def _supports_color() -> bool:
    return bool(getattr(sys.stderr, "isatty", lambda: False)())
