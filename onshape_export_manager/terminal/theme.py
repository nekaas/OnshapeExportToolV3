"""Visual theme — colors, styles, and Unicode box-drawing constants.

Every terminal component imports its visual tokens from here.
Raw ANSI escape codes are forbidden; always use Rich abstractions
or the symbolic constants defined below.
"""

from __future__ import annotations

from rich.style import Style
from rich.text import Text

# ── Unicode box-drawing ────────────────────────────────────────────────────
# Single-line
BOX_H = "─"
BOX_V = "│"
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"
BOX_TD = "┬"
BOX_BD = "┴"
BOX_LR = "├"
BOX_RL = "┤"
BOX_CR = "┼"

# Double-line (used for major sections / banner frame)
DBL_H = "═"
DBL_V = "║"
DBL_TL = "╔"
DBL_TR = "╗"
DBL_BL = "╚"
DBL_BR = "╝"

# -- Status icons -----------------------------------------------------------
ICON_OK = Text("✓", style="bold green")
ICON_FAIL = Text("✗", style="bold red")
ICON_WARN = Text("⚠", style="bold yellow")
ICON_INFO = Text("ⓘ", style="bold cyan")
ICON_ARROW = Text("▶", style="bold #5dade2")
ICON_BULLET = Text("•", style="dim white")
ICON_GEAR = Text("⚙", style="bold #5dade2")
ICON_CLOCK = Text("⏱", style="dim cyan")

# -- Spinner -----------------------------------------------------------------
SPINNER_NAME = "dots"  # Rich spinner to use throughout

# -- Progress bar colours ----------------------------------------------------
BAR_COMPLETE = Style(color="#2ecc71")
BAR_FINISHED = Style(color="#27ae60")
BAR_PULSE = Style(color="#f39c12")

# -- Section helpers ---------------------------------------------------------

def heading(text: str) -> Text:
    """Return a bold white-on-dark heading."""
    return Text(text, style="bold white on #0a0e27")


def muted(text: str) -> Text:
    """Return dimmed secondary text."""
    return Text(text, style="dim white")


def accent(text: str) -> Text:
    """Return cyan accent text."""
    return Text(text, style="bold #5dade2")


def danger(text: str) -> Text:
    """Return bold red danger text."""
    return Text(text, style="bold red")


def success(text: str) -> Text:
    """Return bold green success text."""
    return Text(text, style="bold green")
