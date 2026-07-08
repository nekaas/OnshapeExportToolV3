"""Live system metrics — CPU, RAM, disk, temperature, uptime.

Captures a snapshot of the Raspberry Pi's vital signs for display
in the dashboard and the ``status`` command.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsSnapshot:
    """A point-in-time capture of system and application metrics."""

    # -- System ----------------------------------------------------------
    cpu_percent: str = "—"
    ram_percent: str = "—"
    temperature: str | None = None
    free_space: str = "—"
    uptime: str = "—"

    # -- Application -----------------------------------------------------
    scheduler_status: str = "—"
    queue_depth: str = "—"
    worker_status: str = "—"
    active_export: str | None = None
    database_status: str = "—"
    notifications_status: str = "—"
    api_accounts_summary: str = "—"
    storage_status: str = "—"

    # -- Counts ----------------------------------------------------------
    label_count: int = 0
    profile_count: int = 0


def capture_metrics(
    *,
    app: object | None = None,
) -> MetricsSnapshot:
    """Build a ``MetricsSnapshot`` from live system data.

    Args:
        app: An optional ``Application`` instance.  When provided the
             application-level fields (scheduler, queue, etc.) are
             populated from the running services.
    """
    snap = MetricsSnapshot()

    # -- System metrics (psutil) -----------------------------------------
    try:
        import psutil

        snap.cpu_percent = f"{psutil.cpu_percent(interval=0.1):.0f}%"
        mem = psutil.virtual_memory()
        snap.ram_percent = f"{mem.percent:.0f}%"

        disk = psutil.disk_usage("/")
        snap.free_space = _human_bytes(disk.free)

        # Temperature (Raspberry Pi specific)
        try:
            temps = psutil.sensors_temperatures()
            if "cpu_thermal" in temps:
                snap.temperature = f"{temps['cpu_thermal'][0].current:.0f}°C"
        except Exception:
            pass

        # Uptime
        import time as _time

        boot = _time.time() - psutil.boot_time()
        snap.uptime = _format_uptime(boot)
    except ImportError:
        pass
    except Exception:
        pass

    # -- Application metrics ---------------------------------------------
    if app is not None:
        try:
            snap.scheduler_status = (
                "Running" if getattr(getattr(app, "scheduler", None), "running", False) else "Stopped"
            )
        except Exception:
            snap.scheduler_status = "Unknown"

        try:
            qm = getattr(app, "queue_manager", None)
            if qm is not None:
                waiting = getattr(qm, "waiting_count", 0)
                snap.queue_depth = f"{waiting} waiting"
            else:
                snap.queue_depth = "N/A"
        except Exception:
            snap.queue_depth = "Error"

        try:
            worker = getattr(app, "worker", None)
            if worker is not None:
                snap.worker_status = "Running"
            else:
                snap.worker_status = "N/A"
        except Exception:
            snap.worker_status = "Error"

        try:
            db = getattr(app, "database", None)
            if db is not None:
                snap.database_status = "Healthy"
            else:
                snap.database_status = "N/A"
        except Exception:
            snap.database_status = "Error"

        try:
            notif = getattr(app, "notifications", None)
            snap.notifications_status = "Enabled" if notif is not None else "Disabled"
        except Exception:
            snap.notifications_status = "Error"

        try:
            pool = getattr(app, "api_pool", None)
            if pool is not None:
                accounts = getattr(pool, "accounts", {})
                healthy = sum(1 for a in accounts.values() if getattr(a, "healthy", False))
                total = len(accounts)
                if total == 0:
                    snap.api_accounts_summary = "None configured"
                else:
                    snap.api_accounts_summary = f"{healthy} Healthy"
                    if total - healthy > 0:
                        snap.api_accounts_summary += f" / {total - healthy} Rate Limited"
            else:
                snap.api_accounts_summary = "N/A"
        except Exception:
            snap.api_accounts_summary = "Error"

        try:
            fm = getattr(app, "folder_manager", None)
            if fm is not None:
                snap.storage_status = "Healthy"
            else:
                snap.storage_status = "N/A"
        except Exception:
            snap.storage_status = "Error"

        try:
            cm = getattr(app, "config_manager", None)
            if cm is not None:
                labels = getattr(cm, "labels", {})
                profiles = getattr(cm, "export_profiles", {})
                snap.label_count = len(labels)
                snap.profile_count = len(profiles)
        except Exception:
            pass

    return snap


def _human_bytes(n: int) -> str:
    """Return human-readable size string (e.g. ``"416 GB"``)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} PB"


def _format_uptime(seconds: float) -> str:
    """Format seconds into a human-readable uptime string."""
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins or not parts:
        parts.append(f"{mins}m")
    return " ".join(parts)
