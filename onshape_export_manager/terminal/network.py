"""Network discovery for the appliance.

Detects every way to reach the web interface and displays them
with status indicators and QR codes.
"""

from __future__ import annotations

import socket

from rich.console import Group, RenderableType
from rich.box import ROUNDED
from rich.panel import Panel
from rich.text import Text

from . import theme, widgets
from .console import console


def discover_network(port: int = 8080) -> list[dict[str, str]]:
    """Detect all available access methods.

    Returns a list of dicts with keys ``label``, ``url``, ``ok``,
    and ``note``.
    """
    entries: list[dict[str, str]] = []

    # Localhost (always available)
    entries.append(
        {"label": "Localhost", "url": f"http://localhost:{port}", "ok": "true", "note": ""}
    )

    # LAN IP
    lan_ip = _detect_lan_ip()
    if lan_ip:
        entries.append(
            {"label": "LAN", "url": f"http://{lan_ip}:{port}", "ok": "true", "note": ""}
        )
    else:
        entries.append(
            {"label": "LAN", "url": "—", "ok": "false", "note": "No LAN IP detected"}
        )

    # Hostname / mDNS
    hostname = socket.gethostname()
    entries.append(
        {
            "label": "Hostname",
            "url": f"http://{hostname}.local:{port}",
            "ok": "true",
            "note": "(mDNS — may require Avahi)",
        }
    )

    # Tailscale
    tailscale_ip = _detect_tailscale()
    if tailscale_ip:
        entries.append(
            {
                "label": "Tailscale",
                "url": f"https://{tailscale_ip}:{port}",
                "ok": "true",
                "note": "",
            }
        )
    else:
        entries.append(
            {
                "label": "Tailscale",
                "url": "—",
                "ok": "false",
                "note": "Not running — install tailscale",
            }
        )

    # Cloudflare Tunnel
    cf = _detect_cloudflare()
    if cf:
        entries.append(
            {"label": "Cloudflare Tunnel", "url": cf, "ok": "true", "note": ""}
        )
    else:
        entries.append(
            {
                "label": "Cloudflare Tunnel",
                "url": "—",
                "ok": "false",
                "note": "Not configured",
            }
        )

    return entries


def render_network(port: int = 8080) -> RenderableType:
    """Build a Rich panel showing all network access methods."""
    entries = discover_network(port)
    lines: list[Text] = []
    for e in entries:
        icon = theme.ICON_OK if e["ok"] == "true" else theme.ICON_FAIL
        line = Text.assemble(
            icon,
            "  ",
            Text(e["label"], style="bold white"),
        )
        if e["ok"] == "true":
            line.append(f"\n     {e['url']}", style="dim cyan")
        else:
            line.append(f"\n     {e['note']}", style="dim yellow")
        lines.append(line)

    return Panel(
        Group(*lines),
        title="Network Access",
        border_style="bold #5dade2",
        box=ROUNDED,
        expand=True,
        padding=(1, 2),
    )


def print_network(port: int = 8080) -> None:
    """Print network discovery to the shared console."""
    console.print(render_network(port))


# ── Internal helpers ───────────────────────────────────────────────────────


def _detect_lan_ip() -> str | None:
    """Return the primary LAN IPv4 address, if any."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Doesn't actually send traffic
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    # Fallback: iterate interfaces
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return None


def _detect_tailscale() -> str | None:
    """Return the Tailscale IP if the daemon is reachable, else None."""
    import shutil

    if shutil.which("tailscale") is None:
        return None
    try:
        import subprocess

        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _detect_cloudflare() -> str | None:
    """Return the Cloudflare Tunnel hostname if configured, else None."""
    import shutil

    if shutil.which("cloudflared") is None:
        return None
    # Best-effort: cloudflared tunnel info might give hostname
    try:
        import json
        import subprocess

        result = subprocess.run(
            ["cloudflared", "tunnel", "info", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            hostname = data.get("hostname", "")
            if hostname:
                return f"https://{hostname}"
    except Exception:
        pass
    return None
