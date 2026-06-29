#!/usr/bin/env python3
"""Top-level entrypoint for the Onshape Export Manager.

Runs the web application in one of two modes from a single codebase:

* **Desktop mode** — binds to localhost and opens a browser (Windows-friendly).
* **Server mode** — binds to all interfaces, stays headless, and is intended to
  run under systemd on a Raspberry Pi or Linux server.

The mode, host, and port resolve from (highest priority first): command-line
flags, environment variables, then ``config.json`` (``server`` section).

Examples
--------
    python app.py                      # use config.json (defaults to desktop)
    python app.py --mode server        # headless, 0.0.0.0:8080
    python app.py --mode desktop       # localhost + browser
    python app.py --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from dataclasses import dataclass

from onshape_export_manager import __version__
from onshape_export_manager.core.configuration import ConfigError, ConfigManager
from onshape_export_manager.core.remote_access import local_urls
from onshape_export_manager.core.settings import AppPaths, ensure_project_directories


@dataclass(slots=True)
class RuntimeOptions:
    """Resolved runtime options for launching the server."""

    mode: str
    host: str
    port: int
    open_browser: bool
    log_level: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onshape-export-manager",
        description="Run the Onshape Export Manager web application (desktop or server mode).",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--mode", choices=["desktop", "server"], help="Operating mode.")
    parser.add_argument("--host", help="Interface to bind (e.g. 0.0.0.0).")
    parser.add_argument("--port", type=int, help="Port to listen on.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser in desktop mode.")
    parser.add_argument("--log-level", default=None, help="Uvicorn log level (info, warning, error).")
    return parser


def resolve_options(args: argparse.Namespace) -> RuntimeOptions:
    """Resolve runtime options from CLI flags, env vars, and config.json."""
    paths = AppPaths.from_base_dir(None)
    ensure_project_directories(paths)
    config_manager = ConfigManager(paths)
    config_manager.ensure_default_files()

    mode = host = None
    port = None
    try:
        server = config_manager.load().app.server
        mode, host, port = server.mode, server.host, server.port
        auto_open = server.auto_open_browser
    except (ConfigError, Exception):  # noqa: BLE001 - fall back to safe defaults
        auto_open = True

    mode = args.mode or os.getenv("OEM_MODE") or mode or "desktop"
    host = args.host or os.getenv("OEM_HOST") or host or ("0.0.0.0" if mode == "server" else "127.0.0.1")
    port = args.port or _int_env("OEM_PORT") or port or 8080
    open_browser = mode == "desktop" and not args.no_browser and auto_open
    log_level = (args.log_level or os.getenv("OEM_LOG_LEVEL") or ("warning" if mode == "server" else "info")).lower()
    return RuntimeOptions(mode=mode, host=host, port=int(port), open_browser=open_browser, log_level=log_level)


def print_banner(options: RuntimeOptions) -> None:
    scheme = "http"
    urls = local_urls(options.port, scheme=scheme)
    line = "=" * 60
    print(line)
    print(f"  Onshape Export Manager v{__version__}  —  {options.mode.upper()} MODE")
    print(line)
    print(f"  Binding:  {options.host}:{options.port}")
    for url in urls:
        print(f"  Open:     {url}")
    if options.mode == "server":
        print("  Headless server mode — manage with systemctl or deploy/manage.sh")
    print(line, flush=True)


def schedule_browser_open(options: RuntimeOptions) -> None:
    if not options.open_browser:
        return
    host = "127.0.0.1" if options.host in {"0.0.0.0", "::"} else options.host
    url = f"http://{host}:{options.port}"

    def _open() -> None:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - browser is best-effort
            pass

    threading.Timer(1.5, _open).start()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = resolve_options(args)

    try:
        import uvicorn
    except ModuleNotFoundError:
        print("uvicorn is not installed. Run `pip install -r requirements.txt`.", file=sys.stderr)
        return 1

    from onshape_export_manager.web import create_web_app

    api = create_web_app()
    print_banner(options)
    schedule_browser_open(options)

    uvicorn.run(
        api,
        host=options.host,
        port=options.port,
        log_level=options.log_level,
        access_log=options.mode != "server",
    )
    return 0


def _int_env(name: str) -> int | None:
    value = os.getenv(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
