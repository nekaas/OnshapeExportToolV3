"""Rich error screens — no raw tracebacks during normal operation.

When something goes wrong the terminal shows a clean, actionable
error panel instead of a Python stack trace.  Diagnostic details
are only shown in verbose / debug mode.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.box import DOUBLE
from rich.text import Text

from .console import console, get_output_mode, OutputMode


def render_error(
    *,
    title: str = "Error",
    context: str = "",
    reason: str = "",
    suggestion: str = "",
    detail: str = "",
) -> Panel:
    """Build a polished error panel.

    Args:
        title: Short error headline (e.g. ``"Export Failed"``).
        context: Where or on what the error occurred.
        reason: Human-readable cause.
        suggestion: Action the administrator can take.
        detail: Additional technical info (only shown in verbose/debug).
    """
    body = Text()
    if context:
        body.append("Context\n", style="bold #5dade2")
        body.append(f"  {context}\n\n", style="white")
    if reason:
        body.append("Reason\n", style="bold #f39c12")
        body.append(f"  {reason}\n\n", style="white")
    if suggestion:
        body.append("Suggested Fix\n", style="bold #2ecc71")
        body.append(f"  {suggestion}\n", style="white")

    if detail and get_output_mode() in (OutputMode.VERBOSE, OutputMode.DEBUG):
        body.append("\nDiagnostic Information\n", style="bold #e74c3c")
        body.append(f"  {detail}\n", style="dim red")

    body.append("\n")
    body.append("[D] Diagnostics  [L] Logs  [R] Retry", style="dim white")

    return Panel(
        body,
        title=title,
        border_style="bold red",
        box=DOUBLE,
        expand=True,
        padding=(1, 2),
    )


def print_error(
    *,
    title: str = "Error",
    context: str = "",
    reason: str = "",
    suggestion: str = "",
    detail: str = "",
) -> None:
    """Print a polished error panel to the shared console."""
    console.print(
        render_error(
            title=title,
            context=context,
            reason=reason,
            suggestion=suggestion,
            detail=detail,
        )
    )
