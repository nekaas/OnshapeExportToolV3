"""Reusable Rich renderables — panels, dividers, spinners, status lines.

Every piece of terminal chrome that appears in more than one place
should be factored into a helper here.
"""

from __future__ import annotations

from typing import Sequence

from rich.box import ROUNDED, SIMPLE
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from . import theme

# ── Panels ─────────────────────────────────────────────────────────────────


def appliance_panel(
    content: RenderableType,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    double: bool = False,
    expand: bool = True,
) -> Panel:
    """Return a Rich Panel with the appliance's signature look.

    Args:
        content: The renderable to place inside the panel.
        title: Optional title (left-aligned in the top border).
        subtitle: Optional subtitle (right-aligned in the top border).
        double: Use double-line borders for major sections.
        expand: Whether to fill the terminal width.
    """
    from rich.box import DOUBLE  # avoid top-level unused import

    box = DOUBLE if double else ROUNDED
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style="bold #5dade2" if not double else "bold #f4d03f",
        box=box,
        expand=expand,
        padding=(1, 2),
    )


def info_panel(message: str, *, title: str = "Info") -> Panel:
    """A muted info panel for secondary information."""
    return Panel(
        Text(message, style="dim white"),
        title=title,
        border_style="dim cyan",
        box=ROUNDED,
        expand=True,
        padding=(0, 2),
    )


def warning_panel(message: str, *, title: str = "Warning") -> Panel:
    """A yellow warning panel."""
    return Panel(
        Text(message, style="yellow"),
        title=title,
        border_style="yellow",
        box=ROUNDED,
        expand=True,
        padding=(0, 2),
    )


def error_panel(message: str, *, title: str = "Error") -> Panel:
    """A red error panel."""
    return Panel(
        Text(message, style="bold red"),
        title=title,
        border_style="red",
        box=ROUNDED,
        expand=True,
        padding=(0, 2),
    )


# ── Dividers ───────────────────────────────────────────────────────────────


def section_divider(label: str = "") -> Rule:
    """A styled horizontal rule, optionally with a centred label."""
    return Rule(
        title=Text(label, style="bold #5dade2") if label else None,
        style="dim #5dade2",
    )


def heavy_divider() -> Rule:
    """A double-line horizontal rule for major section breaks."""
    return Rule(style="bold #f4d03f", characters="═")


# ── Status rows ────────────────────────────────────────────────────────────


def status_row(label: str, ok: bool, detail: str = "") -> Text:
    """Return a single ``[icon] label  detail`` status line.

    Args:
        label: What is being checked (e.g. "Database").
        ok: ``True`` → ✓ (green), ``False`` → ✗ (red).
        detail: Optional right-side detail text.
    """
    icon = theme.ICON_OK if ok else theme.ICON_FAIL
    result = Text.assemble(icon, "  ", theme.heading(label))
    if detail:
        result.append("  ")
        result.append(theme.muted(detail))
    return result


def checklist(steps: Sequence[tuple[str, bool, str]]) -> Group:
    """Render a vertical checklist of status rows.

    Each element is ``(label, ok, detail)``.
    """
    lines: list[Text] = []
    for label, ok, detail in steps:
        lines.append(status_row(label, ok, detail))
    return Group(*lines)


# ── Spinner ────────────────────────────────────────────────────────────────


def waiting_spinner(text: str) -> Group:
    """A spinner with label, used during async startup steps."""
    return Group(
        Spinner(theme.SPINNER_NAME, text=Text(text, style="dim cyan")),
    )


# ── Key-Value table ────────────────────────────────────────────────────────


def kv_table(rows: Sequence[tuple[str, str]], *, title: str | None = None) -> Table:
    """A compact two-column key-value table.

    Args:
        rows: ``[(key, value), ...]`` pairs.
        title: Optional table title.
    """
    t = Table(
        title=title,
        show_header=False,
        box=SIMPLE,
        expand=True,
        padding=(0, 1),
    )
    t.add_column("Key", style="bold #5dade2", width=20)
    t.add_column("Value", style="white")
    for k, v in rows:
        t.add_row(k, v)
    return t


# ── Empty state ────────────────────────────────────────────────────────────


def empty_state(message: str) -> Panel:
    """A muted panel shown when there is nothing to display."""
    return Panel(
        Text(message, style="dim italic white", justify="center"),
        border_style="dim #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 0),
    )
