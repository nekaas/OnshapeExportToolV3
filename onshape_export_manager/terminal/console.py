"""Shared Rich Console singleton and output mode flags.

Every terminal component imports ``console`` from here rather than
creating its own Console instance.  This guarantees consistent width
detection, colour-system, and output target.
"""

from __future__ import annotations

from enum import Enum

from rich.console import Console as _RichConsole
from rich.theme import Theme


class OutputMode(str, Enum):
    """Controls how much raw detail reaches the terminal."""

    NORMAL = "normal"  # polished Rich output, no raw logs, no tracebacks
    VERBOSE = "verbose"  # polished + Python logging at INFO + tracebacks
    DEBUG = "debug"  # polished + Python logging at DEBUG


# -- Theme -------------------------------------------------------------------
_APPLIANCE_THEME = Theme(
    {
        "success": "bold green",
        "failure": "bold red",
        "warning": "bold yellow",
        "info": "bold cyan",
        "muted": "dim white",
        "heading": "bold white on #0a0e27",
        "accent": "#5dade2",
        "banner": "#f4d03f",
        "progress.elapsed": "dim cyan",
        "progress.remaining": "dim yellow",
        "bar.complete": "#2ecc71",
        "bar.finished": "#27ae60",
    }
)

# -- Singleton ---------------------------------------------------------------
_console: _RichConsole | None = None
_mode: OutputMode = OutputMode.NORMAL


def get_console() -> _RichConsole:
    """Return (and lazily create) the shared Rich Console."""
    global _console
    if _console is None:
        _console = _RichConsole(theme=_APPLIANCE_THEME, highlight=False)
    return _console


def set_output_mode(mode: OutputMode) -> None:
    """Set the global output mode (normal / verbose / debug)."""
    global _mode
    _mode = mode


def get_output_mode() -> OutputMode:
    """Return the current output mode."""
    return _mode


# Create the singleton eagerly so ``from .console import console`` works.
console: _RichConsole = get_console()
