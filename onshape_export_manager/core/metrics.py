"""Analytics and metrics service for the dashboard and JSON API.

This module turns the raw database, configuration, and account-pool state into
JSON-serializable summaries: headline counts, success rates, export activity
time series, account health, queue breakdowns, disk usage, and a global search
index. It is intentionally dependency-light so it can power the web API, the
terminal UI, and reporting without pulling in framework code.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from onshape_export_manager.core.api_pool import AccountRuntimeState
from onshape_export_manager.core.database import ExportHistoryEntry, QueueEntry, SchedulerJobEntry
from onshape_export_manager.core.export_formats import list_format_definitions
from onshape_export_manager.core.jobs import JobStatus
from onshape_export_manager.core.security import mask_secret

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.app import Application


HEALTH_HEALTHY = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_RATE_LIMITED = "rate_limited"
HEALTH_FAILED = "failed"
HEALTH_DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class DiskUsage:
    """Summary of disk usage for a directory tree."""

    total_bytes: int
    file_count: int
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_bytes": self.total_bytes,
            "human": human_bytes(self.total_bytes),
            "file_count": self.file_count,
            "truncated": self.truncated,
        }


class MetricsService:
    """Compute dashboard analytics from application state."""

    def __init__(self, application: "Application") -> None:
        self.app = application

    # -- High level payloads ------------------------------------------------

    def dashboard_snapshot(self, *, history_limit: int = 500, activity_days: int = 14) -> dict[str, Any]:
        """Return the full analytics payload used by the dashboard."""
        config = self._safe_config()
        database = self.app.database
        history = database.list_export_history(limit=history_limit)
        accounts = self._account_states()
        queue_entries = database.list_queue(limit=10_000)
        scheduler_jobs = database.list_scheduler_jobs()

        return {
            "generated_at": _now().isoformat(),
            "version": self._version(),
            "summary": self._summary(config, history, accounts, queue_entries, scheduler_jobs),
            "exports": {
                "success_rate": success_rate(history),
                "total_files": sum(len(entry.exported_files) for entry in history),
                "average_duration_seconds": average_duration(history),
                "activity": export_activity(history, days=activity_days),
                "by_profile": counts_by(history, lambda item: item.export_profile),
                "by_label": counts_by(history, lambda item: item.label_name),
                "by_account": counts_by(history, lambda item: item.account_name),
            },
            "accounts": [serialize_account_state(state) for state in accounts],
            "account_health": account_health_breakdown(accounts, config),
            "queue": self._queue_payload(queue_entries),
            "scheduler": [serialize_scheduler_job(job) for job in scheduler_jobs],
            "recent_history": [serialize_history(entry) for entry in history[:15]],
            "disk": self.disk_usage().to_dict(),
            "database": database.status(),
            "formats": [serialize_format(item) for item in list_format_definitions()],
        }

    def summary_counts(self) -> dict[str, int]:
        """Return only the headline counts (cheap, used for polling)."""
        config = self._safe_config()
        history = self.app.database.list_export_history(limit=10_000)
        accounts = self._account_states()
        queue_entries = self.app.database.list_queue(limit=10_000)
        scheduler_jobs = self.app.database.list_scheduler_jobs()
        return self._summary(config, history, accounts, queue_entries, scheduler_jobs)

    # -- Components ---------------------------------------------------------

    def _summary(
        self,
        config: Any,
        history: list[ExportHistoryEntry],
        accounts: list[AccountRuntimeState],
        queue_entries: list[QueueEntry],
        scheduler_jobs: list[SchedulerJobEntry],
    ) -> dict[str, int]:
        queue_counts = Counter(entry.status for entry in queue_entries)
        failed = sum(1 for entry in history if not entry.success)
        healthy_accounts = sum(
            1 for state in accounts if state.rate_limit_status == "available"
        )
        return {
            "accounts": len(config.accounts.accounts) if config else len(accounts),
            "healthy_accounts": healthy_accounts,
            "labels": len(config.labels.labels) if config else 0,
            "export_profiles": len(config.export_profiles.profiles) if config else 0,
            "total_exports": len(history),
            "successful_exports": len(history) - failed,
            "failed_exports": failed,
            "queue_size": queue_counts.get(JobStatus.PENDING, 0),
            "queue_running": queue_counts.get(JobStatus.RUNNING, 0),
            "scheduler_jobs": len(scheduler_jobs),
            "scheduler_enabled": sum(1 for job in scheduler_jobs if job.enabled),
        }

    def _queue_payload(self, queue_entries: list[QueueEntry]) -> dict[str, Any]:
        counts = Counter(entry.status for entry in queue_entries)
        recent = sorted(queue_entries, key=lambda item: item.updated_at, reverse=True)[:25]
        return {
            "counts": {status.value: counts.get(status, 0) for status in JobStatus},
            "total": len(queue_entries),
            "items": [serialize_queue(entry) for entry in recent],
        }

    def disk_usage(self, *, max_files: int = 50_000) -> DiskUsage:
        """Compute total size and file count of the exports directory."""
        return directory_usage(self.app.paths.exports_dir, max_files=max_files)

    def global_search(self, query: str, *, limit_per_group: int = 8) -> dict[str, Any]:
        """Search accounts, labels, profiles, history, queue, and scheduler jobs."""
        needle = query.strip().lower()
        if not needle:
            return {"query": query, "total": 0, "groups": []}

        config = self._safe_config()
        groups: list[dict[str, Any]] = []

        if config is not None:
            groups.append(
                _search_group(
                    "Accounts",
                    "accounts",
                    [
                        {
                            "title": account.name,
                            "subtitle": account.description or "Onshape account",
                            "href": "/accounts",
                        }
                        for account in config.accounts.accounts
                        if needle in account.name.lower() or needle in account.description.lower()
                    ],
                    limit_per_group,
                )
            )
            groups.append(
                _search_group(
                    "Labels",
                    "labels",
                    [
                        {
                            "title": label.friendly_name,
                            "subtitle": f"{label.export_profile} · {label.onshape_label_id}",
                            "href": "/labels",
                        }
                        for label in config.labels.labels
                        if needle in label.friendly_name.lower()
                        or needle in label.export_profile.lower()
                    ],
                    limit_per_group,
                )
            )
            groups.append(
                _search_group(
                    "Export Profiles",
                    "export-profiles",
                    [
                        {
                            "title": profile.name,
                            "subtitle": ", ".join(fmt.value for fmt in profile.formats),
                            "href": "/export-profiles",
                        }
                        for profile in config.export_profiles.profiles
                        if needle in profile.name.lower()
                        or any(needle in fmt.value for fmt in profile.formats)
                    ],
                    limit_per_group,
                )
            )

        history = self.app.database.list_export_history(limit=2_000)
        groups.append(
            _search_group(
                "Export History",
                "history",
                [
                    {
                        "title": f"{entry.label_name} · {entry.export_profile}",
                        "subtitle": f"{'Success' if entry.success else 'Failed'} · {entry.account_name}",
                        "href": "/history",
                    }
                    for entry in history
                    if needle in entry.label_name.lower()
                    or needle in entry.export_profile.lower()
                    or needle in entry.account_name.lower()
                ],
                limit_per_group,
            )
        )

        groups = [group for group in groups if group["items"]]
        total = sum(group["count"] for group in groups)
        return {"query": query, "total": total, "groups": groups}

    def _account_states(self) -> list[AccountRuntimeState]:
        if self.app.api_pool is None:
            return []
        return self.app.api_pool.snapshot()

    def _safe_config(self) -> Any:
        try:
            return self.app.config_manager.load()
        except Exception:  # pragma: no cover - surfaced elsewhere
            return None

    def _version(self) -> str:
        from onshape_export_manager import __version__

        return __version__


# -- Serialization helpers --------------------------------------------------


def serialize_account_state(state: AccountRuntimeState) -> dict[str, Any]:
    """Serialize account runtime state for the API and UI."""
    return {
        "name": state.name,
        "api_usage": state.api_usage,
        "failure_count": state.failure_count,
        "status": state.rate_limit_status,
        "health": _health_from_status(state.rate_limit_status, state.failure_count),
        "last_used": state.last_used.isoformat() if state.last_used else None,
        "rate_limited_until": (
            state.rate_limited_until.isoformat() if state.rate_limited_until else None
        ),
        "last_error": state.last_error,
    }


def serialize_history(entry: ExportHistoryEntry) -> dict[str, Any]:
    """Serialize an export history entry."""
    return {
        "id": entry.id,
        "started_at": entry.started_at.isoformat() if entry.started_at else None,
        "finished_at": entry.finished_at.isoformat() if entry.finished_at else None,
        "account_name": entry.account_name,
        "label_name": entry.label_name,
        "export_profile": entry.export_profile,
        "files": entry.exported_files,
        "file_count": len(entry.exported_files),
        "duration_seconds": round(entry.duration_seconds, 3),
        "success": entry.success,
        "failures": entry.failures,
        "retry_count": entry.retry_count,
    }


def serialize_queue(entry: QueueEntry) -> dict[str, Any]:
    """Serialize a queue entry."""
    return {
        "id": entry.id,
        "label_name": entry.label_name,
        "profile_name": entry.profile_name,
        "status": entry.status.value,
        "retry_count": entry.retry_count,
        "next_run_at": entry.next_run_at.isoformat() if entry.next_run_at else None,
        "last_error": entry.last_error,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def serialize_scheduler_job(job: SchedulerJobEntry) -> dict[str, Any]:
    """Serialize a scheduler job."""
    return {
        "id": job.id,
        "name": job.name,
        "label_name": job.label_name,
        "interval": job.interval,
        "enabled": job.enabled,
        "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
        "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
    }


def serialize_format(definition: Any) -> dict[str, Any]:
    """Serialize an export format definition."""
    return {
        "format": definition.format.value,
        "display_name": definition.display_name,
        "extension": definition.default_extension,
        "supports_part_studio": definition.supports_part_studio,
        "supports_drawing": definition.supports_drawing,
        "native": definition.onshape_native,
    }


def serialize_account_config(account: Any) -> dict[str, Any]:
    """Serialize a stored account, masking secrets."""
    return {
        "name": account.name,
        "description": account.description,
        "enabled": account.enabled,
        "access_key": mask_secret(account.access_key),
        "secret_key": "********",
        "api_usage": account.api_usage,
        "failure_count": account.failure_count,
        "status": account.rate_limit_status,
    }


# -- Aggregations -----------------------------------------------------------


def success_rate(history: list[ExportHistoryEntry]) -> float:
    """Return the percentage of successful exports (0-100)."""
    if not history:
        return 0.0
    successes = sum(1 for entry in history if entry.success)
    return round(successes / len(history) * 100, 1)


def average_duration(history: list[ExportHistoryEntry]) -> float:
    """Return the average export duration in seconds."""
    if not history:
        return 0.0
    return round(sum(entry.duration_seconds for entry in history) / len(history), 2)


def counts_by(history: list[ExportHistoryEntry], key) -> list[dict[str, Any]]:
    """Group history by a key function, returning sorted counts."""
    counter: Counter[str] = Counter(key(entry) for entry in history)
    return [
        {"name": name, "count": count}
        for name, count in counter.most_common(10)
    ]


def export_activity(history: list[ExportHistoryEntry], *, days: int = 14) -> dict[str, Any]:
    """Return a daily time series of successful and failed exports."""
    today = _now().date()
    start = today - timedelta(days=days - 1)
    buckets: dict[str, dict[str, int]] = {
        (start + timedelta(days=offset)).isoformat(): {"success": 0, "failed": 0}
        for offset in range(days)
    }
    for entry in history:
        moment = entry.started_at or entry.created_at
        if moment is None:
            continue
        day = moment.astimezone(timezone.utc).date()
        if day < start or day > today:
            continue
        key = day.isoformat()
        bucket = buckets.setdefault(key, {"success": 0, "failed": 0})
        bucket["success" if entry.success else "failed"] += 1

    labels = sorted(buckets)
    return {
        "labels": labels,
        "success": [buckets[label]["success"] for label in labels],
        "failed": [buckets[label]["failed"] for label in labels],
    }


def account_health_breakdown(
    accounts: list[AccountRuntimeState],
    config: Any,
) -> dict[str, int]:
    """Return account counts grouped by health bucket."""
    disabled = 0
    if config is not None:
        disabled = sum(1 for account in config.accounts.accounts if not account.enabled)
    breakdown: dict[str, int] = defaultdict(int)
    breakdown[HEALTH_DISABLED] = disabled
    for state in accounts:
        breakdown[_health_from_status(state.rate_limit_status, state.failure_count)] += 1
    return dict(breakdown)


def directory_usage(path: Path, *, max_files: int = 50_000) -> DiskUsage:
    """Walk a directory tree and total file sizes up to ``max_files``."""
    if not path.exists():
        return DiskUsage(total_bytes=0, file_count=0)
    total = 0
    count = 0
    truncated = False
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:  # pragma: no cover - races/permission
                continue
            count += 1
            if count >= max_files:
                truncated = True
                break
    return DiskUsage(total_bytes=total, file_count=count, truncated=truncated)


def human_bytes(num_bytes: int) -> str:
    """Format a byte count as a human readable string."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _health_from_status(status: str, failure_count: int) -> str:
    if status == "rate_limited":
        return HEALTH_RATE_LIMITED
    if status == "failed":
        return HEALTH_FAILED
    if failure_count > 0:
        return HEALTH_DEGRADED
    return HEALTH_HEALTHY


def _search_group(
    title: str,
    page: str,
    items: list[dict[str, Any]],
    limit: int,
) -> dict[str, Any]:
    return {
        "title": title,
        "page": page,
        "count": len(items),
        "items": items[:limit],
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)
