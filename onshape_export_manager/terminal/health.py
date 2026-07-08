"""Health report rendering.

Produces a polished Rich panel summarising the status of every
subsystem in the appliance.
"""

from __future__ import annotations

from rich.console import Group
from rich.box import ROUNDED
from rich.panel import Panel
from rich.text import Text

from . import theme
from .console import console
from .metrics import MetricsSnapshot, capture_metrics


def render_health(app: object | None = None) -> Panel:
    """Build a Rich health-report panel.

    Args:
        app: Optional ``Application`` instance for live data.
    """
    snap = capture_metrics(app=app)

    entries: list[tuple[str, bool, str]] = [
        ("Database", snap.database_status == "Healthy", snap.database_status),
        (
            "Workers",
            snap.worker_status == "Running",
            snap.worker_status,
        ),
        (
            "Scheduler",
            snap.scheduler_status == "Running",
            snap.scheduler_status,
        ),
        (
            "Storage",
            snap.storage_status == "Healthy",
            f"{snap.storage_status}  •  {snap.free_space} free",
        ),
        (
            "Notifications",
            snap.notifications_status == "Enabled",
            snap.notifications_status,
        ),
        (
            "API Accounts",
            snap.api_accounts_summary not in ("Error", "N/A", "None configured"),
            snap.api_accounts_summary,
        ),
        (
            "Queue",
            snap.queue_depth not in ("Error",),
            snap.queue_depth,
        ),
    ]

    lines: list[Text] = []
    for label, ok, detail in entries:
        icon = theme.ICON_OK if ok else theme.ICON_FAIL
        line = Text.assemble(icon, "  ", Text(label, style="bold white"))
        if detail:
            line.append("  ")
            line.append(Text(detail, style="dim white"))
        lines.append(line)

    # Recent errors placeholder
    lines.append(Text(""))
    lines.append(Text("Recent Errors", style="bold #5dade2"))
    lines.append(Text("  None", style="dim white"))

    return Panel(
        Group(*lines),
        title="System Health",
        border_style="bold #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 2),
    )


def print_health(app: object | None = None) -> None:
    """Print the health report to the shared console."""
    console.print(render_health(app=app))
