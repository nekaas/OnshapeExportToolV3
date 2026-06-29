"""System and Raspberry Pi resource monitoring.

Reports CPU, RAM, disk, temperature, uptime, and load for the dashboard. Uses
``psutil`` when available and falls back to lightweight stdlib / ``/proc``
readings otherwise, so it works on Raspberry Pi OS, Ubuntu Server ARM64, Debian
ARM64, and developer machines without extra dependencies.

All readings are cheap and non-blocking to keep CPU usage low on low-power
hardware: CPU percentage is sampled as the delta since the previous call rather
than by busy-waiting.
"""

from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import psutil

    HAS_PSUTIL = True
except ModuleNotFoundError:  # pragma: no cover - psutil optional
    psutil = None  # type: ignore[assignment]
    HAS_PSUTIL = False


THERMAL_ZONE = Path("/sys/class/thermal/thermal_zone0/temp")
PROC_MEMINFO = Path("/proc/meminfo")
PROC_UPTIME = Path("/proc/uptime")
DEVICE_TREE_MODEL = Path("/proc/device-tree/model")


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """A used/total/percent triple in bytes."""

    used: int
    total: int
    percent: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "used": self.used,
            "total": self.total,
            "percent": round(self.percent, 1),
            "used_human": human_bytes(self.used),
            "total_human": human_bytes(self.total),
        }


def system_snapshot(disk_path: Path | str | None = None) -> dict[str, Any]:
    """Return a JSON-serializable snapshot of system resources."""
    target = Path(disk_path) if disk_path else Path.home()
    cpu = cpu_percent()
    memory = memory_usage()
    disk = disk_usage(target)
    temperature = cpu_temperature_c()
    return {
        "hostname": hostname(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "is_raspberry_pi": is_raspberry_pi(),
        "pi_model": raspberry_pi_model(),
        "cpu_percent": cpu,
        "cpu_count": os.cpu_count() or 1,
        "load_average": load_average(),
        "memory": memory.to_dict() if memory else None,
        "disk": disk.to_dict() if disk else None,
        "temperature_c": temperature,
        "uptime_seconds": uptime_seconds(),
        "uptime_human": human_duration(uptime_seconds()),
        "psutil": HAS_PSUTIL,
    }


def cpu_percent() -> float:
    """Return CPU utilisation since the previous call (non-blocking)."""
    if HAS_PSUTIL:
        return round(float(psutil.cpu_percent(interval=None)), 1)
    # Fallback: derive from load average over core count.
    load = load_average()
    if load is None:
        return 0.0
    cores = os.cpu_count() or 1
    return round(min(load[0] / cores * 100.0, 100.0), 1)


def memory_usage() -> ResourceUsage | None:
    """Return RAM usage."""
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        return ResourceUsage(used=int(vm.used), total=int(vm.total), percent=float(vm.percent))
    info = _read_meminfo()
    if info is None:
        return None
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    used = max(total - available, 0)
    percent = (used / total * 100.0) if total else 0.0
    return ResourceUsage(used=used, total=total, percent=percent)


def disk_usage(path: Path) -> ResourceUsage | None:
    """Return disk usage for the filesystem containing ``path``."""
    target = path if path.exists() else Path.home()
    try:
        usage = shutil.disk_usage(target)
    except OSError:  # pragma: no cover - permission/race
        return None
    percent = (usage.used / usage.total * 100.0) if usage.total else 0.0
    return ResourceUsage(used=int(usage.used), total=int(usage.total), percent=percent)


def cpu_temperature_c() -> float | None:
    """Return CPU temperature in Celsius, or ``None`` if unavailable."""
    if THERMAL_ZONE.exists():
        try:
            raw = THERMAL_ZONE.read_text(encoding="utf-8").strip()
            value = float(raw)
            return round(value / 1000.0 if value > 1000 else value, 1)
        except (OSError, ValueError):  # pragma: no cover - defensive
            pass
    if HAS_PSUTIL and hasattr(psutil, "sensors_temperatures"):
        try:
            sensors = psutil.sensors_temperatures()  # type: ignore[attr-defined]
        except (AttributeError, OSError):  # pragma: no cover - platform dependent
            sensors = {}
        for entries in sensors.values():
            for entry in entries:
                if entry.current:
                    return round(float(entry.current), 1)
    return None


def load_average() -> tuple[float, float, float] | None:
    """Return the 1/5/15 minute load average, or ``None`` on Windows."""
    if hasattr(os, "getloadavg"):
        try:
            one, five, fifteen = os.getloadavg()
            return (round(one, 2), round(five, 2), round(fifteen, 2))
        except OSError:  # pragma: no cover - defensive
            return None
    return None


def uptime_seconds() -> int:
    """Return system uptime in seconds."""
    if PROC_UPTIME.exists():
        try:
            return int(float(PROC_UPTIME.read_text(encoding="utf-8").split()[0]))
        except (OSError, ValueError, IndexError):  # pragma: no cover - defensive
            pass
    if HAS_PSUTIL:
        try:
            return int(time.time() - psutil.boot_time())
        except Exception:  # pragma: no cover - defensive
            return 0
    return 0


@lru_cache(maxsize=1)
def is_raspberry_pi() -> bool:
    """Return True when running on Raspberry Pi hardware."""
    return "raspberry pi" in (raspberry_pi_model() or "").lower()


@lru_cache(maxsize=1)
def raspberry_pi_model() -> str | None:
    """Return the device model string when available (e.g. 'Raspberry Pi 5')."""
    if DEVICE_TREE_MODEL.exists():
        try:
            return DEVICE_TREE_MODEL.read_text(encoding="utf-8").strip("\x00").strip()
        except OSError:  # pragma: no cover - defensive
            return None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("model") and "raspberry" in line.lower():
                    return line.split(":", 1)[1].strip()
        except OSError:  # pragma: no cover - defensive
            return None
    return None


def hostname() -> str:
    """Return the machine hostname."""
    try:
        return platform.node() or "localhost"
    except Exception:  # pragma: no cover - defensive
        return "localhost"


def _read_meminfo() -> dict[str, int] | None:
    if not PROC_MEMINFO.exists():
        return None
    try:
        result: dict[str, int] = {}
        for line in PROC_MEMINFO.read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                # values are in kB
                result[key.strip()] = int(parts[0]) * 1024
        return result
    except OSError:  # pragma: no cover - defensive
        return None


def human_bytes(num_bytes: int) -> str:
    """Format a byte count as a human readable string."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def human_duration(seconds: int) -> str:
    """Format a duration in seconds as a compact human string."""
    if seconds <= 0:
        return "0m"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes and not days:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "<1m"
