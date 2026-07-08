# System Architecture — Onshape Export Manager

> **Date**: 2026-07-08  
> **Audience**: Developers, contributors, technical evaluators  
> **Purpose**: Complete architecture reference — component design, data models, API surface, threading model, and deployment architecture

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Browser (Alpine.js SPA-like)  │  CLI (argparse commands)       │
│  ┌──────────────────────────┐  │  ┌──────────────────────────┐  │
│  │ Jinja2 Templates         │  │  │ onshape_export_manager/  │  │
│  │ Alpine.js Components     │  │  │ cli.py                   │  │
│  │ Chart.js · Flatpickr     │  │  │                          │  │
│  └──────────┬───────────────┘  │  └──────────┬───────────────┘  │
└─────────────┼──────────────────┴─────────────┼──────────────────┘
              │ HTTP/SSE/WS                     │ Python
              ▼                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WEB / CLI LAYER                             │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│  │ FastAPI Application      │  │ CLI Entrypoint               │ │
│  │ - 50+ REST endpoints     │  │ - init, run-export, backup   │ │
│  │ - SSE /api/stream        │  │ - config management          │ │
│  │ - WebSocket /ws/events   │  │ - worker control             │ │
│  │ - Jinja2 template engine │  │                              │ │
│  │ - Auth middleware         │  │                              │ │
│  │ - Rate limiter            │  │                              │ │
│  └──────────┬───────────────┘  └──────────────┬───────────────┘ │
└─────────────┼──────────────────────────────────┼─────────────────┘
              │                                  │
              ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION CONTAINER                         │
│  Application (dataclass)                                        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ Database  │ │ ConfigMgr │ │ EventBus  │ │ ApiPool   │       │
│  │ (SQLite)  │ │ (JSON)    │ │ (Pub/Sub) │ │ (Lease)   │       │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘       │
└────────┼─────────────┼─────────────┼─────────────┼──────────────┘
         │             │             │             │
         ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ QueueManager │  │ SchedulerSvc │  │ ExportEngine │          │
│  │ - enqueue    │  │ - sync jobs  │  │ - discover   │          │
│  │ - claim_next │  │ - advance    │  │ - translate  │          │
│  │ - retry      │  │ - intervals  │  │ - download   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐          │
│  │ AuditService │  │ Notification │  │ BackupMgr   │          │
│  │ - persist    │  │ Service      │  │ - zip/restore│          │
│  │ - query      │  │ - channels   │  │ - prune      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TelemetrySt. │  │ Metrics Svc  │  │ System Mon.  │          │
│  │ - record     │  │ - aggregate  │  │ - CPU/RAM    │          │
│  │ - series     │  │ - snapshot   │  │ - /proc fall │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKGROUND WORKER                              │
│  Daemon Thread + asyncio Loop                                   │
│  Tick (every 5s):                                               │
│    1. Scheduler.advance() → enqueue due jobs                    │
│    2. QueueManager.claim_next() → claim PENDING job             │
│    3. ExportEngine.export() → run export pipeline               │
│    4. Telemetry.record() → store metrics                        │
│    5. EventBus.emit() → publish results                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Layered Architecture Detail

### Foundation Layer

**No dependencies on other project modules. Pure data and utilities.**

| Module | Purpose |
|---|---|
| `models.py` | Pydantic/dataclass models for core domain types |
| `jobs.py` | Job and JobStatus enums |
| `retry.py` | Exponential backoff calculation, HTTP status classification |
| `settings.py` | AppPaths dataclass, directory bootstrapping |
| `security.py` | Secret masking, environment variable resolution (`env:VAR`) |
| `validation.py` | Pydantic request/response models for the API |

### Infrastructure Layer

**State management and I/O. Depends on Foundation only.**

| Module | Purpose |
|---|---|
| `database.py` | SQLite connection management, schema migrations, typed queries |
| `logger.py` | Multi-area rotating file logs, ANSI colorized console output |
| `events.py` | EventBus (pub/sub), EventType/Severity/Category enums |
| `configuration.py` | JSON config loading with Pydantic validation |

### Service Layer

**Business logic. Depends on Foundation + Infrastructure.**

| Module | Purpose |
|---|---|
| `api_pool.py` | Legacy flat account pool (lease, health, rate limits) |
| `organizations.py` | Organization + credential hierarchy (CredentialPool, OrganizationManager) |
| `auth.py` | Owner authentication, scrypt hashing, TOTP, session management |
| `export_formats.py` | Format registry (STL, STEP, OBJ, etc.) |
| `queue_manager.py` | Export job queue with retry and backoff |
| `scheduler.py` | Cron-style scheduler derived from label configuration |
| `profile_manager.py` | Export profile CRUD operations |
| `folder_manager.py` | Timestamped export directory creation |
| `backup.py` | ZIP backup/restore for config and database |
| `system_monitor.py` | CPU, RAM, disk, temperature via psutil or /proc |
| `metrics.py` | Dashboard data aggregation, global search |
| `notifications.py` | Multi-channel notification dispatch (Discord, Slack, Teams, Email, Webhook) |
| `remote_access.py` | Local network URL detection, Tailscale/Cloudflare status |

### Integration Layer

**External API integration. Depends on Service Layer.**

| Module | Purpose |
|---|---|
| `onshape_client.py` | Onshape REST API wrapper (auth, documents, elements, exports, translations) |
| `export_engine.py` | Complete export pipeline orchestration |

### Process Layer

**Long-running processes. Depends on all layers.**

| Module | Purpose |
|---|---|
| `worker.py` | BackgroundWorker — daemon thread, tick loop, job processing |

---

## 3. Data Models

### Database Schema (SQLite)

```sql
-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Export history
CREATE TABLE export_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label_name TEXT NOT NULL,
    export_profile TEXT NOT NULL,
    account_name TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_seconds REAL,
    success INTEGER NOT NULL DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    exported_files TEXT,          -- JSON array of {path, format, size}
    error_message TEXT,
    onshape_label_id TEXT,
    destination TEXT,
    job_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Export queue
CREATE TABLE queue (
    id TEXT PRIMARY KEY,           -- UUID
    label_name TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed/cancelled
    payload TEXT,                  -- JSON
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    reason TEXT                    -- manual/scheduled
);

-- Scheduler jobs
CREATE TABLE scheduler_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    label_name TEXT NOT NULL,
    interval TEXT NOT NULL,        -- 15min/30min/hourly/daily/weekly/monthly
    enabled INTEGER DEFAULT 1,
    next_run_at TEXT,
    last_run_at TEXT,
    created_at TEXT NOT NULL
);

-- Application state (key-value)
CREATE TABLE application_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Audit events
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT,
    actor TEXT,
    data TEXT,                     -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Telemetry time-series
CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    value REAL NOT NULL
);
CREATE INDEX idx_telemetry_metric_time ON telemetry(metric, timestamp);
```

### Configuration File Schemas

All config files use Pydantic models for validation. See `core/configuration.py` for the complete model definitions.

**config.json** (partial):
```json
{
  "app": {
    "server": { "mode": "desktop", "host": "127.0.0.1", "port": 8080, "auto_open_browser": true },
    "retry": { "max_attempts": 3, "backoff_base_seconds": 10, "backoff_max_seconds": 300, "retry_http_statuses": [429, 502, 503] },
    "logging": { "level": "info", "retention_days": 30 },
    "worker": { "poll_seconds": 5, "autostart": true, "count": 1 },
    "folders": { "exports_dir": "exports", "timestamp_format": "%Y-%m-%d_%H%M%S" },
    "notifications": { "enabled": true, "channels": [] }
  }
}
```

**labels.json**:
```json
{
  "labels": [
    {
      "friendly_name": "Robotics Team",
      "onshape_label_id": "5a7b3c9d1e2f...",
      "assigned_accounts": ["Primary", "Backup"],
      "export_location": "exports",
      "export_profile": "STL+STEP",
      "scheduler": { "enabled": true, "interval": "daily", "time": "06:00" },
      "enabled": true
    }
  ]
}
```

---

## 4. API Surface

### REST Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/status` | Full dashboard context |
| `GET` | `/api/metrics` | Aggregated dashboard data |
| `GET` | `/api/summary` | Lightweight counts (for SSE) |
| `GET` | `/api/stream` | SSE event stream |
| `GET` | `/api/accounts` | Flat account list (legacy) |
| `GET` | `/api/organizations` | Organization + credential hierarchy |
| `POST` | `/api/organizations` | Create organization |
| `DELETE` | `/api/organizations/{id}` | Delete organization |
| `POST` | `/api/organizations/{id}/credentials` | Add credential to org |
| `DELETE` | `/api/organizations/{id}/credentials/{cid}` | Delete credential |
| `POST` | `/api/organizations/{id}/credentials/{cid}/test` | Test credential |
| `POST` | `/api/organizations/import` | Migrate flat accounts to orgs |
| `GET` | `/api/labels` | List labels |
| `POST` | `/api/labels` | Create label |
| `GET` | `/api/profiles` | List export profiles |
| `POST` | `/api/profiles` | Create profile |
| `GET` | `/api/formats` | List available export formats |
| `GET` | `/api/queue` | List queue entries |
| `POST` | `/api/exports/run` | Enqueue manual export |
| `POST` | `/api/exports/preview` | Preview export estimates |
| `POST` | `/api/queue/{id}/cancel` | Cancel queued job |
| `POST` | `/api/queue/{id}/retry` | Requeue failed job |
| `GET` | `/api/history` | Export history (with filters) |
| `GET` | `/api/scheduler` | Scheduler jobs list |
| `GET` | `/api/worker` | Worker status |
| `POST` | `/api/worker/start` | Start worker |
| `POST` | `/api/worker/stop` | Stop worker |
| `GET` | `/api/system` | System health + worker + backups |
| `GET` | `/api/remote-access` | Network/URL/Tailscale info |
| `GET` | `/api/backups` | List backups |
| `POST` | `/api/backups` | Create backup |
| `GET` | `/api/logs/{area}` | Tail log file |
| `GET` | `/api/search` | Global search (command palette) |
| `GET` | `/api/events` | Persisted audit events (with filters) |
| `GET` | `/api/events/recent` | In-memory ring buffer events |
| `GET` | `/api/telemetry/metrics` | List telemetry metric names |
| `GET` | `/api/telemetry/{metric}` | Telemetry time series |
| `GET` | `/api/notifications` | List notification channels |
| `POST` | `/api/notifications` | Create notification channel |
| `PUT` | `/api/notifications/{id}` | Update notification channel |
| `DELETE` | `/api/notifications/{id}` | Delete notification channel |
| `POST` | `/api/notifications/{id}/test` | Test notification channel |
| `GET` | `/api/setup/status` | Setup wizard status |
| `POST` | `/api/setup/owner` | Create owner account |
| `POST` | `/api/setup/storage` | Set storage path |
| `POST` | `/api/setup/complete` | Mark setup complete |

### WebSocket

| Path | Purpose |
|---|---|
| `/ws/events` | Live audit event stream. Replays last 20 events on connect. |

### SSE

| Path | Purpose |
|---|---|
| `/api/stream` | Summary counts pushed every 4 seconds |

---

## 5. Threading & Concurrency Model

```
┌─────────────────────────────────────────┐
│             MAIN PROCESS                 │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Uvicorn ASGI Server               │  │
│  │ - Main thread: HTTP request loop  │  │
│  │ - Worker threads: request handlers│  │
│  │ - AsyncIO event loop              │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────┴───────────────────┐  │
│  │ BackgroundWorker (daemon thread)  │  │
│  │ - Own asyncio event loop          │  │
│  │ - Tick every 5 seconds            │  │
│  │ - Shared state: Database (WAL)    │  │
│  │ - Shared state: ApiPool (⚠️ mut)  │  │
│  │ - Shared state: EventBus (TS)     │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ NotificationService (daemon thrd) │  │
│  │ - SMTP/HTTP dispatch              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Thread Safety Status

| Component | Thread Safety | Notes |
|---|---|---|
| EventBus | ✅ Thread-safe | `threading.Lock` on all operations |
| Database (SQLite WAL) | ✅ Safe for reads | Concurrent reads OK; writes serialized by SQLite |
| ConfigManager | ⚠️ GIL-dependent | Read/write to JSON files; CPython GIL protects |
| ApiPool | ❌ Not safe | Mutable state (failure_count, api_usage) mutated without locks |
| QueueManager | ❌ TOCTOU race | `claim_next()` has read-then-write race |
| remote_access._cache | ⚠️ GIL-dependent | Module-level dict with TTL |

---

## 6. Deployment Architecture

### Single-Machine (Raspberry Pi)

```
┌─────────────────────────────────────────┐
│           RASPBERRY PI                   │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ systemd                           │  │
│  │ onshape-export-manager.service    │  │
│  │  └─ uvicorn (port 8080)           │  │
│  │     └─ FastAPI + Worker           │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Optional: Reverse Proxy            │  │
│  │ Nginx / Caddy / Tailscale Funnel  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Storage:                               │
│  /home/pi/exports/     (exported files) │
│  /home/pi/.oem/        (config + DB)    │
└─────────────────────────────────────────┘
```

### Desktop Mode (macOS/Linux/Windows)

```
┌─────────────────────────────────────────┐
│           DESKTOP / LAPTOP               │
│                                         │
│  python app.py --mode desktop           │
│  └─ uvicorn (127.0.0.1:8080)           │
│     └─ Opens browser automatically      │
│                                         │
│  Storage:                               │
│  ./exports/             (exported files) │
│  [package_dir]/         (config + DB)    │
└─────────────────────────────────────────┘
```

---

## 7. Key Design Decisions

### Why SQLite (not PostgreSQL)?

- Zero-configuration: no separate database server to install or maintain
- Single-file: easy to back up, easy to move
- WAL mode provides sufficient concurrency for single-machine deployment
- Perfect for Raspberry Pi (low resource usage)
- Trade-off: no horizontal scaling — accepted because this is a single-machine appliance

### Why File-Based Configuration (not a database)?

- Transparent: users can inspect and edit config with any text editor
- Version-controllable: config files can be tracked in git
- Backup-friendly: config is just files
- Trade-off: no concurrent editing, no schema enforcement at the filesystem level (mitigated by Pydantic validation on load)

### Why Alpine.js (not React/Vue)?

- No build step required — works directly from CDN
- Tiny footprint (~15KB) — important for Raspberry Pi
- Declarative syntax close to HTML — easy to understand for backend developers
- Trade-off: no virtual DOM, no component composition at scale, no TypeScript support

### Why Python (not Go/Rust)?

- Rich ecosystem for HTTP, JSON, SQLite
- Onshape's API is REST/JSON — Python's strengths
- Accessible to the target audience (makers, educators, engineers)
- Trade-off: GIL limits CPU-bound parallelism, but the application is I/O-bound (API calls, file writes)

### Why No API Versioning Yet?

- Version 1 has no external consumers beyond its own frontend
- Versioning adds complexity without benefit until there is an external API consumer
- Deprecation headers are already sent on `/api/*` without `/v1` prefix — ready for future versioning

---

## 8. Security Architecture

| Layer | Mechanism |
|---|---|
| Transport | HTTPS via reverse proxy (Nginx/Caddy); plain HTTP on localhost for desktop mode |
| Authentication | Single-owner model; scrypt password hashing (N=2^14); session tokens |
| 2FA | Optional TOTP via authenticator app |
| Secrets | API keys can reference env vars (`env:VAR`); masked in API responses; masked in logs |
| Rate Limiting | In-memory per-IP: 5 login attempts/60s, 120 API requests/60s |
| Session Management | HTTP-only, SameSite=Lax cookies; 24h default, 30d with "remember me" |
| Filesystem | Exports written to configurable directory; no path traversal (uses Path objects) |
| Event Sanitization | Secrets stripped from event data before broadcast |

---

*End of System Architecture. See PROJECT_CONTEXT.md for subsystem descriptions and data flow diagrams.*
