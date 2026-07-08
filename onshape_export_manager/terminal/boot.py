"""Staged boot sequence with Rich checkmark display.

Replaces raw logging during startup with a polished, step-by-step
checklist showing the boot progress of each subsystem.
"""

from __future__ import annotations

import time
from typing import Callable

from rich.live import Live
from rich.box import ROUNDED
from rich.text import Text

from . import theme, widgets
from .console import console, get_output_mode, OutputMode


def _step_line(step_num: int, total: int, label: str, ok: bool | None, detail: str = "") -> Text:
    """Render a single boot step line.

    Args:
        step_num: 1-based step number.
        total: Total number of steps.
        label: Step description.
        ok: ``True`` → ✓, ``False`` → ✗, ``None`` → spinner (in progress).
        detail: Optional detail (shown when ok or failed).
    """
    prefix = f"[{step_num}/{total}]"
    if ok is None:
        # In progress — show spinner marker
        icon = Text("⏳", style="bold #f39c12")
    elif ok:
        icon = theme.ICON_OK
    else:
        icon = theme.ICON_FAIL

    line = Text.assemble(
        Text(prefix, style="dim white"),
        "  ",
        icon,
        "  ",
        Text(label, style="bold white"),
    )
    if detail and ok is not None:
        line.append("  ")
        line.append(Text(detail, style="dim white"))
    return line


def run_boot_sequence(
    steps: list[tuple[str, Callable[[], tuple[bool, str]]]],
    *,
    title: str = "System Boot",
    show_when_done: bool = True,
) -> bool:
    """Execute a sequence of boot steps with a live-updating checklist.

    Args:
        steps: List of ``(label, callable)`` pairs.  Each callable returns
               ``(ok, detail)``.
        title: Panel title for the checklist.
        show_when_done: If ``True``, the completed checklist remains visible
                        for a moment before the caller continues.

    Returns:
        ``True`` if every step passed, ``False`` otherwise.
    """
    total = len(steps)
    results: list[tuple[str, bool, str]] = []
    all_ok = True

    def _render() -> Text:
        """Build the current checklist as a Rich Text."""
        lines: list[Text] = []
        for i, (label, _, _) in enumerate(steps):
            step_num = i + 1
            if i < len(results):
                _, ok, detail = results[i]
                lines.append(_step_line(step_num, total, label, ok, detail))
            elif i == len(results):
                # Currently executing
                lines.append(_step_line(step_num, total, label, None))
            else:
                # Not yet started
                prefix = f"[{step_num}/{total}]"
                lines.append(
                    Text.assemble(
                        Text(prefix, style="dim white"),
                        "    ",
                        Text(label, style="dim white"),
                    )
                )
        return Text("\n").join(lines) if lines else Text("")

    mode = get_output_mode()
    # In debug mode we let the logging subsystem also print.
    if mode == OutputMode.DEBUG:
        console.print(f"[dim]Boot sequence started ({total} steps)[/dim]")

    panel_kwargs = dict(
        title=title,
        border_style="bold #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 2),
    )

    with Live(
        _render(),
        console=console,
        refresh_per_second=10,
        transient=not show_when_done,
    ) as live:
        for i, (label, fn) in enumerate(steps):
            try:
                ok, detail = fn()
            except Exception as exc:
                ok, detail = False, str(exc)
                if mode in (OutputMode.VERBOSE, OutputMode.DEBUG):
                    import traceback

                    traceback.print_exc()

            results.append((label, ok, detail))
            if not ok:
                all_ok = False
            live.update(_render())
            # Brief pause so the user can see each checkmark appear
            time.sleep(0.15)

        if show_when_done and all_ok:
            # Let the completed checklist linger
            time.sleep(0.4)

    return all_ok
