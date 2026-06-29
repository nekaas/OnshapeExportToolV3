"""Remote-access detection for headless / Server Mode deployments.

Detects and reports the status of Tailscale, Cloudflare Tunnel, reverse proxies
(NGINX / Caddy / Traefik), and HTTPS certificates so the dashboard can show the
user exactly how to reach the appliance — without any manual configuration.

All external-command probes are cheap: the binary is located with
``shutil.which`` first and only invoked (with a short timeout) when present.
Results are cached briefly so dashboard polling never spawns processes in a
tight loop, keeping CPU usage low on a Raspberry Pi.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LETSENCRYPT_LIVE = Path("/etc/letsencrypt/live")
_CACHE_TTL_SECONDS = 15.0
_cache: dict[str, tuple[float, Any]] = {}


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Status of one remote-access provider."""

    name: str
    installed: bool
    connected: bool
    detail: str = ""
    urls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "installed": self.installed,
            "connected": self.connected,
            "detail": self.detail,
            "urls": self.urls,
        }


def remote_access_snapshot(port: int = 8080, *, use_https: bool | None = None) -> dict[str, Any]:
    """Return a JSON-serializable snapshot of all remote-access methods."""
    tailscale = tailscale_status(port)
    cloudflare = cloudflare_status()
    proxies = reverse_proxy_status()
    https = https_status()
    scheme = "https" if (use_https if use_https is not None else https["enabled"]) else "http"
    local = local_urls(port, scheme=scheme)
    return {
        "local_urls": local,
        "tailscale": tailscale.to_dict(),
        "cloudflare": cloudflare.to_dict(),
        "reverse_proxies": [proxy.to_dict() for proxy in proxies],
        "https": https,
        "recommended_url": _recommended_url(local, tailscale, cloudflare),
    }


def tailscale_status(port: int = 8080) -> ServiceStatus:
    """Detect Tailscale and report the appliance's tailnet address."""
    cached = _cached("tailscale")
    if cached is not None:
        return cached

    binary = shutil.which("tailscale")
    if binary is None:
        return _store("tailscale", ServiceStatus("Tailscale", installed=False, connected=False,
                                                  detail="tailscale not installed"))

    payload = _run_json([binary, "status", "--json"])
    if payload is None:
        return _store("tailscale", ServiceStatus("Tailscale", installed=True, connected=False,
                                                  detail="tailscaled not running"))

    self_node = payload.get("Self") or {}
    backend = payload.get("BackendState", "")
    ips = [ip for ip in self_node.get("TailscaleIPs", []) if ":" not in ip]  # IPv4 only
    dns_name = (self_node.get("DNSName") or "").rstrip(".")
    connected = backend == "Running" and bool(ips)

    urls: list[str] = []
    for ip in ips:
        urls.append(f"http://{ip}:{port}")
    if dns_name:
        urls.append(f"http://{dns_name}:{port}")

    detail = "connected" if connected else f"state={backend or 'unknown'}"
    return _store(
        "tailscale",
        ServiceStatus("Tailscale", installed=True, connected=connected, detail=detail, urls=urls),
    )


def cloudflare_status() -> ServiceStatus:
    """Detect a Cloudflare Tunnel (cloudflared) and its connection state."""
    cached = _cached("cloudflare")
    if cached is not None:
        return cached

    binary = shutil.which("cloudflared")
    running = _service_active("cloudflared") or _process_running("cloudflared")
    if binary is None and not running:
        return _store("cloudflare", ServiceStatus("Cloudflare Tunnel", installed=False,
                                                   connected=False, detail="cloudflared not installed"))

    urls: list[str] = []
    detail = "running" if running else "installed, not running"
    if binary is not None:
        tunnels = _run_json([binary, "tunnel", "list", "--output", "json"])
        if isinstance(tunnels, list) and tunnels:
            names = ", ".join(str(t.get("name", "")) for t in tunnels if t.get("name"))
            if names:
                detail = f"tunnels: {names}"
    return _store(
        "cloudflare",
        ServiceStatus("Cloudflare Tunnel", installed=binary is not None or running,
                      connected=running, detail=detail, urls=urls),
    )


def reverse_proxy_status() -> list[ServiceStatus]:
    """Detect installed reverse proxies (NGINX, Caddy, Traefik)."""
    cached = _cached("proxies")
    if cached is not None:
        return cached

    statuses: list[ServiceStatus] = []
    for name, binary in (("NGINX", "nginx"), ("Caddy", "caddy"), ("Traefik", "traefik")):
        installed = shutil.which(binary) is not None
        active = _service_active(binary) if installed else False
        statuses.append(
            ServiceStatus(name, installed=installed, connected=active,
                          detail="active" if active else ("installed" if installed else "not installed"))
        )
    return _store("proxies", statuses)


def https_status() -> dict[str, Any]:
    """Detect available HTTPS certificates (Let's Encrypt / self-signed)."""
    letsencrypt_domains: list[str] = []
    if LETSENCRYPT_LIVE.exists():
        try:
            letsencrypt_domains = [p.name for p in LETSENCRYPT_LIVE.iterdir() if p.is_dir()]
        except OSError:  # pragma: no cover - permission
            letsencrypt_domains = []
    return {
        "enabled": bool(letsencrypt_domains),
        "letsencrypt": bool(letsencrypt_domains),
        "letsencrypt_domains": letsencrypt_domains,
        "self_signed": False,
    }


def local_urls(port: int = 8080, *, scheme: str = "http") -> list[str]:
    """Return local URLs for reaching the dashboard."""
    urls = [f"{scheme}://localhost:{port}"]
    ip = local_ip_address()
    if ip and ip not in {"127.0.0.1", "localhost"}:
        urls.append(f"{scheme}://{ip}:{port}")
    return urls


def local_ip_address() -> str | None:
    """Return the primary LAN IP address without contacting any network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are actually sent for a UDP connect; it just selects a route.
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:  # pragma: no cover - offline
        return None
    finally:
        sock.close()


def _recommended_url(local: list[str], tailscale: ServiceStatus, cloudflare: ServiceStatus) -> str | None:
    if cloudflare.connected and cloudflare.urls:
        return cloudflare.urls[0]
    if tailscale.connected and tailscale.urls:
        return tailscale.urls[0]
    return local[-1] if local else None


def _run_json(command: list[str]) -> Any:
    try:
        result = subprocess.run(  # noqa: S603 - command from trusted detection
            command,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _service_active(unit: str) -> bool:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return False
    try:
        result = subprocess.run(  # noqa: S603 - trusted unit name
            [systemctl, "is-active", "--quiet", unit],
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _process_running(name: str) -> bool:
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return False
    try:
        result = subprocess.run(  # noqa: S603 - trusted process name
            [pgrep, "-x", name],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _cached(key: str) -> Any:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        _cache.pop(key, None)
        return None
    return value


def _store(key: str, value: Any) -> Any:
    _cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, value)
    return value
