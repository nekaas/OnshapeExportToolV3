"""FastAPI application powering the premium web dashboard.

The web layer is intentionally thin: it exposes a JSON API over the metrics,
configuration, database, queue, and account-pool services and serves a single
client-rendered dashboard (Tailwind + Alpine.js + Chart.js + HTMX). All heavy
lifting lives in :mod:`onshape_export_manager.core`.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from onshape_export_manager import __version__
from onshape_export_manager.app import Application, create_app
from onshape_export_manager.core.configuration import ConfigError
from onshape_export_manager.core.auth import (
    SESSION_COOKIE,
    AuthError,
    AuthService,
    totp_provisioning_uri,
)
from onshape_export_manager.core.backup import BackupError, BackupManager
from onshape_export_manager.core.events import EventCategory, EventSeverity, EventType
from onshape_export_manager.core.export_formats import list_format_definitions
from onshape_export_manager.core.logger import AREA_LOG_FILES, WEB_LOGGER, get_logger, tail_log_file
from onshape_export_manager.core.metrics import (
    MetricsService,
    human_bytes,
    serialize_account_config,
    serialize_history,
    serialize_queue,
    serialize_scheduler_job,
)
from onshape_export_manager.core.organizations import (
    CredentialPool,
    OrganizationError,
    OrganizationManager,
    serialize_organization,
)
from onshape_export_manager.core.remote_access import remote_access_snapshot
from onshape_export_manager.core.system_monitor import system_snapshot
from onshape_export_manager.core.validation import (
    CreateLabelRequest,
    CreateNotificationRequest,
    CreateOwnerRequest,
    CreateProfileRequest,
    ManualExportRequest,
    SetStorageRequest,
    UpdateGroupRequest,
    UpdateNotificationRequest,
)
from onshape_export_manager.core.worker import BackgroundWorker

try:
    from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from starlette.exceptions import HTTPException as StarletteHTTPException
except ModuleNotFoundError:  # pragma: no cover - dependency installed by requirements.txt
    FastAPI = None  # type: ignore[assignment]
    Query = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]
    WebSocket = None  # type: ignore[assignment]
    WebSocketDisconnect = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    RedirectResponse = None  # type: ignore[assignment]
    StreamingResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]
    Jinja2Templates = None  # type: ignore[assignment]


# ── Primary navigation (7 items + Settings gear) ──────────────────────
# Phase 0 redesign: collapsed from 14 items.  Settings, Logs, System,
# Notifications, and Backups live under the Settings gear.
NAV_ITEMS: list[dict[str, str]] = [
    {"slug": "", "label": "Home", "icon": "home"},
    {"slug": "organizations", "label": "Organisations", "icon": "key"},
    {"slug": "export", "label": "Export", "icon": "bolt"},
    {"slug": "history", "label": "History", "icon": "history"},
]

# ── Legacy route slugs (kept accessible via URL but hidden from nav) ──
LEGACY_PAGES: set[str] = {
    "dashboard",
    "accounts",
    "api-keys",
    "labels",
    "export-profiles",
    "manual-export",
    "queue",
    "scheduler",
    "system",
    "activity",
    "logs",
    "notifications",
    "plugins",
    "settings",
}

# ── Settings sub-pages (rendered within /settings via tabs) ────────────
SETTINGS_TABS: list[str] = [
    "general",
    "notifications",
    "backups",
    "remote-access",
    "logs",
    "about",
]

ALLOWED_PAGES = {item["slug"] for item in NAV_ITEMS if item["slug"]} | LEGACY_PAGES

LOG_FILES: dict[str, str] = {"app": "app.log", "errors": "errors.log"}
LOG_FILES.update({name.rsplit(".", 1)[-1]: filename for name, filename in AREA_LOG_FILES.items()})


if StaticFiles is not None:

    class _RevalidatingStaticFiles(StaticFiles):
        """StaticFiles that asks browsers to revalidate instead of blindly
        caching, so updated CSS/JS is never served stale from disk cache."""

        def file_response(self, *args: Any, **kwargs: Any):  # type: ignore[override]
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
            return response

else:  # pragma: no cover - dependency missing
    _RevalidatingStaticFiles = None  # type: ignore[assignment, misc]


def create_web_app(base_dir: str | Path | None = None):
    """Create and configure the FastAPI application."""
    if FastAPI is None or Jinja2Templates is None or StaticFiles is None:
        raise RuntimeError("FastAPI/Jinja2 is not installed. Run `pip install -r requirements.txt`.")

    application = create_app(base_dir)
    metrics = MetricsService(application)
    auth = AuthService(application.database)
    static_dir = application.paths.ui_dir / "static"
    templates = Jinja2Templates(directory=str(application.paths.ui_dir / "templates"))
    logger = get_logger(WEB_LOGGER)
    auth_state = {"configured": auth.is_configured()}

    poll_interval = 5.0
    autostart_worker = True
    try:
        app_cfg = application.config_manager.load().app
        poll_interval = float(getattr(app_cfg, "worker_poll_seconds", 5.0))
        autostart_worker = bool(getattr(app_cfg, "worker_autostart", True))
    except Exception:  # noqa: BLE001 - fall back to defaults if config invalid
        pass
    worker = BackgroundWorker(application, poll_interval_seconds=poll_interval)

    def emit_event(
        event_type: EventType,
        message: str,
        *,
        severity: EventSeverity = EventSeverity.INFO,
        data: dict[str, Any] | None = None,
        actor: str = "web",
    ) -> None:
        """Publish an event from the web layer onto the shared bus (safe no-op
        if the bus is unavailable)."""
        bus = application.event_bus
        if bus is None:
            return
        try:
            bus.emit(
                event_type,
                message,
                severity=severity,
                data=dict(data or {}),
                source="web",
                actor=actor,
            )
        except Exception:  # noqa: BLE001 - event emission must never break a request
            logger.exception("Failed to emit web event %s", event_type)

    # -- Rate limiter (in-memory, per-IP) -----------------------------------

    import time as _time
    from collections import defaultdict

    class _RateLimiter:
        """Simple token-bucket-inspired per-IP rate limiter.

        Tracks request timestamps per key (typically ``client_ip``) in an
        in-memory dict. Thread-safe enough for a single-process ASGI server
        (Guarded by the GIL for CPython).
        """

        def __init__(self, max_requests: int, window_seconds: float) -> None:
            self._max = max_requests
            self._window = window_seconds
            self._buckets: dict[str, list[float]] = defaultdict(list)

        def allow(self, key: str) -> bool:
            now = _time.monotonic()
            timestamps = self._buckets[key]
            # Expire old entries
            cutoff = now - self._window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if len(timestamps) >= self._max:
                return False
            timestamps.append(now)
            # Prevent unbounded memory growth from exhausted IPs
            if len(self._buckets) > 10_000:
                stale = [k for k, ts in self._buckets.items() if not ts or ts[-1] < cutoff]
                for k in stale:
                    del self._buckets[k]
            return True

        def reset(self, key: str) -> None:
            self._buckets.pop(key, None)

    # Login: 5 attempts per 60 seconds before rate-limiting
    _login_limiter = _RateLimiter(max_requests=5, window_seconds=60.0)
    # API: 120 requests per 60 seconds (generous; 2 req/s sustained)
    _api_limiter = _RateLimiter(max_requests=120, window_seconds=60.0)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_api):
        if application.notifications is not None:
            try:
                application.notifications.start()
            except Exception as exc:  # noqa: BLE001 - never block startup
                logger.warning("Notification service failed to start: %s", exc)
        emit_event(EventType.SYSTEM_STARTUP, "Web application started", actor="system")
        if autostart_worker:
            try:
                worker.start()
            except Exception as exc:  # noqa: BLE001 - never block startup
                logger.warning("Worker failed to start: %s", exc)
        try:
            yield
        finally:
            worker.stop()
            emit_event(EventType.SYSTEM_SHUTDOWN, "Web application stopping", actor="system")
            if application.notifications is not None:
                application.notifications.stop()

    api = FastAPI(
        title="Onshape Export Manager",
        version=__version__,
        description="Premium export automation for Onshape across multiple accounts.",
        lifespan=lifespan,
    )

    # -- Centralized exception-to-HTTP mapping (Item 13) --------------------

    _EXCEPTION_STATUS: dict[type[Exception], int] = {
        ConfigError: 400,
        AuthError: 401,
        OrganizationError: 400,
        BackupError: 500,
        ValueError: 400,
        KeyError: 404,
        FileNotFoundError: 404,
        PermissionError: 403,
        NotImplementedError: 501,
    }

    @api.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc):
        return JSONResponse(
            {"error": exc.detail, "status_code": exc.status_code},
            status_code=exc.status_code,
        )

    @api.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc):
        status_code = 500
        for exc_type, code in _EXCEPTION_STATUS.items():
            if isinstance(exc, exc_type):
                status_code = code
                break
        logger.warning(
            "Unhandled %s in %s %s: %s",
            type(exc).__name__,
            request.method,
            request.url.path,
            exc,
        )
        return JSONResponse(
            {
                "error": str(exc) if status_code < 500 else "Internal server error",
                "status_code": status_code,
                "type": type(exc).__name__,
            },
            status_code=status_code,
        )

    # -- API versioning header (Item 15) ------------------------------------

    @api.middleware("http")
    async def _api_version_header(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/") and "/api/v" not in request.url.path:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "Sat, 01 Jan 2027 00:00:00 GMT"
            response.headers["Link"] = (
                f'</api/v1{request.url.path[4:]}>; rel="successor-version"'
            )
        return response

    api.mount(
        "/static",
        _RevalidatingStaticFiles(directory=str(static_dir)),
        name="static",
    )

    def asset_version() -> str:
        """Return a cache-busting token derived from static asset mtimes.

        Appended to CSS/JS URLs so browsers always fetch the current build
        instead of a stale cached copy.
        """
        try:
            latest = max(
                path.stat().st_mtime
                for path in static_dir.glob("*")
                if path.is_file()
            )
            return str(int(latest))
        except (ValueError, OSError):
            return __version__

    def render(
        request: Request,
        template: str,
        extra: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
    ):
        context = {
            "request": request,
            "version": __version__,
            "nav_items": NAV_ITEMS,
            "asset_version": asset_version(),
            "authenticated": getattr(request.state, "authenticated", False),
            "auth_configured": auth_state["configured"],
        }
        if extra:
            context.update(extra)
        return templates.TemplateResponse(request, template, context, status_code=status_code)

    # -- Authentication guard ----------------------------------------------

    PUBLIC_PATHS = {"/health", "/login", "/logout"}

    @api.middleware("http")
    async def auth_guard(request: Request, call_next):
        path = request.url.path
        request.state.authenticated = False

        # API rate limiting (skip public and static paths)
        if path.startswith("/api"):
            client_ip = request.client.host if request.client else "unknown"
            if not _api_limiter.allow(client_ip):
                return JSONResponse(
                    {"error": "rate limited", "retry_after_seconds": 60},
                    status_code=429,
                )

        if path in PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Setup mode: until an owner exists the app is open (first-run wizard).
        if not auth_state["configured"]:
            if auth.is_configured():
                auth_state["configured"] = True
            else:
                return await call_next(request)

        if auth.validate_session(request.cookies.get(SESSION_COOKIE)):
            request.state.authenticated = True
            return await call_next(request)

        if path.startswith("/api"):
            return JSONResponse({"error": "authentication required"}, status_code=401)
        return RedirectResponse("/login", status_code=302)

    # -- Login / logout ----------------------------------------------------

    @api.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if auth_state["configured"] and auth.validate_session(request.cookies.get(SESSION_COOKIE)):
            return RedirectResponse("/", status_code=302)
        return render(
            request,
            "login.html",
            {
                "page": "",
                "page_title": "Sign In",
                "setup": not auth.is_configured(),
                "totp_enabled": auth.totp_enabled(),
                "error": request.query_params.get("error", ""),
            },
        )

    @api.post("/login")
    async def login_submit(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        if not _login_limiter.allow(client_ip):
            emit_event(
                EventType.AUTH_LOGIN_FAILED,
                f"Rate-limited login attempt from {client_ip}",
                severity=EventSeverity.WARNING,
                data={"ip": client_ip, "reason": "rate_limited"},
                actor=client_ip,
            )
            return RedirectResponse(
                f"/login?error={_q('Too many login attempts. Please wait before trying again.')}",
                status_code=302,
            )

        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        totp = str(form.get("totp", "")).strip()
        remember = bool(form.get("remember"))

        if not auth.is_configured():
            try:
                auth.create_owner(username, password)
                auth_state["configured"] = True
            except AuthError as exc:
                return RedirectResponse(f"/login?error={_q(str(exc))}", status_code=302)
        else:
            if not auth.authenticate(username, password):
                emit_event(
                    EventType.AUTH_LOGIN_FAILED,
                    f"Failed sign-in attempt for '{username}'",
                    severity=EventSeverity.WARNING,
                    data={"username": username, "reason": "bad_password"},
                    actor=username or "unknown",
                )
                return RedirectResponse(f"/login?error={_q('Invalid username or password')}", status_code=302)
            if auth.totp_enabled() and not auth.verify_login_totp(totp):
                emit_event(
                    EventType.AUTH_LOGIN_FAILED,
                    f"Failed two-factor for '{username}'",
                    severity=EventSeverity.WARNING,
                    data={"username": username, "reason": "bad_totp"},
                    actor=username or "unknown",
                )
                return RedirectResponse(f"/login?error={_q('Invalid two-factor code')}", status_code=302)

        token = auth.create_session(remember=remember, user_agent=request.headers.get("user-agent", ""))
        response = RedirectResponse("/", status_code=302)
        _set_session_cookie(response, token, remember)
        # Reset rate limiter on successful login
        _login_limiter.reset(client_ip)
        logger.info("Owner signed in")
        emit_event(
            EventType.AUTH_LOGIN_SUCCEEDED,
            "Owner signed in",
            severity=EventSeverity.SUCCESS,
            actor=username or "owner",
        )
        return response

    @api.get("/logout")
    @api.post("/logout")
    async def logout(request: Request):
        auth.destroy_session(request.cookies.get(SESSION_COOKIE))
        response = RedirectResponse("/login", status_code=302)
        response.delete_cookie(SESSION_COOKIE)
        emit_event(EventType.AUTH_LOGOUT, "Owner signed out")
        return response

    # -- First-run setup wizard --------------------------------------------

    @api.get("/setup", response_class=HTMLResponse)
    async def setup_page(request: Request):
        if auth.is_configured() and application.database.get_state("setup.completed") == "true":
            return RedirectResponse("/", status_code=302)
        return render(request, "wizard.html", {"page": "", "page_title": "Setup"})

    @api.get("/api/setup/status")
    async def setup_status() -> dict[str, Any]:
        return {
            "configured": auth.is_configured(),
            "completed": application.database.get_state("setup.completed") == "true",
            "exports_dir": str(application.paths.exports_dir),
        }

    @api.post("/api/setup/owner")
    async def setup_owner(body: CreateOwnerRequest, request: Request):
        try:
            auth.create_owner(body.username, body.password)
            auth_state["configured"] = True
        except AuthError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        token = auth.create_session(remember=True, user_agent=request.headers.get("user-agent", ""))
        response = JSONResponse({"ok": True})
        _set_session_cookie(response, token, True)
        logger.info("Setup: owner account created")
        return response

    @api.post("/api/setup/storage")
    async def setup_storage(body: SetStorageRequest):
        path = body.exports_dir
        try:
            _update_app_config(application, lambda data: data.setdefault("folders", {}).update({"exports_dir": path}))
            Path(path).mkdir(parents=True, exist_ok=True)
        except (OSError, ConfigError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"ok": True, "path": path}

    @api.post("/api/setup/complete")
    async def setup_complete() -> dict[str, Any]:
        application.database.set_state("setup.completed", "true")
        logger.info("Setup completed")
        return {"ok": True}

    @api.post("/api/labels")
    async def api_create_label(body: CreateLabelRequest):
        try:
            label = _create_label(application, body.model_dump())
        except (ConfigError, ValueError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"friendly_name": label["friendly_name"]}

    @api.post("/api/groups")
    async def api_create_group(body: CreateLabelRequest):
        """Create a group (alias for label creation)."""
        try:
            label = _create_label(application, body.model_dump())
        except (ConfigError, ValueError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"friendly_name": label["friendly_name"], "group": label}

    @api.put("/api/groups/{group_name}")
    async def api_update_group(group_name: str, body: UpdateGroupRequest):
        """Update an existing group's settings."""
        try:
            updated = _update_label(application, group_name, body.model_dump(exclude_none=True))
        except (ConfigError, ValueError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=404 if "not found" in str(exc).lower() else 400)
        return {"friendly_name": updated["friendly_name"], "group": updated}

    @api.delete("/api/groups/{group_name}")
    async def api_delete_group(group_name: str):
        """Delete a group."""
        try:
            _delete_label(application, group_name)
        except (ConfigError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=404 if "not found" in str(exc).lower() else 400)
        return {"deleted": True, "friendly_name": group_name}

    @api.put("/api/groups/{group_name}/move")
    async def api_move_group(group_name: str, request: Request):
        """Move a group to a different account."""
        body = await request.json()
        target_account = str(body.get("account", "")).strip()
        if not target_account:
            return JSONResponse({"error": "target 'account' is required"}, status_code=400)
        try:
            updated = _move_label(application, group_name, target_account)
        except (ConfigError, ValueError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=404 if "not found" in str(exc).lower() else 400)
        return {"friendly_name": updated["friendly_name"], "group": updated}

    @api.post("/api/profiles")
    async def api_create_profile(request: Request):
        from onshape_export_manager.core.profile_manager import (
            ExportProfileManager,
            ExportProfileManagerError,
            parse_format_list,
        )

        body = await request.json()
        manager = ExportProfileManager(application.config_manager)
        try:
            profile = manager.add_profile(
                str(body.get("name", "")).strip(),
                parse_format_list(str(body.get("formats", "stl"))),
                replace=bool(body.get("replace", False)),
            )
        except (ConfigError, ValidationError, ExportProfileManagerError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"name": profile["name"], "formats": profile["formats"]}

    @api.post("/api/organizations/{org_id}/credentials/{credential_id}/test")
    async def api_test_credential(org_id: str, credential_id: str):
        return _test_credential(application, org_id, credential_id)

    # -- Health & meta ------------------------------------------------------

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "onshape-export-manager", "version": __version__}

    @api.get("/api/tree")
    async def api_tree() -> dict[str, Any]:
        """Return organisations with nested groups as a tree structure."""
        try:
            config = application.config_manager.load()
        except Exception:
            return {"organisations": []}

        # Read organisations from organizations.json directly
        from onshape_export_manager.core.configuration import read_json
        orgs_data = read_json(application.config_manager.organizations_file)
        orgs = orgs_data.get("organizations", [])

        # Build org → credential names mapping for group assignment
        org_accounts: dict[str, set[str]] = {}
        for org in orgs:
            names = set()
            for cred in org.get("credentials", []):
                names.add(cred.get("name", ""))
            org_accounts[org["name"]] = names

        # Build groups for each organisation
        labels = config.labels.labels if hasattr(config, 'labels') else []
        org_groups: dict[str, list[dict[str, Any]]] = {org["name"]: [] for org in orgs}

        for lbl in labels:
            group_data = {
                "friendly_name": lbl.friendly_name,
                "onshape_label_id": lbl.onshape_label_id,
                "export_profile": lbl.export_profile,
                "export_location": lbl.export_location,
                "schedule": lbl.scheduler.interval if lbl.scheduler else None,
                "enabled": lbl.enabled,
            }
            assigned = False
            for org_name, cred_names in org_accounts.items():
                if any(acc in cred_names for acc in lbl.assigned_accounts):
                    if org_name in org_groups:
                        org_groups[org_name].append(group_data)
                    assigned = True
            if not assigned and orgs:
                first = orgs[0]["name"]
                if first in org_groups:
                    org_groups[first].append(group_data)

        result: list[dict[str, Any]] = []
        for org in orgs:
            gs = org_groups.get(org["name"], [])
            healthy = sum(
                1 for c in org.get("credentials", [])
                if c.get("rate_limit_status", "healthy") == "healthy"
            )
            result.append({
                "id": org.get("id", org["name"]),
                "name": org["name"],
                "type": org.get("type", "other"),
                "description": org.get("description", ""),
                "enabled": org.get("enabled", True),
                "credential_count": len(org.get("credentials", [])),
                "credentials_healthy": healthy,
                "groups": gs,
                "group_count": len(gs),
            })

        return {"organisations": result}

    @api.get("/api/status")
    async def status() -> dict[str, Any]:
        return build_dashboard_context(application)

    # -- Analytics ----------------------------------------------------------

    @api.get("/api/metrics")
    async def api_metrics() -> dict[str, Any]:
        return metrics.dashboard_snapshot()

    @api.get("/api/summary")
    async def api_summary() -> dict[str, Any]:
        return metrics.summary_counts()

    @api.get("/api/stream")
    async def api_stream(request: Request):
        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break
                payload = json.dumps(metrics.summary_counts())
                yield f"data: {payload}\n\n"
                await asyncio.sleep(4)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # -- Resources ----------------------------------------------------------

    def organizations_payload() -> dict[str, Any]:
        manager = OrganizationManager(application.config_manager)
        config = manager.load()
        credentials = config.runtime_credentials()
        pool = CredentialPool(credentials, database=application.database)
        states = {state.credential_id: state for state in pool.snapshot()}
        return {
            "organizations": [serialize_organization(org, states) for org in config.organizations],
            "types": ["school", "company", "department", "customer", "workshop", "team", "other"],
        }

    @api.get("/api/organizations")
    async def api_organizations() -> dict[str, Any]:
        return organizations_payload()

    @api.post("/api/organizations")
    async def api_create_organization(request: Request) -> dict[str, Any]:
        body = await request.json()
        manager = OrganizationManager(application.config_manager)
        try:
            org = manager.create_organization(
                str(body.get("name", "")).strip(),
                org_type=str(body.get("type", "company")),
                description=str(body.get("description", "")),
                priority=int(body.get("priority", 1)),
                notes=str(body.get("notes", "")),
            )
        except (OrganizationError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        logger.info("Organization created: %s", org.name)
        emit_event(
            EventType.ORG_CREATED,
            f"Organization created: {org.name}",
            data={"id": org.id, "name": org.name},
        )
        return {"id": org.id, "name": org.name}

    @api.delete("/api/organizations/{org_id}")
    async def api_delete_organization(org_id: str) -> dict[str, Any]:
        manager = OrganizationManager(application.config_manager)
        try:
            manager.delete_organization(org_id)
        except OrganizationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return {"deleted": org_id}

    @api.post("/api/organizations/{org_id}/duplicate")
    async def api_duplicate_organization(org_id: str) -> dict[str, Any]:
        manager = OrganizationManager(application.config_manager)
        try:
            clone = manager.duplicate_organization(org_id)
        except OrganizationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return {"id": clone.id, "name": clone.name}

    @api.post("/api/organizations/{org_id}/credentials")
    async def api_add_credential(org_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        manager = OrganizationManager(application.config_manager)
        try:
            cred = manager.add_credential(
                org_id,
                name=str(body.get("name", "")).strip(),
                access_key=str(body.get("access_key", "")).strip(),
                secret_key=str(body.get("secret_key", "")).strip(),
                environment=str(body.get("environment", "production")),
                priority=int(body.get("priority", 1)),
                notes=str(body.get("notes", "")),
            )
        except (OrganizationError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        logger.info("Credential added to %s: %s", org_id, cred.name)
        return {"id": cred.id, "name": cred.name}

    @api.delete("/api/organizations/{org_id}/credentials/{credential_id}")
    async def api_delete_credential(org_id: str, credential_id: str) -> dict[str, Any]:
        manager = OrganizationManager(application.config_manager)
        try:
            manager.delete_credential(org_id, credential_id)
        except OrganizationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return {"deleted": credential_id}

    @api.post("/api/organizations/import")
    async def api_import_organizations() -> dict[str, Any]:
        manager = OrganizationManager(application.config_manager)
        config = manager.import_from_accounts()
        return {"organizations": len(config.organizations)}

    @api.get("/api/accounts")
    async def api_accounts() -> dict[str, Any]:
        config = _safe_config(application)
        runtime = (
            {state.name: state for state in application.api_pool.snapshot()}
            if application.api_pool is not None
            else {}
        )
        accounts = []
        if config is not None:
            for account in config.accounts.accounts:
                payload = serialize_account_config(account)
                state = runtime.get(account.name)
                if state is not None:
                    payload["status"] = state.rate_limit_status
                    payload["api_usage"] = state.api_usage
                    payload["failure_count"] = state.failure_count
                    payload["last_used"] = state.last_used.isoformat() if state.last_used else None
                accounts.append(payload)
        return {"accounts": accounts}

    @api.get("/api/labels")
    async def api_labels() -> dict[str, Any]:
        config = _safe_config(application)
        labels = [label.model_dump(mode="json") for label in config.labels.labels] if config else []
        return {"labels": labels}

    @api.get("/api/groups")
    async def api_groups() -> dict[str, Any]:
        """List all groups (alias for labels)."""
        config = _safe_config(application)
        labels = [label.model_dump(mode="json") for label in config.labels.labels] if config else []
        return {"groups": labels}

    @api.get("/api/profiles")
    async def api_profiles() -> dict[str, Any]:
        config = _safe_config(application)
        profiles = (
            [profile.model_dump(mode="json") for profile in config.export_profiles.profiles]
            if config
            else []
        )
        return {"profiles": profiles}

    @api.get("/api/formats")
    async def api_formats() -> dict[str, Any]:
        from onshape_export_manager.core.metrics import serialize_format

        return {"formats": [serialize_format(item) for item in list_format_definitions()]}

    @api.get("/api/queue")
    async def api_queue() -> dict[str, Any]:
        entries = application.database.list_queue(limit=500)
        return {"items": [serialize_queue(entry) for entry in entries]}

    @api.get("/api/history")
    async def api_history(
        limit: int = Query(100, ge=1, le=2000),
        label: str | None = None,
        success: bool | None = None,
    ) -> dict[str, Any]:
        entries = application.database.list_export_history(
            limit=limit, label_name=label, success=success
        )
        return {"history": [serialize_history(entry) for entry in entries]}

    @api.get("/api/scheduler")
    async def api_scheduler() -> dict[str, Any]:
        jobs = application.database.list_scheduler_jobs()
        running = application.database.get_state("scheduler.running", "false") == "true"
        return {"running": running, "jobs": [serialize_scheduler_job(job) for job in jobs]}

    # -- Worker & export execution -----------------------------------------

    @api.get("/api/worker")
    async def api_worker() -> dict[str, Any]:
        return worker.status().to_dict()

    @api.post("/api/worker/start")
    async def api_worker_start() -> dict[str, Any]:
        worker.start()
        logger.info("Worker started via API")
        return worker.status().to_dict()

    @api.post("/api/worker/stop")
    async def api_worker_stop() -> dict[str, Any]:
        worker.stop()
        logger.info("Worker stopped via API")
        return worker.status().to_dict()

    @api.post("/api/exports/run")
    async def api_run_export(body: ManualExportRequest) -> dict[str, Any]:
        """Enqueue manual export(s); supports tree selection via labels array."""
        if application.queue_manager is None:
            return JSONResponse(
                {"error": "queue is unavailable; check configuration"}, status_code=503
            )
        # Support tree selection: labels array for group-based exports
        label_names: list[str] = []
        if body.labels:
            label_names = [l.strip() for l in body.labels if l.strip()]
        elif body.label:
            label_names = [body.label.strip()]

        if not label_names:
            return JSONResponse({"error": "no labels selected"}, status_code=400)

        job_ids: list[str] = []
        for label_name in label_names:
            try:
                label, profile = _resolve_label_profile(
                    application, label_name, body.profile or ""
                )
                body_dict = body.model_dump(exclude_none=True)
                start_iso, end_iso, _ = _manual_export_window(body_dict)
            except ValueError as exc:
                return JSONResponse({"error": f"{label_name}: {exc}"}, status_code=400)

            payload: dict[str, Any] = {
                "label_name": label.friendly_name,
                "profile_name": profile.name,
                "start_iso": start_iso,
                "end_iso": end_iso,
            }
            if body.destination:
                payload["destination"] = body.destination

            job_id = application.queue_manager.enqueue(
                label_name=label.friendly_name,
                profile_name=profile.name,
                payload=payload,
                reason="manual",
            )
            job_ids.append(job_id)
            logger.info("Manual export enqueued id=%s label=%s", job_id, label.friendly_name)
            emit_event(
                EventType.JOB_ENQUEUED,
                f"Manual export queued for {label.friendly_name}",
                data={"job_id": job_id, "label": label.friendly_name, "profile": profile.name},
            )

        if not worker.running and autostart_worker:
            worker.start()
        return {"queued": True, "job_ids": job_ids, "count": len(job_ids)}

    @api.post("/api/exports/preview")
    async def api_preview_export(body: ManualExportRequest) -> dict[str, Any]:
        """Validate and estimate a manual export before it is queued."""
        try:
            return _manual_export_preview(application, body.model_dump(exclude_none=True))
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "valid": False}, status_code=400)

    @api.post("/api/queue/{job_id}/cancel")
    async def api_cancel_job(job_id: str) -> dict[str, Any]:
        if application.queue_manager is None:
            return JSONResponse({"error": "queue is unavailable"}, status_code=503)
        if application.database.get_queue_entry(job_id) is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        application.queue_manager.cancel(job_id, reason="cancelled via UI")
        emit_event(
            EventType.JOB_CANCELLED,
            f"Queued job {job_id} cancelled",
            severity=EventSeverity.WARNING,
            data={"job_id": job_id},
        )
        return {"cancelled": job_id}

    @api.post("/api/queue/{job_id}/retry")
    async def api_retry_job(job_id: str) -> dict[str, Any]:
        if application.queue_manager is None:
            return JSONResponse({"error": "queue is unavailable"}, status_code=503)
        if application.database.get_queue_entry(job_id) is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        application.queue_manager.requeue(job_id)
        if not worker.running and autostart_worker:
            worker.start()
        return {"requeued": job_id}

    @api.post("/api/queue/batch")
    async def api_queue_batch(request: Request) -> dict[str, Any]:
        """Batch cancel or retry multiple queue jobs."""
        if application.queue_manager is None:
            return JSONResponse({"error": "queue is unavailable"}, status_code=503)
        body = await request.json()
        action = str(body.get("action", "")).strip()
        job_ids = list(body.get("job_ids", []) or [])
        if not job_ids:
            return JSONResponse({"error": "job_ids is required"}, status_code=400)
        if action not in ("cancel", "retry"):
            return JSONResponse({"error": "action must be 'cancel' or 'retry'"}, status_code=400)

        results: dict[str, list[str]] = {"succeeded": [], "failed": []}
        for job_id in job_ids:
            try:
                entry = application.database.get_queue_entry(job_id)
                if entry is None:
                    results["failed"].append(job_id)
                    continue
                if action == "cancel":
                    application.queue_manager.cancel(job_id, reason="batch cancel")
                else:
                    application.queue_manager.requeue(job_id)
                results["succeeded"].append(job_id)
            except Exception:
                results["failed"].append(job_id)

        emit_event(
            EventType.JOB_CANCELLED if action == "cancel" else EventType.CUSTOM,
            f"Batch {action}: {len(results['succeeded'])} succeeded, {len(results['failed'])} failed",
            severity=EventSeverity.INFO,
            data={"action": action, "succeeded": len(results["succeeded"]), "failed": len(results["failed"])},
        )
        return {"action": action, **results}

    # -- Events / audit / telemetry (AI-ready foundation) -------------------

    @api.get("/api/events")
    async def api_events(
        limit: int = Query(100, ge=1, le=2000),
        offset: int = Query(0, ge=0),
        category: str | None = None,
        severity: str | None = None,
        type: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Return the persisted audit/event log with filters and pagination."""
        if application.audit is None:
            return {"events": [], "summary": {}, "categories": []}
        events = application.audit.list_events(
            category=category,
            severity=severity,
            event_type=type,
            actor=actor,
            limit=limit,
            offset=offset,
        )
        return {
            "events": events,
            "summary": application.audit.summary(),
            "categories": application.audit.categories(),
            "severities": [str(item) for item in EventSeverity],
        }

    @api.get("/api/events/recent")
    async def api_events_recent(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
        """Return the in-memory ring buffer of recent events (fast, no SQL)."""
        if application.event_bus is None:
            return {"events": []}
        events = application.event_bus.recent(limit=limit)
        return {"events": [event.to_dict() for event in events]}

    @api.get("/api/telemetry/metrics")
    async def api_telemetry_metrics() -> dict[str, Any]:
        """List metric names that have recorded telemetry samples."""
        if application.telemetry is None:
            return {"metrics": []}
        return {"metrics": application.telemetry.metrics()}

    @api.get("/api/telemetry/{metric}")
    async def api_telemetry_series(
        metric: str,
        limit: int = Query(500, ge=1, le=5000),
    ) -> dict[str, Any]:
        """Return a metric's time series for historical charts."""
        if application.telemetry is None:
            return {"metric": metric, "timestamps": [], "values": [], "count": 0}
        return application.telemetry.series(metric, limit=limit)

    # -- Notification channels (browser-managed) ---------------------------

    @api.get("/api/notifications")
    async def api_notifications() -> dict[str, Any]:
        config = _safe_config(application)
        notifications = config.app.notifications if config else None
        channels = (
            [_serialize_channel(channel) for channel in notifications.channels]
            if notifications
            else []
        )
        return {
            "enabled": notifications.enabled if notifications else True,
            "channels": channels,
            "kinds": ["discord", "slack", "teams", "email", "webhook"],
            "severities": [str(item) for item in EventSeverity],
            "categories": [str(item) for item in EventCategory],
        }

    @api.post("/api/notifications")
    async def api_create_notification(body: CreateNotificationRequest) -> dict[str, Any]:
        try:
            channel = _upsert_notification_channel(application, body.model_dump(), create=True)
        except (ConfigError, ValidationError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        emit_event(
            EventType.CONFIG_UPDATED,
            f"Notification channel created: {channel['name']}",
            data={"channel_id": channel["id"], "kind": channel["kind"]},
        )
        return channel

    @api.put("/api/notifications/{channel_id}")
    async def api_update_notification(channel_id: str, body: UpdateNotificationRequest) -> dict[str, Any]:
        data = body.model_dump(exclude_unset=True)
        data["id"] = channel_id
        try:
            channel = _upsert_notification_channel(application, data, create=False)
        except (ConfigError, ValidationError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        emit_event(EventType.CONFIG_UPDATED, f"Notification channel updated: {channel['name']}")
        return channel

    @api.delete("/api/notifications/{channel_id}")
    async def api_delete_notification(channel_id: str) -> dict[str, Any]:
        try:
            removed = _delete_notification_channel(application, channel_id)
        except (ConfigError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if not removed:
            return JSONResponse({"error": "channel not found"}, status_code=404)
        emit_event(EventType.CONFIG_UPDATED, f"Notification channel deleted: {channel_id}")
        return {"deleted": channel_id}

    @api.post("/api/notifications/{channel_id}/test")
    async def api_test_notification(channel_id: str) -> dict[str, Any]:
        if application.notifications is None:
            return JSONResponse({"error": "notifications unavailable"}, status_code=503)
        spec = next(
            (s for s in application.notifications.channels() if s.id == channel_id), None
        )
        if spec is None:
            return JSONResponse({"error": "channel not found or disabled"}, status_code=404)
        result = application.notifications.test_channel(spec)
        return {"ok": result.ok, "detail": result.detail, "kind": result.kind}

    if WebSocket is not None:

        @api.websocket("/ws/events")
        async def ws_events(websocket: WebSocket) -> None:
            """Stream live events to the browser over a WebSocket.

            HTTP middleware does not run for WebSocket scope, so authentication
            is enforced here: an unconfigured app (first-run) is open; otherwise
            a valid session cookie is required.
            """
            if auth_state["configured"] and not auth.validate_session(
                websocket.cookies.get(SESSION_COOKIE)
            ):
                await websocket.close(code=4401)
                return
            await websocket.accept()
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)

            def _on_event(event) -> None:
                # Called from any thread; hop back onto the web loop safely.
                try:
                    loop.call_soon_threadsafe(_enqueue, event.to_dict())
                except RuntimeError:  # pragma: no cover - loop shutting down
                    pass

            def _enqueue(payload: dict[str, Any]) -> None:
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass  # drop the oldest-style: skip when client is too slow

            token = None
            if application.event_bus is not None:
                token = application.event_bus.subscribe(_on_event)
            try:
                # Replay a little recent history so the feed is never empty.
                if application.event_bus is not None:
                    for event in application.event_bus.recent(limit=20):
                        await websocket.send_json(event.to_dict())
                while True:
                    payload = await queue.get()
                    await websocket.send_json(payload)
            except WebSocketDisconnect:
                pass
            except Exception:  # noqa: BLE001 - normal on client disconnect
                pass
            finally:
                if token is not None and application.event_bus is not None:
                    application.event_bus.unsubscribe(token)

    @api.get("/api/system")
    async def api_system() -> dict[str, Any]:
        queue_stats = (
            application.queue_manager.stats() if application.queue_manager is not None else None
        )
        config = _safe_config(application)
        worker_count = config.app.worker_count if config else 0
        return {
            "system": system_snapshot(application.paths.exports_dir),
            "workers": worker_count,
            "jobs_running": queue_stats.running if queue_stats else 0,
            "jobs_queued": queue_stats.pending if queue_stats else 0,
            "database_bytes": _file_size(application.paths.database_file),
            "worker": worker.status().to_dict(),
        }

    @api.get("/api/remote-access")
    async def api_remote_access() -> dict[str, Any]:
        config = _safe_config(application)
        port = config.app.server.port if config else 8080
        return remote_access_snapshot(port)

    @api.get("/api/backups")
    async def api_backups() -> dict[str, Any]:
        manager = BackupManager(application.paths, database=application.database)
        return {"backups": [info.to_dict() for info in manager.list_backups()]}

    @api.post("/api/backups")
    async def api_create_backup(include_logs: bool = Query(False)) -> dict[str, Any]:
        manager = BackupManager(application.paths, database=application.database)
        try:
            info = manager.create_backup(include_logs=include_logs)
        except BackupError as exc:
            emit_event(
                EventType.BACKUP_FAILED,
                "Backup failed",
                severity=EventSeverity.ERROR,
                data={"error": str(exc)},
            )
            return JSONResponse({"error": str(exc)}, status_code=500)
        logger.info("Backup created via API: %s", info.name)
        emit_event(
            EventType.BACKUP_CREATED,
            f"Backup created: {info.name}",
            severity=EventSeverity.SUCCESS,
            data=info.to_dict(),
        )
        return info.to_dict()

    # -- Export archive download --------------------------------------------

    @api.get("/api/exports/download/{label_name}")
    async def api_download_export(label_name: str, timestamp: str = Query("")):
        """Stream a completed export folder as a ZIP archive."""
        import io
        import zipfile
        from pathlib import Path as _Path

        exports_root = application.paths.exports_dir
        if timestamp:
            target = exports_root / label_name / timestamp
        else:
            # Find the most recent export for this label
            label_dir = exports_root / label_name
            if not label_dir.is_dir():
                return JSONResponse({"error": "no exports found for this label"}, status_code=404)
            subdirs = sorted(
                [d for d in label_dir.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            if not subdirs:
                return JSONResponse({"error": "no exports found for this label"}, status_code=404)
            target = subdirs[0]

        if not target.is_dir():
            return JSONResponse({"error": "export folder not found"}, status_code=404)

        # Stream a ZIP in memory (exports are typically <100MB)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(target.rglob("*")):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(target))
                    archive.write(file_path, arcname)
        buffer.seek(0)

        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in label_name)
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="export_{safe_name}.zip"',
            },
        )

    @api.get("/api/logs/{area}")
    async def api_logs(area: str, limit: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
        filename = LOG_FILES.get(area)
        if filename is None:
            return JSONResponse({"error": f"unknown log area '{area}'"}, status_code=404)
        lines = tail_log_file(application.paths.logs_dir / filename, limit=limit)
        return {"area": area, "lines": lines, "available": sorted(LOG_FILES)}

    @api.get("/api/search")
    async def api_search(q: str = Query("", alias="q")) -> dict[str, Any]:
        return metrics.global_search(q)

    # -- Legacy page title lookup ------------------------------------------
    _LEGACY_TITLES: dict[str, str] = {
        "dashboard": "Dashboard",
        "organizations": "Organizations",
        "accounts": "Accounts",
        "export-profiles": "Export Profiles",
        "manual-export": "Manual Export",
        "queue": "Queue",
        "scheduler": "Scheduler",
        "system": "System",
        "activity": "Activity",
        "logs": "Logs",
        "notifications": "Notifications",
        "plugins": "Plugins",
        "settings": "Settings",
    }

    def _page_title(slug: str) -> str:
        """Resolve a display title for a page slug (new or legacy)."""
        for item in NAV_ITEMS:
            if item["slug"] == slug:
                return item["label"]
        return _LEGACY_TITLES.get(slug, slug.replace("-", " ").title())

    # -- Pages --------------------------------------------------------------

    @api.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        if not auth.is_configured():
            return RedirectResponse("/setup", status_code=302)
        return render(request, "dashboard.html", {"page": "", "page_title": "Home"})

    @api.get("/{page_name}", response_class=HTMLResponse)
    async def section(request: Request, page_name: str):
        if page_name not in ALLOWED_PAGES:
            return render(
                request,
                "not_found.html",
                {"page": "", "page_title": "Not Found", "page_name": page_name},
                status_code=404,
            )
        # Redirect legacy pages to their new equivalents
        _redirects: dict[str, str] = {
            "dashboard": "/",
            "api-keys": "/organizations",
            "labels": "/organizations",
            "accounts": "/organizations",
            "export-profiles": "/organizations",
            "manual-export": "/export",
            "queue": "/export",
            "scheduler": "/organizations",
        }
        if page_name in _redirects:
            return RedirectResponse(_redirects[page_name], status_code=301)
        title = _page_title(page_name)
        return render(
            request,
            "section.html",
            {"page": page_name, "page_title": title},
        )

    logger.info("Web application initialized version=%s", __version__)
    return api


def build_dashboard_context(application: Application) -> dict[str, Any]:
    """Build dependency-free dashboard data used by web routes and tests.

    Retained for backwards compatibility with the original API and tests; the
    live dashboard is rendered client-side from :mod:`metrics`.
    """
    config = application.config_manager.load()
    database_status = application.database.status()
    queue_stats = (
        application.queue_manager.stats() if application.queue_manager is not None else None
    )
    account_states = (
        application.api_pool.snapshot() if application.api_pool is not None else []
    )
    scheduler_jobs = application.database.list_scheduler_jobs()
    recent_history = application.database.list_export_history(limit=10)

    return {
        "version": __version__,
        "counts": {
            "accounts": len(config.accounts.accounts),
            "labels": len(config.labels.labels),
            "export_profiles": len(config.export_profiles.profiles),
            "running_exports": database_status["export_queue"],
            "queue_size": queue_stats.pending if queue_stats else 0,
            "failed_exports": len(
                application.database.list_export_history(success=False, limit=10_000)
            ),
            "scheduler_jobs": len(scheduler_jobs),
        },
        "database": database_status,
        "queue": queue_stats,
        "accounts": account_states,
        "profiles": config.export_profiles.profiles,
        "available_formats": list_format_definitions(part_studio_only=True),
        "labels": config.labels.labels,
        "scheduler_jobs": scheduler_jobs,
        "recent_history": recent_history,
        "logs_dir": str(application.paths.logs_dir),
    }


def _safe_config(application: Application) -> Any:
    try:
        return application.config_manager.load()
    except Exception:  # pragma: no cover - surfaced via API where relevant
        return None


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _q(value: str) -> str:
    from urllib.parse import quote

    return quote(value)


def _update_app_config(application: Application, mutator) -> None:
    """Apply a mutator to config.json and re-validate before writing."""
    from onshape_export_manager.core.configuration import AppConfig, read_json, write_json

    path = application.config_manager.config_file
    data = read_json(path)
    mutator(data)
    AppConfig.model_validate(data)
    write_json(path, data)


def _serialize_channel(channel: Any) -> dict[str, Any]:
    """Serialize a notification channel, masking secret option values."""
    data = channel.model_dump(mode="json")
    options = dict(data.get("options") or {})
    for secret_key in ("smtp_password",):
        if options.get(secret_key):
            options[secret_key] = "********"
    data["options"] = options
    return data


def _upsert_notification_channel(
    application: Application, body: dict[str, Any], *, create: bool
) -> dict[str, Any]:
    """Create or update a notification channel in config.json (validated write)."""
    from uuid import uuid4

    from onshape_export_manager.core.configuration import NotificationChannelConfig

    channel_id = str(body.get("id") or "").strip() or str(uuid4())
    incoming = {
        "id": channel_id,
        "name": str(body.get("name", "")).strip(),
        "kind": str(body.get("kind", "webhook")).strip().lower(),
        "enabled": bool(body.get("enabled", True)),
        "target": str(body.get("target", "")).strip(),
        "min_severity": str(body.get("min_severity", "info")).strip().lower(),
        "categories": list(body.get("categories", []) or []),
        "options": dict(body.get("options", {}) or {}),
    }
    # Validate the single channel up-front for a precise error message.
    NotificationChannelConfig.model_validate(incoming)

    def mutator(data: dict[str, Any]) -> None:
        notifications = data.setdefault("notifications", {"enabled": True, "channels": []})
        channels = notifications.setdefault("channels", [])
        existing = next((c for c in channels if c.get("id") == channel_id), None)
        if existing is None:
            if not create:
                raise ValueError(f"channel '{channel_id}' not found")
            channels.append(incoming)
        else:
            # Preserve a masked secret: if the client sent the mask, keep the
            # stored value instead of overwriting it with asterisks.
            merged_options = dict(incoming["options"])
            for secret_key in ("smtp_password",):
                if merged_options.get(secret_key) == "********":
                    merged_options[secret_key] = (existing.get("options") or {}).get(secret_key, "")
            incoming["options"] = merged_options
            existing.update(incoming)

    _update_app_config(application, mutator)
    # Return a secret-masked copy so the client never receives stored passwords.
    masked = dict(incoming)
    masked_options = dict(incoming["options"])
    for secret_key in ("smtp_password",):
        if masked_options.get(secret_key):
            masked_options[secret_key] = "********"
    masked["options"] = masked_options
    return masked


def _delete_notification_channel(application: Application, channel_id: str) -> bool:
    """Remove a notification channel by id. Returns True if one was removed."""
    removed = {"value": False}

    def mutator(data: dict[str, Any]) -> None:
        notifications = data.get("notifications")
        if not notifications:
            return
        channels = notifications.get("channels", [])
        new_channels = [c for c in channels if c.get("id") != channel_id]
        removed["value"] = len(new_channels) != len(channels)
        notifications["channels"] = new_channels

    _update_app_config(application, mutator)
    return removed["value"]


def _create_label(application: Application, body: dict[str, Any]) -> dict[str, Any]:
    """Create and persist a new label, validating references before writing."""
    from onshape_export_manager.core.configuration import LabelsConfig, read_json, write_json

    manager = application.config_manager
    config = manager.load()
    import re
    name = re.sub(r"<[^>]*>", "", str(body.get("friendly_name", "")).strip()).replace("/", "-").strip()
    new = {
        "friendly_name": name,
        "onshape_label_id": str(body.get("onshape_label_id", "")).strip(),
        "assigned_accounts": list(body.get("assigned_accounts", []) or []),
        "export_location": str(body.get("export_location", "exports")),
        "export_profile": str(body.get("export_profile", "STL")),
        "scheduler": body.get("scheduler") or None,
        "enabled": bool(body.get("enabled", True)),
    }
    if not new["friendly_name"]:
        raise ValueError("friendly_name must not be empty")
    labels = read_json(manager.labels_file).get("labels", [])
    if any(label.get("friendly_name") == new["friendly_name"] for label in labels):
        raise ValueError(f"label '{new['friendly_name']}' already exists")

    profile_names = {profile.name for profile in config.export_profiles.profiles}
    if new["export_profile"] not in profile_names:
        raise ValueError(f"export profile '{new['export_profile']}' does not exist")
    account_names = {account.name for account in config.accounts.accounts}
    missing = set(new["assigned_accounts"]) - account_names
    if missing:
        raise ValueError(f"unknown accounts: {', '.join(sorted(missing))}")

    updated = {"labels": [*labels, new]}
    LabelsConfig.model_validate(updated)
    write_json(manager.labels_file, updated)
    # Notify the scheduler to re-sync its jobs
    if application.event_bus is not None:
        application.event_bus.emit(
            EventType.LABELS_CHANGED,
            "Label created: " + new["friendly_name"],
            data={"label": new["friendly_name"]},
        )
    return new


def _update_label(application: Application, group_name: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update an existing label/group, validating references before writing."""
    from onshape_export_manager.core.configuration import LabelsConfig, read_json, write_json

    manager = application.config_manager
    config = manager.load()
    labels = read_json(manager.labels_file).get("labels", [])
    idx = next((i for i, lbl in enumerate(labels) if lbl.get("friendly_name") == group_name), None)
    if idx is None:
        raise ValueError(f"group '{group_name}' not found")

    current = dict(labels[idx])
    import re
    if "friendly_name" in updates and updates["friendly_name"] != current["friendly_name"]:
        new_name = re.sub(r"<[^>]*>", "", str(updates["friendly_name"]).strip()).replace("/", "-").strip()
        if not new_name:
            raise ValueError("friendly_name must not be empty after sanitization")
        if any(lbl.get("friendly_name") == new_name for lbl in labels):
            raise ValueError(f"group '{new_name}' already exists")
        current["friendly_name"] = new_name

    for field in ("onshape_label_id", "export_location", "export_profile", "scheduler", "enabled"):
        if field in updates:
            current[field] = updates[field]

    if "assigned_accounts" in updates:
        account_names = {account.name for account in config.accounts.accounts}
        missing = set(updates["assigned_accounts"]) - account_names
        if missing:
            raise ValueError(f"unknown accounts: {', '.join(sorted(missing))}")
        current["assigned_accounts"] = updates["assigned_accounts"]

    if "export_profile" in updates:
        profile_names = {profile.name for profile in config.export_profiles.profiles}
        if updates["export_profile"] not in profile_names:
            raise ValueError(f"export profile '{updates['export_profile']}' does not exist")

    labels[idx] = current
    updated = {"labels": labels}
    LabelsConfig.model_validate(updated)
    write_json(manager.labels_file, updated)
    if application.event_bus is not None:
        application.event_bus.emit(
            EventType.LABELS_CHANGED,
            "Group updated: " + current["friendly_name"],
            data={"label": current["friendly_name"]},
        )
    return current


def _delete_label(application: Application, group_name: str) -> None:
    """Delete a label/group by friendly name."""
    from onshape_export_manager.core.configuration import LabelsConfig, read_json, write_json

    manager = application.config_manager
    labels = read_json(manager.labels_file).get("labels", [])
    idx = next((i for i, lbl in enumerate(labels) if lbl.get("friendly_name") == group_name), None)
    if idx is None:
        raise ValueError(f"group '{group_name}' not found")

    removed = labels.pop(idx)
    updated = {"labels": labels}
    LabelsConfig.model_validate(updated)
    write_json(manager.labels_file, updated)
    if application.event_bus is not None:
        application.event_bus.emit(
            EventType.LABELS_CHANGED,
            "Group deleted: " + removed["friendly_name"],
            data={"label": removed["friendly_name"]},
        )
    logger.info("Deleted group '%s'", group_name)


def _move_label(application: Application, group_name: str, target_account: str) -> dict[str, Any]:
    """Move a label/group to a different account."""
    from onshape_export_manager.core.configuration import LabelsConfig, read_json, write_json

    manager = application.config_manager
    config = manager.load()
    account_names = {account.name for account in config.accounts.accounts}
    if target_account not in account_names:
        raise ValueError(f"unknown account '{target_account}'")

    labels = read_json(manager.labels_file).get("labels", [])
    idx = next((i for i, lbl in enumerate(labels) if lbl.get("friendly_name") == group_name), None)
    if idx is None:
        raise ValueError(f"group '{group_name}' not found")

    current = dict(labels[idx])
    accounts = list(current.get("assigned_accounts", []))
    # Remove from all current accounts, assign to target
    current["assigned_accounts"] = [target_account]
    labels[idx] = current

    updated = {"labels": labels}
    LabelsConfig.model_validate(updated)
    write_json(manager.labels_file, updated)
    if application.event_bus is not None:
        application.event_bus.emit(
            EventType.LABELS_CHANGED,
            f"Group '{group_name}' moved to {target_account}",
            data={"label": group_name, "account": target_account},
        )
    return current


def _resolve_label_profile(application: Application, label_name: str, profile_name: str):
    """Resolve a label name (and optional profile override) to runtime objects.

    Mirrors the CLI's resolution so manual exports launched from the browser run
    through exactly the same path as ``--run-export``.
    """
    config = application.config_manager.load()
    labels = {
        label.friendly_name: label
        for label in config.runtime_labels(application.paths.package_dir)
        if label.enabled
    }
    label = labels.get(label_name)
    if label is None:
        available = ", ".join(sorted(labels)) or "none"
        raise ValueError(f"unknown or disabled label '{label_name}'. Available: {available}")

    profiles = {
        profile.name: profile
        for profile in config.runtime_export_profiles()
        if profile.enabled
    }
    resolved_name = profile_name or label.export_profile
    profile = profiles.get(resolved_name)
    if profile is None:
        available = ", ".join(sorted(profiles)) or "none"
        raise ValueError(f"unknown or disabled export profile '{resolved_name}'. Available: {available}")
    return label, profile


FORMAT_STORAGE_BYTES: dict[str, int] = {
    "stl": 1_800_000,
    "step": 3_200_000,
    "parasolid": 2_600_000,
    "obj": 2_400_000,
    "iges": 3_000_000,
    "dxf": 900_000,
    "pdf": 650_000,
}

FORMAT_RUNTIME_SECONDS: dict[str, int] = {
    "stl": 16,
    "step": 28,
    "parasolid": 24,
    "obj": 20,
    "iges": 26,
    "dxf": 12,
    "pdf": 10,
}


def _manual_export_preview(application: Application, body: dict[str, Any]) -> dict[str, Any]:
    """Build the browser preview payload for a manual export request.

    The preview intentionally avoids spending Onshape API calls. It validates
    local configuration and uses recent export history, when available, to make
    estimates; the worker still performs live document discovery at run time.
    """
    label_name = str(body.get("label", "")).strip()
    if not label_name:
        raise ValueError("label is required")
    label, profile = _resolve_label_profile(
        application,
        label_name,
        str(body.get("profile", "")).strip(),
    )
    start_iso, end_iso, window = _manual_export_window(body)
    format_payloads = _format_payloads(profile.formats)
    history = application.database.list_export_history(
        label_name=label.friendly_name,
        success=True,
        limit=100,
    )
    matching_history = [
        entry for entry in history if entry.export_profile == profile.name and entry.exported_files
    ]
    document_estimate = _estimate_documents(matching_history, format_count=len(profile.formats))
    format_count = len(profile.formats)
    files_estimate = document_estimate * format_count if document_estimate is not None else None
    per_document_storage = sum(
        FORMAT_STORAGE_BYTES.get(export_format.value, 1_500_000)
        for export_format in profile.formats
    )
    per_document_runtime = 10 + sum(
        FORMAT_RUNTIME_SECONDS.get(export_format.value, 18)
        for export_format in profile.formats
    )
    storage_bytes = (
        per_document_storage * document_estimate if document_estimate is not None else None
    )
    runtime_seconds = (
        8 + per_document_runtime * document_estimate if document_estimate is not None else None
    )
    api_calls = (
        1 + document_estimate * (2 + format_count)
        if document_estimate is not None
        else None
    )
    recent_runs = [serialize_history(entry) for entry in history[:5]]
    source = "history" if document_estimate is not None else "run_time"

    return {
        "valid": True,
        "label": {
            "name": label.friendly_name,
            "onshape_label_id": label.onshape_label_id,
            "assigned_accounts": label.assigned_accounts,
            "export_location": str(label.export_location),
        },
        "profile": {
            "name": profile.name,
            "formats": [export_format.value for export_format in profile.formats],
            "bambu_enabled": profile.bambu.enabled,
        },
        "formats": format_payloads,
        "window": {
            "start_iso": start_iso,
            "end_iso": end_iso,
            "start_display": _display_datetime(start_iso),
            "end_display": _display_datetime(end_iso),
            "duration_hours": window["duration_hours"],
            "duration_label": _duration_label(window["duration_hours"]),
        },
        "estimates": {
            "documents": document_estimate,
            "documents_source": source,
            "documents_label": (
                f"{document_estimate} document{'s' if document_estimate != 1 else ''}"
                if document_estimate is not None
                else "Discovered at run time"
            ),
            "files": files_estimate,
            "files_label": (
                f"{files_estimate} file{'s' if files_estimate != 1 else ''}"
                if files_estimate is not None
                else f"{format_count} per document"
            ),
            "api_calls": api_calls,
            "api_calls_label": (
                f"{api_calls} calls"
                if api_calls is not None
                else f"1 + {2 + format_count} per document"
            ),
            "runtime_seconds": runtime_seconds,
            "runtime_label": (
                _human_duration(runtime_seconds)
                if runtime_seconds is not None
                else f"{_human_duration(per_document_runtime)} per document"
            ),
            "storage_bytes": storage_bytes,
            "storage_label": (
                human_bytes(storage_bytes)
                if storage_bytes is not None
                else f"{human_bytes(per_document_storage)} per document"
            ),
            "per_document_storage_bytes": per_document_storage,
            "per_document_runtime_seconds": per_document_runtime,
        },
        "checks": [
            {
                "key": "label",
                "label": "Label",
                "status": "ok",
                "detail": f"{label.friendly_name} is enabled",
            },
            {
                "key": "profile",
                "label": "Profile",
                "status": "ok",
                "detail": f"{profile.name} exports {format_count} format{'s' if format_count != 1 else ''}",
            },
            {
                "key": "window",
                "label": "Window",
                "status": "ok",
                "detail": _duration_label(window["duration_hours"]),
            },
            {
                "key": "accounts",
                "label": "Accounts",
                "status": "ok" if label.assigned_accounts else "warning",
                "detail": (
                    f"{len(label.assigned_accounts)} assigned"
                    if label.assigned_accounts
                    else "Any available account may be used"
                ),
            },
        ],
        "timeline": [
            {
                "label": "Validate",
                "status": "done",
                "detail": "Configuration and time window are ready",
            },
            {
                "label": "Discover",
                "status": "pending",
                "detail": "Worker queries Onshape for matching documents",
            },
            {
                "label": "Export",
                "status": "pending",
                "detail": ", ".join(item["display_name"] for item in format_payloads),
            },
            {
                "label": "Store",
                "status": "pending",
                "detail": str(label.export_location),
            },
        ],
        "recent_runs": recent_runs,
    }


def _manual_export_window(body: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Normalize optional browser datetimes to the worker's UTC ISO contract."""
    start = _parse_web_datetime(body.get("start"))
    end = _parse_web_datetime(body.get("end"))
    now = datetime.now(timezone.utc)
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(days=1)
    if start > end:
        raise ValueError("start must be before or equal to end")
    duration_hours = round((end - start).total_seconds() / 3600, 2)
    return (
        start.astimezone(timezone.utc).isoformat(),
        end.astimezone(timezone.utc).isoformat(),
        {"duration_hours": duration_hours},
    )


def _parse_web_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid date/time: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_payloads(formats: list[Any]) -> list[dict[str, Any]]:
    from onshape_export_manager.core.export_formats import get_format_definition

    payloads = []
    for export_format in formats:
        definition = get_format_definition(export_format)
        payloads.append(
            {
                "format": export_format.value,
                "display_name": definition.display_name,
                "extension": definition.default_extension,
            }
        )
    return payloads


def _estimate_documents(history: list[Any], *, format_count: int) -> int | None:
    if not history or format_count <= 0:
        return None
    samples = [
        max(1, round(len(entry.exported_files) / format_count))
        for entry in history[:10]
        if entry.exported_files
    ]
    if not samples:
        return None
    samples.sort()
    midpoint = len(samples) // 2
    if len(samples) % 2:
        return samples[midpoint]
    return max(1, round((samples[midpoint - 1] + samples[midpoint]) / 2))


def _display_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _duration_label(hours: float) -> str:
    if hours < 1:
        return f"{round(hours * 60)} minutes"
    if hours < 48:
        return f"{hours:g} hours"
    days = hours / 24
    return f"{days:.1f} days"


def _human_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(round(float(seconds)))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s" if sec else f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def _test_credential(application: Application, org_id: str, credential_id: str):
    """Build a client from a stored credential and probe the Onshape API."""
    import time

    from onshape_export_manager.core.onshape_client import OnshapeClient, RequestRetryPolicy
    from onshape_export_manager.core.organizations import CredentialPool, OrganizationManager

    manager = OrganizationManager(application.config_manager)
    config = manager.load()
    org = next((o for o in config.organizations if o.id == org_id), None)
    if org is None:
        return JSONResponse({"error": "organization not found"}, status_code=404)
    credential = next((c for c in org.credentials if c.id == credential_id), None)
    if credential is None:
        return JSONResponse({"error": "credential not found"}, status_code=404)

    try:
        runtime = credential.to_runtime(org.name, resolve_env=True)
    except ConfigError as exc:
        return {"ok": False, "error": str(exc)}

    app_config = application.config_manager.load()
    client = OnshapeClient(
        account=runtime,  # duck-typed: name/access_key/secret_key
        base_url=app_config.app.onshape_base_url,
        retry_policy=RequestRetryPolicy(
            max_attempts=1, request_timeout_seconds=app_config.app.request_timeout_seconds
        ),
    )
    start = time.monotonic()
    try:
        response = client.api_get("/documents?limit=1", retries=1)
    except Exception as exc:  # noqa: BLE001 - report any connection error to the UI
        return {"ok": False, "error": str(exc)}
    latency = round((time.monotonic() - start) * 1000, 1)
    if response.status_code == 200:
        try:
            CredentialPool(config.runtime_credentials(), database=application.database).record_success(
                credential_id, latency_ms=latency
            )
        except Exception:  # noqa: BLE001 - state update is best-effort
            pass
        return {"ok": True, "latency_ms": latency}
    return {"ok": False, "error": f"HTTP {response.status_code}", "latency_ms": latency}


def _set_session_cookie(response: Any, token: str, remember: bool) -> None:
    max_age = 30 * 24 * 3600 if remember else None
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
    )


app = create_web_app() if FastAPI is not None else None
