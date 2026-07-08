"""Export progress bars and ETA display.

Replaces raw logging ("Exporting...") with a Rich progress bar
showing file count, estimated time remaining, API requests, and
the current filename.
"""

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.box import ROUNDED
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from .console import console


class ExportProgressTracker:
    """Tracks a single export's progress for Rich display."""

    def __init__(self, export_name: str, total_files: int):
        self.export_name = export_name
        self.total_files = total_files
        self.completed_files = 0
        self.api_requests = 0
        self.retry_count = 0
        self.current_file: str = "—"
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold #5dade2]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True,
        )
        self._task: TaskID = self._progress.add_task(
            f"[bold white]{export_name}",
            total=total_files,
        )

    def update(
        self,
        completed: int,
        *,
        api_requests: int | None = None,
        retry_count: int | None = None,
        current_file: str | None = None,
    ) -> None:
        """Advance the progress bar."""
        self.completed_files = completed
        if api_requests is not None:
            self.api_requests = api_requests
        if retry_count is not None:
            self.retry_count = retry_count
        if current_file is not None:
            self.current_file = current_file
        self._progress.update(self._task, completed=completed)

    @property
    def progress(self) -> Progress:
        return self._progress

    def render_panel(self) -> Panel:
        """Build a Rich Panel combining the progress bar with metadata."""
        info_lines: list[Text] = []
        info_lines.append(
            Text.assemble(
                Text("Files", style="bold #5dade2"),
                Text(f"  {self.completed_files} / {self.total_files}", style="white"),
            )
        )
        info_lines.append(
            Text.assemble(
                Text("API Requests", style="bold #5dade2"),
                Text(f"  {self.api_requests}", style="white"),
            )
        )
        info_lines.append(
            Text.assemble(
                Text("Retry Count", style="bold #5dade2"),
                Text(f"  {self.retry_count}", style="white"),
            )
        )
        info_lines.append(
            Text.assemble(
                Text("Current File", style="bold #5dade2"),
                Text(f"  {self.current_file}", style="dim cyan"),
            )
        )

        return Panel(
            Group(self._progress, Text(""), *info_lines),
            title="Current Export",
            border_style="bold #5dade2",
            box=ROUNDED,
            expand=True,
            padding=(1, 2),
        )


def simple_progress(label: str, total: int) -> Progress:
    """Return a one-off Rich Progress bar for indeterminate tasks."""
    prog = Progress(
        SpinnerColumn(),
        TextColumn(f"[bold white]{label}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        expand=True,
    )
    prog.add_task(label, total=total)
    return prog
