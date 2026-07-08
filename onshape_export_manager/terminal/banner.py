"""Boot splash — large ASCII art logo and version information.

Renders the first thing an administrator sees when the appliance starts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rich.align import Align
from rich.box import DOUBLE
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from onshape_export_manager import __version__

from . import theme, widgets
from .console import console


# -- ASCII art logo ----------------------------------------------------------

_LOGO = r"""
 ██████╗ ███╗   ██╗███████╗██╗  ██╗ █████╗ ██████╗ ███████╗
██╔═══██╗████╗  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝
██║   ██║██╔██╗ ██║███████╗███████║███████║██████╔╝█████╗
██║   ██║██║╚██╗██║╚════██║██╔══██║██╔══██║██╔═══╝ ██╔══╝
╚██████╔╝██║ ╚████║███████║██║  ██║██║  ██║██║     ███████╗
 ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝
""".strip("\n")


def _banner_text() -> Text:
    """Return the coloured ASCII logo as a Rich Text."""
    return Text(_LOGO, style="bold #f4d03f")


def _platform_label() -> str:
    """Best-effort platform description."""
    try:
        with open("/sys/firmware/devicetree/base/model") as fh:
            return fh.read().strip("\x00").strip() or "Linux"
    except FileNotFoundError:
        pass
    try:
        import platform

        return platform.platform() or "Linux"
    except Exception:
        return "Linux"


def render_banner(
    *,
    mode: str = "Console",
    db_type: str = "SQLite",
) -> RenderableType:
    """Return the full boot-splash renderable.

    Args:
        mode: Runtime mode label (e.g. ``"Console"``, ``"Server"``).
        db_type: Database label (e.g. ``"SQLite"``).
    """
    import platform as _platform
    import sys

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    meta_rows = [
        ("Version", __version__),
        ("Platform", _platform_label()),
        ("Python", sys.version.split()[0]),
        ("Database", db_type),
        ("Mode", mode),
        ("Boot Time", now),
    ]

    # Build a two-column key-value chunk for the metadata area.
    meta_text = Text()
    for key, value in meta_rows:
        meta_text.append(f"  {key:.<20}", style="bold #5dade2")
        meta_text.append(f"  {value}\n", style="white")

    subtitle = Text("ONSHAPE EXPORT MANAGER APPLIANCE", style="bold white")

    # Assemble: logo → heavy divider → subtitle → metadata
    group = Group(
        _banner_text(),
        widgets.heavy_divider(),
        Align.center(subtitle),
        "",
        Align.center(meta_text),
    )

    return Panel(
        group,
        box=DOUBLE,
        border_style="bold #f4d03f",
        expand=True,
        padding=(1, 3),
    )


def print_banner(*, mode: str = "Console", db_type: str = "SQLite") -> None:
    """Print the boot splash directly to the shared console."""
    console.print(render_banner(mode=mode, db_type=db_type))
