# Project Context — Onshape Export Manager

> **Date**: 2026-07-08  
> **Purpose**: Complete explanation of every subsystem, relationship, data flow, and design philosophy  
> **Audience**: Developers onboarding to the project

---

## What Is This?

The Onshape Export Manager is a **self-hosted desktop/web application** that automates batch export of CAD files from Onshape (a cloud-native CAD platform). It runs on a Raspberry Pi, Linux server, or macOS desktop and provides a browser-based dashboard for configuration, monitoring, and control.

### The Core Problem

Exporting files from Onshape manually is tedious:
- Open each document → Select Part Studio → Choose format → Download → Repeat
- Onshape enforces strict API rate limits per account
- You need to remember which documents need fresh exports and when
- Multi-account teams have no centralized management

### The Solution

This application automates the entire pipeline:
1. Connect your Onshape API keys
2. Tag documents in Onshape with labels
3. Configure what formats to export for each label
4. Set a schedule or trigger manually
5. The application discovers, exports, and organizes your files automatically

---

## Design Philosophy

### Appliance, Not Web App

The application is designed to be an **appliance** — like a network printer or a NAS. You set it up once on a Raspberry Pi, and it runs unattended for months. The web UI is for configuration and monitoring, not for continuous interaction.

### Offline-First for CAD Files

Exports are local files. The application writes to a directory you control. There is no cloud storage dependency. Your CAD files stay on your hardware.

### Graceful Degradation

Every subsystem is designed to fail independently. If the Onshape API is unreachable, exports queue and retry. If configuration is invalid, the application boots in a limited mode and shows clear error states. No single failure takes down the entire system.

### Event-Driven Architecture

The entire application is built around an **EventBus** — a publish/subscribe hub with a bounded ring buffer. Every subsystem (logging, audit, WebSocket streaming, notifications, metrics) consumes events through the bus rather than through direct coupling. This is the single best architectural decision in the codebase.

---

## Subsystem Map

```
┌──────────────────────────────────────────────────────────────┐
│                     WEB LAYER (web.py)                        │
│  FastAPI · Jinja2 Templates · Alpine.js · Chart.js           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ REST API │ │ SSE      │ │ WebSocket│ │ Templates│       │
│  │ 50+ eps  │ │ /stream  │ │ /ws/     │ │ 6 pages  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
└───────┼────────────┼────────────┼────────────┼──────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION (app.py)                       │
│  Service Container — holds all singleton references           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Database  │ │Config Mgr│ │Event Bus │ │API Pool  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
└───────┼────────────┼────────────┼────────────┼──────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────┐
│                    CORE SERVICES                              │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Queue Mgr │ │Scheduler │ │Export    │ │Notif.    │       │
│  │          │ │Service   │ │Engine    │ │Service   │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       │            │            │            │               │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐       │
│  │Audit     │ │Telemetry │ │Backup    │ │System    │       │
│  │Service   │ │Store     │ │Manager   │ │Monitor   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                   BACKGROUND WORKER                           │
│  Daemon thread with asyncio event loop                        │
│  Tick (every 5s): Sync Scheduler → Drain Queue → Record      │
└──────────────────────────────────────────────────────────────┘
```

---

## Subsystem Details

### 1. Configuration System (`core/configuration.py`)

**What it does**: Loads, validates, and provides access to all configuration.

**Files managed**:
- `config/config.json` — Application settings (server, retry, logging, notifications)
- `config/accounts.json` — Legacy flat account list (being deprecated)
- `config/organizations.json` — Hierarchical organization + credential model
- `config/labels.json` — Label definitions (bridge Onshape labels → export config)
- `config/export_profiles.json` — Export format combinations

**Key classes**:
- `ConfigManager` — Loads config files with Pydantic validation
- `AppConfig` — Top-level Pydantic model for config.json
- `LabelsConfig` — Pydantic model for labels.json
- `ExportProfilesConfig` — Pydantic model for profiles

**Design note**: Configuration is file-based (JSON) for transparency and backup simplicity. There is no config database — users can edit files directly if needed.

---

### 2. Database (`core/database.py`)

**What it does**: SQLite database for persistent state — export history, queue, scheduler jobs, application state, events, telemetry.

**Tables**:
- `schema_version` — Migration tracking (v1→v2→v3)
- `export_history` — Every export run with full details
- `queue` — Export job queue (pending, running, completed, failed, cancelled)
- `scheduler_jobs` — Scheduled export definitions
- `application_state` — Key-value store for runtime flags
- `events` — Persisted audit/event log
- `telemetry` — Time-series metric samples

**Key features**:
- WAL mode for concurrent reads during writes
- Versioned schema migrations applied automatically on startup
- Typed dataclass row mapping (no ORM)
- All access centralized through the `Database` class

---

### 3. EventBus (`core/events.py`)

**What it does**: Thread-safe publish/subscribe hub with a bounded ring buffer for replay.

**Key features**:
- `emit()` — Publish an event to all subscribers
- `subscribe()` — Register a callback; returns an unsubscribe token
- `recent(limit)` — Replay the last N events (for late-joining WebSocket clients)
- `EventType` enum — Typed event categories (SYSTEM_STARTUP, JOB_ENQUEUED, EXPORT_COMPLETED, etc.)
- `EventSeverity` enum — INFO, SUCCESS, WARNING, ERROR, CRITICAL
- `EventCategory` enum — EXPORTS, SYSTEM, SECURITY, CONFIG

**Subscribers**:
- `AuditService` — Persists events to the database
- `NotificationService` — Sends alerts via configured channels
- `WebSocket /ws/events` — Streams events to browser clients
- `TelemetryStore` — Samples metrics for time-series charts

**Critical property**: `EventBus.publish()` wraps every subscriber in try/except. A crashing subscriber cannot take down the system.

---

### 4. API Pool & Credential Management (`core/api_pool.py`, `core/organizations.py`)

**What it does**: Manages multiple Onshape API keys, tracks their health and rate limits, and selects the best key for each export.

**Current state** (technical debt):
- `ApiPool` — Legacy: flat list from `accounts.json`, mutable dataclass state tracking
- `CredentialPool` — New: hierarchical from `organizations.json`, EMA-based latency tracking

**Selection algorithm** (both pools):
1. Filter: only enabled, non-rate-limited credentials
2. Sort: by API usage (ascending), then failure count (ascending), then last used (oldest first)
3. Return the best candidate

**Health tracking**:
- `api_usage` — Counter of API calls today
- `failure_count` — Consecutive failures
- `rate_limit_status` — available / rate_limited / disabled
- `last_used` — Timestamp of last lease
- `rate_limit_resets_at` — When the rate limit window resets

**Migration plan**: The `ApiPool` is being deprecated in favor of `CredentialPool`. See TECHNICAL_DEBT.md ARCH-01.

---

### 5. Queue Manager (`core/queue_manager.py`)

**What it does**: Manages the export job queue with retry logic.

**Job lifecycle**:
```
PENDING → RUNNING → COMPLETED
                  → FAILED → (retry) → PENDING
                  → CANCELLED
```

**Key features**:
- `enqueue()` — Add a job to the queue with optional delayed start
- `claim_next()` — Atomically claim the next due job (TOCTOU race — see TECHNICAL_DEBT.md ARCH-04)
- `mark_completed()` / `mark_failed()` — Update job status
- `cancel()` / `requeue()` — Administrative operations
- Exponential backoff: base delay × (backoff multiplier ^ attempt number), capped at max delay
- Configurable retryable HTTP status codes (typically 429, 502, 503)

---

### 6. Scheduler (`core/scheduler.py`)

**What it does**: Manages cron-style scheduled export jobs derived from label configuration.

**Key features**:
- `sync_from_labels()` — Creates/updates/removes scheduler jobs to match label schedules
- `advance()` — Moves `next_run_at` forward for jobs whose time has arrived
- Supported intervals: 15min, 30min, hourly, daily, weekly, monthly

**Current limitation**: Scheduler is synced once at startup. Label changes while running do not update scheduler jobs until restart. See TECHNICAL_DEBT.md ARCH-05.

---

### 7. Export Engine (`core/export_engine.py`)

**What it does**: Orchestrates the complete export pipeline for a single job.

**Pipeline steps**:
1. **Account leasing** — Obtain the best available API key from the pool
2. **Document discovery** — Fetch documents matching the label, filtered by date range
3. **Workspace resolution** — Determine default workspace for each document
4. **Element discovery** — List Part Studios in each document
5. **Format export** — Route to format-specific export methods:
   - STL: Direct download from Onshape's STL endpoint
   - STEP/OBJ/IGES/Parasolid: Translation API (request translation → poll → download)
   - DXF/PDF: Drawing export endpoints
6. **File organization** — Create timestamped, non-overwriting folder structure:
   ```
   exports/{Label_Name}/{YYYY-MM-DD_HHMMSS}/{FORMAT}/{document}_{element}.{ext}
   ```

**Current limitation**: Only the first Part Studio per document is exported. See PROJECT_AUDIT.md.

---

### 8. Background Worker (`core/worker.py`)

**What it does**: Long-running daemon thread that processes the queue on a tick interval.

**Each tick** (default: every 5 seconds):
1. Advance the scheduler — enqueue any jobs whose next run time has arrived
2. Drain the queue — claim due pending jobs, run them through the ExportEngine
3. Record telemetry — store metrics for dashboard charts
4. Emit events — publish job status changes to the EventBus

**Threading model**: The worker runs on its own daemon thread with its own asyncio event loop. Queue operations are synchronized through SQLite WAL mode (but see TOCTOU race in TECHNICAL_DEBT.md).

---

### 9. Notifications (`core/notifications.py`)

**What it does**: Sends alerts via multiple channels when events occur.

**Supported channels**:
- **Discord** — Webhook-based messages with rich embeds
- **Slack** — Webhook-based messages
- **Microsoft Teams** — Webhook-based adaptive cards
- **Email** — SMTP-based delivery
- **Generic Webhook** — POST JSON to any HTTP endpoint

**Filtering**: Each channel can filter by:
- Event category (exports, system, security)
- Minimum severity (info, success, warning, error, critical)

**Loop guard**: Prevents notification-sent events from triggering infinite notification chains.

---

### 10. Audit Service (`core/audit.py`)

**What it does**: Persists all events to the database and provides query APIs.

**Key features**:
- `AuditService` — Subscribes to EventBus, writes events to the `events` table
- `list_events()` — Query with filters (category, severity, type, actor)
- `summary()` — Count by severity for activity page cards
- `categories()` — List distinct categories for filter dropdowns

---

### 11. Telemetry Store (`core/audit.py`)

**What it does**: Records time-series metric samples for dashboard charts.

**Key features**:
- `record()` — Store a metric sample with timestamp and value
- `series()` — Retrieve a metric's time series for chart rendering
- `metrics()` — List available metric names

---

### 12. Authentication (`core/auth.py`)

**What it does**: Single-owner authentication with scrypt password hashing and optional TOTP 2FA.

**Key features**:
- Single owner account (not multi-user)
- scrypt password hashing (N=2^14, r=8, p=1 — tuned for Raspberry Pi)
- Session tokens with configurable expiry (24h default, 30d with "remember me")
- Optional TOTP two-factor authentication
- Session validation via cookie (`oem_session`)

---

### 13. System Monitor (`core/system_monitor.py`)

**What it does**: Real-time system health tracking for the System page.

**Metrics collected**:
- CPU usage percentage and load average
- Memory usage (used/total/percent)
- Disk usage per mount point
- CPU temperature (Raspberry Pi thermal zone or psutil sensors)
- System uptime
- Raspberry Pi model detection

**Graceful fallback**: Uses `psutil` when available, falls back to `/proc` filesystem reads on minimal systems.

---

### 14. Backup Manager (`core/backup.py`)

**What it does**: ZIP-based backup and restore for configuration and database.

**Key features**:
- `create_backup()` — Compress config + database into a timestamped ZIP
- `list_backups()` — List available backup files
- `restore_backup()` — Extract and restore — creates a safety snapshot first
- `prune_backups()` — Keep only the N most recent backups

---

### 15. Export Formats (`core/export_formats.py`)

**What it does**: Registry of supported export formats and their options.

**Supported formats**: STL (binary/ASCII), STEP, OBJ, IGES, Parasolid, DXF, PDF

**Format definition** includes: display name, Onshape API format name, file extension, MIME type, configurable options (resolution, units, mode), and whether it requires the translation pipeline.

---

### 16. Metrics Service (`core/metrics.py`)

**What it does**: Aggregates data from all subsystems to power the dashboard.

**Key functions**:
- `dashboard_snapshot()` — Full dashboard data (charts, stats, history, health)
- `summary_counts()` — Lightweight counts for SSE streaming
- `global_search()` — Command palette search across all entities

---

### 17. Folder Manager (`core/folder_manager.py`)

**What it does**: Creates and manages the export directory structure.

**Structure**: `{export_location}/{label_name}/{timestamp}/{format}/`

**Key feature**: Timestamps include seconds, ensuring no two exports collide even within the same minute.

---

## Data Flow: An Export from Start to Finish

```
1. USER TRIGGERS EXPORT
   → Manual: POST /api/exports/run  or  Scheduled: Scheduler timer fires
   → QueueManager.enqueue() creates a PENDING job in the database

2. WORKER PICKS UP JOB (next tick, ≤5 seconds)
   → BackgroundWorker._tick()
   → QueueManager.claim_next() → claims the PENDING job, sets status RUNNING

3. EXPORT ENGINE EXECUTES
   → ExportEngine.export()
   → ApiPool.lease() → selects the best API key
   → OnshapeClient.fetch_documents_by_label() → discovers matching documents
   → OnshapeClient.list_elements() → finds Part Studios
   → For each Part Studio × each format:
     → Direct download (STL) or Translation API (STEP/OBJ/etc.)
     → Write file to disk via FolderManager
   → Record to export_history table

4. COMPLETION
   → QueueManager.mark_completed() or mark_failed()
   → EventBus.emit(EXPORT_COMPLETED) or (EXPORT_FAILED)
   → AuditService persists the event
   → NotificationService sends alert (if configured)
   → WebSocket broadcasts to connected browser clients

5. USER SEES RESULT
   → SSE stream updates summary counts
   → History page shows the new entry
   → Toast notification appears (if on Export page)
```

---

## Frontend Architecture

### Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Server Rendering | Jinja2 | Initial HTML, page structure |
| Reactivity | Alpine.js v3.13 | Client-side state, interactivity |
| Styling | Tailwind CSS (CDN) + custom CSS | Design system, glassmorphism |
| Charts | Chart.js v4.4 | Dashboard visualizations |
| Date Pickers | Flatpickr v4.6 | Date range selection |
| Real-time | SSE + WebSocket | Live updates, event streaming |

### Component Architecture

Three Alpine.js components manage the entire frontend:

1. **`appShell`** — Global shell: sidebar, topbar, theme toggle, command palette, toasts, live connection, SSE/polling for summary data. Exposed as `window.oem`.

2. **`dashboardPage`** — Dashboard: stat cards, charts (Chart.js), recent exports timeline. Receives data from `/api/metrics`.

3. **`sectionPage`** — Multi-page controller for all sub-pages. Handles 14 different page types through conditional logic. This is the most in-need-of-refactoring component (see TECHNICAL_DEBT.md FE-01).

### Real-Time Updates

Two channels for live data:

1. **SSE** (`/api/stream`) — Summary counts pushed every 4 seconds. Fallback: polling every 6 seconds.
2. **WebSocket** (`/ws/events`) — Audit events streamed in real-time. Fallback: polling every 6 seconds.

### Theme System

Dark-first with `localStorage` persistence:
- CSS custom properties (60+ variables) define the entire color palette
- `.dark` class on `<html>` toggles between dark and light
- `prefers-color-scheme` respected on first visit
- Theme persists across sessions in `localStorage`

---

## Deployment

The application is designed for two deployment modes:

### Desktop Mode
- Binds to `127.0.0.1:8080`
- Opens browser automatically
- Single-user, local machine

### Server Mode
- Binds to `0.0.0.0:8080`
- Headless (no browser)
- Managed via systemd (`deploy/onshape-export-manager.service`)
- Intended for Raspberry Pi or Linux server

### Systemd Integration

```
deploy/
├── install.sh                          # Interactive installer
├── manage.sh                           # Start/stop/status/restart
├── onshape-export-manager.service      # systemd unit file
└── reverse-proxy.md                    # Nginx/Caddy/Tailscale guide
```

---

## Testing

165 tests across 20+ test files. Framework: pytest.

| Area | Coverage | Notes |
|---|---|---|
| Core services | Good | api_pool, queue, retry, events, database, configuration |
| Export engine | Good | Format routing, folder creation |
| Web API | Moderate | Status, metrics, health endpoints tested |
| CLI | Poor | Almost entirely untested |
| Concurrency | None | No multi-worker/race condition tests |
| E2E | None | No full workflow test |

---

*End of Project Context. See SYSTEM_ARCHITECTURE.md for component-level architecture details.*
