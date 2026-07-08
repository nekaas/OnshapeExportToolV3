"""Rich Table helpers for the appliance terminal.

Shared table constructors used by multiple commands
(accounts, profiles, queue, history, etc.).
"""

from __future__ import annotations

from typing import Any, Sequence

from rich.box import SIMPLE, ROUNDED
from rich.table import Table


def data_table(
    columns: Sequence[str],
    *,
    title: str | None = None,
    caption: str | None = None,
) -> Table:
    """Return a consistently styled Rich Table for data display.

    Args:
        columns: Column header names.
        title: Optional table title (above the table).
        caption: Optional caption (below the table).
    """
    t = Table(
        title=title,
        caption=caption,
        box=ROUNDED,
        expand=True,
        show_header=True,
        header_style="bold #5dade2",
        border_style="dim #5dade2",
        padding=(0, 1),
    )
    for col in columns:
        t.add_column(col, overflow="fold")
    return t


def compact_table(
    columns: Sequence[str],
    *,
    title: str | None = None,
) -> Table:
    """Like ``data_table`` but with a simpler box for denser output."""
    t = Table(
        title=title,
        box=SIMPLE,
        expand=True,
        show_header=True,
        header_style="bold #5dade2",
        border_style="dim #5dade2",
        padding=(0, 1),
    )
    for col in columns:
        t.add_column(col, overflow="fold")
    return t


def fill_table(table: Table, rows: Sequence[Sequence[Any]]) -> None:
    """Populate a table with rows, converting each cell to ``str``."""
    for row in rows:
        table.add_row(*(str(cell) for cell in row))
