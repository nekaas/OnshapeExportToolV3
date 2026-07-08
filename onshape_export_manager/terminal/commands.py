"""Interactive command dispatcher — REPL and one-shot CLI.

Powers both ``onshape-export-manager console`` (persistent REPL with
live dashboard) and ``onshape-export-manager <command>`` (one-shot
polished output).  Every command renders through Rich — never raw
dictionaries or ``repr()``.
"""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from typing import Any, Iterator

from rich.prompt import Prompt
from rich.box import ROUNDED
from rich.table import Table as _Table
from rich.text import Text

from . import theme, widgets
from .banner import print_banner
from .console import console, get_output_mode, OutputMode
from .dashboard import live_dashboard
from .health import print_health
from .metrics import capture_metrics
from .network import print_network
from .errors import print_error
from .qr import print_qr


# ── Logging suppression (normal mode keeps things clean) ───────────────────

@contextmanager
def _quiet_mode() -> Iterator[None]:
    """Temporarily suppress all Python logging output in NORMAL mode.

    Uses ``logging.disable()`` which is a global override — it prevents
    ALL log messages below the given severity from being emitted,
    regardless of individual logger levels or handler configuration.

    In VERBOSE and DEBUG modes logging is left untouched so the
    administrator can see full diagnostics alongside Rich output.
    """
    if get_output_mode() != OutputMode.NORMAL:
        yield
        return

    prev = logging.root.manager.disable  # type: ignore[attr-defined]
    logging.disable(logging.WARNING)
    try:
        yield
    finally:
        logging.disable(prev)

# ── Command registry ───────────────────────────────────────────────────────

_COMMANDS: dict[str, dict[str, Any]] = {
    "help": {
        "description": "Show this help message",
        "one_shot": True,
    },
    "status": {
        "description": "Show current system status snapshot",
        "one_shot": True,
    },
    "dashboard": {
        "description": "Launch the live auto-refreshing dashboard",
        "one_shot": True,
    },
    "accounts": {
        "description": "Show configured Onshape accounts",
        "one_shot": True,
    },
    "labels": {
        "description": "Show configured labels",
        "one_shot": True,
    },
    "profiles": {
        "description": "Show configured export profiles",
        "one_shot": True,
    },
    "queue": {
        "description": "Show export queue status",
        "one_shot": True,
    },
    "workers": {
        "description": "Show background worker status",
        "one_shot": True,
    },
    "scheduler": {
        "description": "Show scheduler status and jobs",
        "one_shot": True,
    },
    "exports": {
        "description": "Show recent export history",
        "one_shot": True,
    },
    "history": {
        "description": "Show export history (alias for exports)",
        "one_shot": True,
    },
    "notifications": {
        "description": "Show notification configuration",
        "one_shot": True,
    },
    "logs": {
        "description": "Show recent application logs",
        "one_shot": True,
    },
    "backup": {
        "description": "Create a configuration backup",
        "one_shot": True,
    },
    "restore": {
        "description": "Restore from a backup",
        "one_shot": True,
    },
    "restore": {
        "description": "List available backups",
        "one_shot": True,
    },
    "storage": {
        "description": "Show storage configuration and usage",
        "one_shot": True,
    },
    "network": {
        "description": "Show network access URLs and QR code",
        "one_shot": True,
    },
    "diagram": {
        "description": "Show system architecture diagram",
        "one_shot": True,
    },
    "health": {
        "description": "Show comprehensive health report",
        "one_shot": True,
    },
    "version": {
        "description": "Show version information",
        "one_shot": True,
    },
    "restart": {
        "description": "Restart the appliance service (requires sudo)",
        "one_shot": True,
    },
    "shutdown": {
        "description": "Gracefully shut down the appliance",
        "one_shot": True,
    },
    "wizard": {
        "description": "Launch the first-run setup wizard",
        "one_shot": True,
    },
    "shortcuts": {
        "description": "Show keyboard shortcuts and quick-reference",
        "one_shot": True,
    },
    "exit": {
        "description": "Exit the interactive console",
        "one_shot": False,  # REPL-only
    },
    "quit": {
        "description": "Exit the interactive console",
        "one_shot": False,  # REPL-only
    },
}


# ── Help ───────────────────────────────────────────────────────────────────


def _print_help() -> None:
    """Print a polished command reference."""
    table = _Table(
        title="Available Commands",
        box=ROUNDED,
        expand=True,
        border_style="bold #5dade2",
        header_style="bold #f4d03f",
        padding=(0, 1),
    )
    table.add_column("Command", style="bold #5dade2")
    table.add_column("Description", style="white")

    for cmd, info in _COMMANDS.items():
        if cmd in ("exit", "quit"):
            continue
        table.add_row(cmd, info["description"])
    table.add_row("exit / quit", "Exit the interactive console")

    console.print(table)


# ── One-shot command dispatch ──────────────────────────────────────────────


def dispatch_one_shot(cmd: str, *, app: object | None = None, port: int = 8080) -> None:
    """Execute a single command and exit (one-shot CLI mode).

    In NORMAL mode, Python logging is suppressed so only Rich output appears.
    """
    with _quiet_mode():
        _dispatch(cmd, app=app, port=port)


def _dispatch(cmd: str, *, app: object | None, port: int) -> None:
    """Inner dispatch — logging already suppressed by caller."""
    if cmd in ("help", "?"):
        _print_help()
    elif cmd == "status":
        _print_status(app)
    elif cmd == "dashboard":
        live_dashboard()
    elif cmd in ("accounts",):
        _print_accounts(app)
    elif cmd in ("labels",):
        _print_labels(app)
    elif cmd in ("profiles",):
        _print_profiles(app)
    elif cmd in ("queue",):
        _print_queue(app)
    elif cmd in ("workers",):
        _print_workers(app)
    elif cmd in ("scheduler",):
        _print_scheduler(app)
    elif cmd in ("exports", "history"):
        _print_history(app)
    elif cmd in ("notifications",):
        _print_notifications(app)
    elif cmd in ("logs",):
        _print_logs(app)
    elif cmd in ("backup",):
        _print_backup(app)
    elif cmd in ("restore",):
        _print_restore(app)
    elif cmd in ("diagram",):
        _print_diagram()
    elif cmd in ("storage",):
        _print_storage(app)
    elif cmd in ("network",):
        print_network(port)
        from .network import discover_network

        entries = discover_network(port)
        best = next((e for e in entries if e["ok"] == "true"), None)
        if best:
            console.print("")
            print_qr(best["url"])
    elif cmd in ("health",):
        print_health(app)
    elif cmd in ("version",):
        from onshape_export_manager import __version__

        console.print(Text(f"Onshape Export Manager v{__version__}", style="bold white"))
    elif cmd in ("restart",):
        _restart_service()
    elif cmd in ("shutdown",):
        _shutdown_service(app)
    elif cmd in ("wizard",):
        from .wizard import run_wizard

        run_wizard(app)
    elif cmd in ("shortcuts",):
        _print_shortcuts()
    else:
        console.print(f"[bold red]Unknown command:[/bold red] {cmd}")
        console.print("Type [bold #5dade2]help[/bold #5dade2] to see available commands.")


# ── Interactive console (REPL) ─────────────────────────────────────────────


def run_console(app: object | None = None, *, port: int = 8080) -> None:
    """Start the interactive terminal REPL.

    Shows the banner, then continuously accepts commands with
    Rich-styled prompts.  Use ``exit`` or ``quit`` to leave.
    """
    print_banner(mode="Console")
    console.print("")
    console.print(
        "  Type [bold #5dade2]help[/bold #5dade2] for available commands, "
        "[bold #5dade2]dashboard[/bold #5dade2] for live view, "
        "[bold #5dade2]exit[/bold #5dade2] to quit."
    )
    console.print("")

    while True:
        try:
            raw = Prompt.ask(
                Text("onshape>", style="bold #5dade2"),
                console=console,
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Shutting down...[/dim]")
            break

        if not raw:
            continue

        cmd, *rest = raw.split(maxsplit=1)
        cmd = cmd.lower()

        if cmd in ("exit", "quit"):
            console.print("[dim]Goodbye.[/dim]")
            break
        elif cmd == "help":
            _print_help()
        elif cmd == "dashboard":
            live_dashboard()
        elif cmd in ("restart",):
            _restart_service()
        elif cmd in ("shutdown",):
            _shutdown_service(app)
            break
        else:
            # Delegate everything else to the shared dispatcher
            _dispatch(cmd, app=app, port=port)


# ── Command implementations ────────────────────────────────────────────────


def _print_status(app: object | None = None) -> None:
    """Render a one-shot status snapshot."""
    snap = capture_metrics(app=app)
    rows = [
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
    console.print(widgets.kv_table(rows, title="System Status"))


def _get_app_config(app: object | None = None):
    """Safely load application config, returning None on failure."""
    if app is None:
        return None
    try:
        cm = getattr(app, "config_manager", None)
        if cm is None:
            return None
        return cm.load()
    except Exception:
        return None


# -- Accounts --------------------------------------------------------------


def _print_accounts(app: object | None = None) -> None:
    config = _get_app_config(app)
    if config is None:
        console.print(widgets.empty_state("No configuration loaded"))
        return
    from .tables import data_table, fill_table

    accounts = getattr(config, "accounts", None)
    if accounts is None or not accounts.accounts:
        console.print(widgets.empty_state("No accounts configured"))
        return

    # Try to get runtime status from API pool for richer display
    runtime: dict[str, dict[str, str]] = {}
    if app is not None:
        try:
            pool = getattr(app, "api_pool", None)
            if pool is not None:
                for state in pool.snapshot():
                    runtime[state.name] = {
                        "status": state.rate_limit_status,
                        "usage": str(state.api_usage),
                        "failures": str(state.failure_count),
                    }
        except Exception:
            pass

    table = data_table(["Name", "Status", "Usage", "Failures"], title="Onshape Accounts")
    rows: list[list[str]] = []
    for acc in accounts.accounts:
        if acc.name in runtime:
            rt = runtime[acc.name]
            rows.append([acc.name, rt["status"], rt["usage"], rt["failures"]])
        else:
            rows.append([
                acc.name,
                "disabled" if not acc.enabled else "—",
                str(getattr(acc, "api_usage", 0)),
                str(getattr(acc, "failure_count", 0)),
            ])
    fill_table(table, rows)
    console.print(table)


# -- Labels ----------------------------------------------------------------


def _print_labels(app: object | None = None) -> None:
    config = _get_app_config(app)
    if config is None:
        console.print(widgets.empty_state("No configuration loaded"))
        return
    from .tables import data_table, fill_table

    labels = getattr(config, "labels", None)
    if labels is None or not labels.labels:
        console.print(widgets.empty_state("No labels configured"))
        return

    table = data_table(["Name", "Profile", "Accounts", "Schedule", "Enabled"], title="Labels")
    rows: list[list[str]] = []
    for lbl in labels.labels:
        sched_raw = getattr(lbl, "scheduler", None)
        sched = sched_raw if isinstance(sched_raw, str) else "—"
        rows.append([
            lbl.friendly_name,
            lbl.export_profile,
            ", ".join(lbl.assigned_accounts),
            sched,
            "✓" if lbl.enabled else "✗",
        ])
    fill_table(table, rows)
    console.print(table)


# -- Profiles --------------------------------------------------------------


def _print_profiles(app: object | None = None) -> None:
    config = _get_app_config(app)
    if config is None:
        console.print(widgets.empty_state("No configuration loaded"))
        return
    from .tables import data_table, fill_table

    profiles = getattr(config, "export_profiles", None)
    if profiles is None or not profiles.profiles:
        console.print(widgets.empty_state("No profiles configured"))
        return

    table = data_table(["Name", "Formats", "Enabled"], title="Export Profiles")
    rows: list[list[str]] = []
    for prof in profiles.profiles:
        rows.append([
            prof.name,
            ", ".join(f.value for f in prof.formats),
            "✓" if prof.enabled else "✗",
        ])
    fill_table(table, rows)
    console.print(table)


# -- Queue -----------------------------------------------------------------


def _print_queue(app: object | None = None) -> None:
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    qm = getattr(app, "queue_manager", None)
    if qm is None:
        console.print(widgets.empty_state("Queue manager not available"))
        return
    try:
        stats = qm.stats()
    except Exception as exc:
        console.print(widgets.error_panel(f"Failed to read queue: {exc}"))
        return

    rows = [
        ("Total", str(stats.total)),
        ("Pending", str(stats.pending)),
        ("Running", str(stats.running)),
        ("Completed", str(stats.completed)),
        ("Failed", str(stats.failed)),
        ("Cancelled", str(stats.cancelled)),
    ]
    console.print(widgets.kv_table(rows, title="Export Queue"))


# -- Workers ---------------------------------------------------------------


def _print_workers(app: object | None = None) -> None:
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    worker = getattr(app, "worker", None)
    if worker is None:
        console.print(widgets.empty_state("Worker not available"))
        return
    try:
        status = worker.status()
    except Exception as exc:
        console.print(widgets.error_panel(f"Failed to read worker: {exc}"))
        return

    rows = [
        ("Running", "✓" if status.running else "✗"),
        ("Worker Count", str(getattr(status, "worker_count", 1))),
        ("Jobs Processed", str(status.jobs_processed)),
        ("Jobs Failed", str(status.jobs_failed)),
        ("Active Job", status.active_job_id or "—"),
        ("Active Label", status.active_label or "—"),
        ("Last Tick", status.last_tick_at or "—"),
        ("Last Error", status.last_error or "—"),
    ]
    console.print(widgets.kv_table(rows, title="Background Worker"))


# -- Scheduler -------------------------------------------------------------


def _print_scheduler(app: object | None = None) -> None:
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    db = getattr(app, "database", None)
    if db is None:
        console.print(widgets.empty_state("Database not available"))
        return
    try:
        running = db.get_state("scheduler.running", "false")
        jobs = db.list_scheduler_jobs()
    except Exception as exc:
        console.print(widgets.error_panel(f"Failed to read scheduler: {exc}"))
        return

    rows = [("Running", running)]
    if jobs:
        rows.append(("Jobs", str(len(jobs))))
        enabled = [j for j in jobs if j.enabled]
        rows.append(("Enabled", str(len(enabled))))
    console.print(widgets.kv_table(rows, title="Scheduler"))

    if jobs:
        from .tables import compact_table, fill_table

        table = compact_table(["Label", "Interval", "Next Run", "Enabled"], title="Scheduled Jobs")
        job_rows: list[list[str]] = []
        for j in jobs:
            next_run = j.next_run_at.isoformat() if j.next_run_at else "—"
            job_rows.append([j.label_name, j.interval, next_run, "✓" if j.enabled else "✗"])
        fill_table(table, job_rows)
        console.print(table)


# -- History ---------------------------------------------------------------


def _print_history(app: object | None = None) -> None:
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    db = getattr(app, "database", None)
    if db is None:
        console.print(widgets.empty_state("Database not available"))
        return
    try:
        entries = db.list_export_history(limit=20)
    except Exception as exc:
        console.print(widgets.error_panel(f"Failed to read history: {exc}"))
        return

    if not entries:
        console.print(widgets.empty_state("No export history yet"))
        return

    from .tables import data_table, fill_table

    table = data_table(["Label", "Profile", "Files", "Duration", "Status"], title="Recent Exports")
    rows: list[list[str]] = []
    for e in entries:
        rows.append([
            e.label_name,
            e.export_profile,
            str(len(e.exported_files)),
            f"{e.duration_seconds:.1f}s",
            "✓" if e.success else "✗",
        ])
    fill_table(table, rows)
    console.print(table)


# -- Notifications ---------------------------------------------------------


def _print_notifications(app: object | None = None) -> None:
    config = _get_app_config(app)
    if config is None:
        console.print(widgets.empty_state("No configuration loaded"))
        return
    from .tables import data_table, fill_table

    notif = getattr(config, "notifications", None)
    channels = getattr(notif, "channels", []) if notif else []
    if not channels:
        console.print(widgets.empty_state("No notification channels configured"))
        return

    table = data_table(["Name", "Kind", "Target", "Enabled"], title="Notification Channels")
    rows: list[list[str]] = []
    for ch in channels:
        rows.append([
            getattr(ch, "name", "—"),
            getattr(ch, "kind", "—"),
            getattr(ch, "target", "—"),
            "✓" if getattr(ch, "enabled", True) else "✗",
        ])
    fill_table(table, rows)
    console.print(table)


# -- Logs ------------------------------------------------------------------


def _print_logs(app: object | None = None) -> None:
    from pathlib import Path as _Path

    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    paths = getattr(app, "paths", None)
    if paths is None:
        console.print(widgets.empty_state("App paths not available"))
        return
    logs_dir = getattr(paths, "logs_dir", None)
    if logs_dir is None or not _Path(logs_dir).is_dir():
        console.print(widgets.empty_state("Logs directory not found"))
        return

    log_files = sorted(_Path(logs_dir).glob("*.log"))
    if not log_files:
        console.print(widgets.empty_state("No log files found"))
        return

    console.print(widgets.kv_table(
        [("Logs directory", str(logs_dir))],
        title="Application Logs",
    ))
    from .tables import compact_table, fill_table

    table = compact_table(["File", "Size", "Modified"], title="Log Files")
    rows: list[list[str]] = []
    for lf in log_files:
        stat = lf.stat()
        size = f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024 * 1024 else f"{stat.st_size / (1024*1024):.1f} MB"
        import datetime as _dt
        mtime = _dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        rows.append([lf.name, size, mtime])
    fill_table(table, rows)
    console.print(table)


# -- Backup ----------------------------------------------------------------


def _print_backup(app: object | None = None) -> None:
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    try:
        from onshape_export_manager.core.backup import BackupManager

        paths = getattr(app, "paths", None)
        database = getattr(app, "database", None)
        if paths is None:
            console.print(widgets.empty_state("App paths not available"))
            return
        mgr = BackupManager(paths, database=database)
        info = mgr.create_backup()
        console.print(widgets.kv_table([
            ("Backup", info.name),
            ("Size", info.to_dict().get("size_human", str(info.size_bytes))),
            ("Entries", str(info.entry_count)),
            ("Created", info.created_at.isoformat()),
        ], title="Backup Created"))
    except Exception as exc:
        console.print(widgets.error_panel(f"Backup failed: {exc}"))


# -- Storage ---------------------------------------------------------------


def _print_storage(app: object | None = None) -> None:
    from pathlib import Path as _Path

    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    paths = getattr(app, "paths", None)
    if paths is None:
        console.print(widgets.empty_state("App paths not available"))
        return

    dirs = [
        ("Exports", getattr(paths, "exports_dir", None)),
        ("Config", getattr(paths, "config_dir", None)),
        ("Database", getattr(paths, "database_dir", None)),
        ("Logs", getattr(paths, "logs_dir", None)),
        ("Backups", getattr(paths, "backups_dir", None)),
    ]
    rows: list[tuple[str, str]] = []
    for label, d in dirs:
        if d is None:
            rows.append((label, "—"))
            continue
        p = _Path(d) if isinstance(d, str) else d
        if not p.exists():
            rows.append((label, "not found"))
            continue
        total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        if total < 1024 * 1024:
            rows.append((label, f"{total / 1024:.1f} KB"))
        else:
            rows.append((label, f"{total / (1024*1024):.1f} MB"))
    console.print(widgets.kv_table(rows, title="Storage Usage"))


def _print_restore(app: object | None = None) -> None:
    """List available backups and offer to restore one."""
    if app is None:
        console.print(widgets.empty_state("Application not available"))
        return
    try:
        from onshape_export_manager.core.backup import BackupManager

        paths = getattr(app, "paths", None)
        database = getattr(app, "database", None)
        if paths is None:
            console.print(widgets.empty_state("App paths not available"))
            return
        mgr = BackupManager(paths, database=database)
        backups = mgr.list_backups()
    except Exception as exc:
        console.print(widgets.error_panel(f"Failed to list backups: {exc}"))
        return

    if not backups:
        console.print(widgets.empty_state("No backups found. Run 'backup' to create one."))
        return

    from .tables import compact_table, fill_table

    table = compact_table(["#", "Name", "Size", "Created", "Entries"], title="Available Backups")
    rows: list[list[str]] = []
    for i, b in enumerate(backups, 1):
        d = b.to_dict()
        rows.append([
            str(i),
            b.name,
            d.get("size_human", str(b.size_bytes)),
            b.created_at.strftime("%Y-%m-%d %H:%M"),
            str(b.entry_count),
        ])
    fill_table(table, rows)
    console.print(table)
    console.print("")
    console.print("[dim]Use the web dashboard to restore a specific backup.[/dim]")
    console.print("[dim]CLI restore: python -m onshape_export_manager.cli --restore <name>[/dim]")


def _print_diagram() -> None:
    """Render an ASCII architecture diagram of the system."""
    from rich.panel import Panel
    from rich.text import Text

    diagram = Text(
        """\
                              ┌─────────────────────────┐
                              │    Onshape Export        │
                              │    Manager Appliance      │
                              └────────────┬────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
          ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
          │   Scheduler     │   │   Web Dashboard │   │  Terminal UI    │
          │   (cron-like)   │   │  (FastAPI+HTMX) │   │  (Rich/Textual) │
          └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
                   │                     │                     │
                   ▼                     │                     │
          ┌─────────────────┐            │                     │
          │  Export Queue   │◄───────────┼─────────────────────┘
          │  (FIFO + retry) │            │
          └────────┬────────┘            │
                   │                     │
                   ▼                     │
          ┌─────────────────┐            │
          │  Background     │            │
          │  Workers (1-8)  │            │
          └────────┬────────┘            │
                   │                     │
                   ▼                     │
          ┌─────────────────┐            │
          │  API Pool       │            │
          │  (round-robin)  │            │
          └────────┬────────┘            │
                   │                     │
                   ▼                     │
          ┌─────────────────┐            │
          │  Export Engine  │            │
          │  (Onshape API)  │            │
          └────────┬────────┘            │
                   │                     │
                   ▼                     ▼
          ┌─────────────────────────────────────┐
          │           Storage Layer              │
          │  ┌──────────┐  ┌──────────────────┐ │
          │  │  SQLite   │  │  File System     │ │
          │  │  Database │  │  (STEP/STL/OBJ)  │ │
          │  └──────────┘  └──────────────────┘ │
          └─────────────────────────────────────┘
                               │
                               ▼
          ┌─────────────────────────────────────┐
          │         Notifications               │
          │  Discord / Slack / Teams / Email    │
          └─────────────────────────────────────┘\
        """,
        style="dim cyan",
        justify="center",
    )

    console.print(
        Panel(
            diagram,
            title="System Architecture",
            border_style="bold #5dade2",
            box=ROUNDED,
            expand=True,
            padding=(1, 0),
        )
    )


def _print_placeholder(cmd: str, msg: str) -> None:
    """Print a placeholder panel for commands not yet fully wired."""
    from .widgets import info_panel

    console.print(info_panel(f"`{cmd}` — {msg}.", title="Coming Soon"))


def _print_shortcuts() -> None:
    """Print the keyboard shortcuts and quick-reference card."""
    from .tables import data_table, fill_table

    shortcuts = [
        ("?", "Show this reference"),
        ("g d", "Go to Dashboard"),
        ("g q", "Go to Queue"),
        ("g h", "Go to History"),
        ("g s", "Go to Settings"),
        ("n l", "New Label"),
        ("n p", "New Profile"),
        ("/", "Focus command palette"),
        ("Esc", "Close modal / cancel"),
        ("Ctrl+C", "Stop worker / exit dashboard"),
    ]
    table = data_table(["Shortcut", "Action"], title="Keyboard Shortcuts")
    fill_table(table, [[s[0], s[1]] for s in shortcuts])
    console.print(table)
    console.print("")
    console.print(widgets.info_panel(
        "Quick commands: [bold]status[/] [bold]dashboard[/] [bold]network[/] "
        "[bold]health[/] [bold]accounts[/] [bold]queue[/] [bold]workers[/] "
        "[bold]history[/] [bold]logs[/] [bold]backup[/] [bold]shortcuts[/]",
        title="Terminal Commands",
    ))


def _restart_service() -> None:
    """Restart the systemd service (requires sudo)."""
    import subprocess

    console.print("[bold yellow]Restarting onshape-export-manager service...[/bold yellow]")
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "onshape-export-manager"],
            check=True,
        )
        console.print("[bold green]Service restarted.[/bold green]")
    except subprocess.CalledProcessError:
        print_error(
            title="Restart Failed",
            context="systemd service restart",
            reason="The systemctl command failed.",
            suggestion="Ensure you have sudo privileges and the service is installed.",
        )
    except FileNotFoundError:
        print_error(
            title="Restart Failed",
            context="systemd not available",
            reason="systemctl was not found on this system.",
            suggestion="Restart the process manually or install the systemd service.",
        )


def _shutdown_service(app: object | None = None) -> None:
    """Graceful shutdown: stop workers, flush queue, then stop service."""
    console.print("[bold yellow]Shutting down gracefully...[/bold yellow]")

    # Tell the background worker to stop
    if app is not None:
        worker = getattr(app, "worker", None)
        if worker is not None and hasattr(worker, "stop"):
            console.print("  [dim]Stopping worker...[/dim]")
            worker.stop()

    # Stop the service via systemd
    import subprocess

    try:
        subprocess.run(
            ["sudo", "systemctl", "stop", "onshape-export-manager"],
            check=True,
        )
        console.print("[bold green]Service stopped. Goodbye.[/bold green]")
    except subprocess.CalledProcessError:
        console.print("[bold yellow]Could not stop via systemd — process will exit.[/bold yellow]")
    except FileNotFoundError:
        console.print("[dim]systemctl not available — process will exit.[/dim]")
