"""Terminal QR code generation.

Produces ASCII/Unicode QR codes directly in the terminal — no image
files needed.  The administrator scans the code with a phone to open
the web interface.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.box import ROUNDED
from rich.text import Text

from .console import console


def terminal_qr(url: str, *, label: str = "Scan with your phone") -> Panel:
    """Return a Rich Panel containing an ASCII QR code for *url*.

    Args:
        url: The URL to encode.
        label: Caption displayed above the QR code.
    """
    try:
        import qrcode  # noqa: F401
    except ImportError:
        return Panel(
            Text(
                "QR code generation requires the 'qrcode' package.\nRun: pip install qrcode",
                style="dim red",
            ),
            title="QR Code",
            border_style="red",
            box=ROUNDED,
        )

    # Use qrcode's built-in ASCII rendering (no Pillow needed).
    try:
        qr = qrcode.QRCode(box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        qr_text = _render_qr_ascii(qr)
    except Exception:
        # Fallback: use qrcode's built-in terminal printer
        try:
            import io

            buf = io.StringIO()
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(out=buf, tty=True)
            qr_text = buf.getvalue()
        except Exception:
            return Panel(
                Text(f"Could not generate QR code for: {url}", style="dim red"),
                title="QR Code",
                border_style="red",
                box=ROUNDED,
            )

    return Panel(
        Text(f"{label}\n\n{qr_text}", justify="center"),
        title="QR Code",
        border_style="bold #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 2),
    )


def _render_qr_ascii(qr: "qrcode.QRCode") -> str:
    """Render a QRCode instance as ASCII using █ and space characters."""
    # Get the module matrix as 2D list of bool
    matrix = qr.modules
    rows: list[str] = []
    for row in matrix:
        line = ""
        for cell in row:
            line += "██" if cell else "  "
        rows.append(line)
    return "\n".join(rows)


def print_qr(url: str, *, label: str = "Scan with your phone") -> None:
    """Print a QR code panel to the shared console."""
    console.print(terminal_qr(url, label=label))
