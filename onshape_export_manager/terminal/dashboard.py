"""Live auto-refreshing system dashboard.

Renders a continuously updating Rich ``Live`` display showing
scheduler, queue, workers, storage, CPU/RAM/temp, and uptime.
"""

from __future__ import annotations

from rich.console import Group
from rich.box import ROUNDED
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import theme, widgets
from .console import console
from .metrics import MetricsSnapshot, capture_metrics


def _build_dashboard_panel(snap: MetricsSnapshot) -> Panel:
    """Build the dashboard content from a metrics snapshot."""
    rows: list[tuple[str, str]] = [
        ("Scheduler", snap.scheduler_status),
        ("Queue", snap.queue_depth),
        ("Workers", snap.worker_status),
        ("Active Export", snap.active_export or "—"),
        ("Database", snap.database_status),
        ("Notifications", snap.notifications_status),
        ("API Accounts", snap.api_accounts_summary),
        ("Labels", str(snap.label_count)),
        ("Profiles", str(snap.profile_count)),
        ("Storage", snap.storage_status),
        ("Free Space", snap.free_space),
        ("CPU", snap.cpu_percent),
        ("RAM", snap.ram_percent),
        ("Temperature", snap.temperature or "N/A"),
        ("Uptime", snap.uptime),
    ]

    table = Table(show_header=False, box=None, expand=True, padding=(0, 1))
    table.add_column("Key", style="bold #5dade2", width=16)
    table.add_column("Value", style="white")

    for key, value in rows:
        table.add_row(key, value)

    return Panel(
        table,
        title="System Status",
        border_style="bold #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 2),
    )


def live_dashboard(refresh_per_second: float = 0.5) -> None:
    """Start a continuously refreshing live dashboard.

    Blocks until the user presses Ctrl‑C.
    """
    with Live(
        _build_dashboard_panel(capture_metrics()),
        console=console,
        refresh_per_second=refresh_per_second * 2,
        screen=False,
    ) as live:
        try:
            while True:
                import time

                time.sleep(1.0 / refresh_per_second)
                live.update(_build_dashboard_panel(capture_metrics()))
        except KeyboardInterrupt:
            pass
