# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Points                          │
│  app.py (web server)  │  cli.py (terminal)              │
├─────────────────────────────────────────────────────────┤
│                  Web Layer (web.py)                      │
│  FastAPI router  │  Jinja2 templates  │  55+ API routes │
├─────────────────────────────────────────────────────────┤
│                     Core Services                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │  Worker  │ │ Scheduler│ │  Export  │ │ API Pool  │  │
│  │  (4 th.) │ │          │ │  Engine  │ │            │  │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├───────────┤  │
│  │  Auth    │ │  Queue   │ │ Profiles │ │  Events   │  │
│  │ Service  │ │  Manager │ │ Manager  │ │    Bus    │  │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├───────────┤  │
│  │ Notify   │ │  Backup  │ │  Config  │ │  Metrics  │  │
│  │ Service  │ │  Manager │ │  Manager │ │  Tracker  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
├─────────────────────────────────────────────────────────┤
│                   Data Layer                             │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │   SQLite (WAL)   │  │  JSON Config Files (5)     │   │
│  │  exports.db      │  │  config.json, accounts.json│   │
│  │  v3 schema       │  │  labels.json, profiles.json│   │
│  │  9 tables        │  │  organizations.json        │   │
│  └──────────────────┘  └────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                   File System                            │
│  exports/{label}/{timestamp}/{format}/  │  logs/        │
│  database/backups/                      │               │
└─────────────────────────────────────────────────────────┘
```

## Module Map

| Module | Responsibility | Key Classes |
|--------|---------------|-------------|
| `app.py` | Entry point, CLI parsing, banner | `RuntimeOptions` |
| `onshape_export_manager/app.py` | Application bootstrap, service wiring | `Application`, `create_app()` |
| `web.py` | FastAPI app, 55+ API routes, auth middleware, rate limiting | `create_web_app()` |
| `core/configuration.py` | JSON config management, Pydantic models, hot-reload | `ConfigManager`, `ConfigWatcher`, `AppConfig` |
| `core/database.py` | SQLite layer, schema v3, migrations | `Database`, `ExportHistoryEntry` |
| `core/worker.py` | Multi-threaded job processor | `BackgroundWorker` |
| `core/export_engine.py` | Export orchestration | `ExportEngine` |
| `core/onshape_client.py` | Onshape REST API wrapper | `OnshapeClient` |
| `core/auth.py` | scrypt auth, TOTP, sessions | `AuthService` |
| `core/scheduler.py` | Recurring export scheduling | `Scheduler` |
| `core/queue_manager.py` | Atomic job queue | `QueueManager` |
| `core/events.py` | Pub/sub event bus | `EventBus`, `EventType` |
| `core/models.py` | Shared dataclasses | `OnshapeAccount`, `ExportProfile`, `LabelDefinition` |
| `core/validation.py` | Pydantic request models | `ManualExportRequest`, `CreateLabelRequest` |
| `core/export_formats.py` | Format registry and translation | format constants |
| `core/profile_manager.py` | Export profile CRUD | `ExportProfileManager` |
| `core/api_pool.py` | Thread-safe credential pool | `ApiPool` |
| `core/organizations.py` | Org hierarchy management | `OrganizationManager`, `CredentialPool` |
| `core/folder_manager.py` | Output directory structure | `FolderManager` |
| `core/backup.py` | Config + DB backup/restore | `BackupManager` |
| `core/remote_access.py` | Network diagnostics, Tailscale | `remote_access_snapshot()` |
| `core/system_monitor.py` | CPU, RAM, disk, temp | `system_snapshot()` |
| `core/metrics.py` | Export analytics, dashboard | `metrics.dashboard_snapshot()` |
| `core/notifications.py` | Discord, Slack, Teams, Email, Webhook | `NotificationService` |
| `core/jobs.py` | Job state machine | `ExportJob` |
| `core/retry.py` | Exponential backoff | `RetryPolicy` |
| `core/security.py` | Input sanitization, token generation | utility functions |
| `core/settings.py` | App directory paths | `AppPaths` |
| `core/logger.py` | Structured JSON + text logging | `configure_logging()` |

## Data Flow: Export Request

```
User clicks "Export Selected"
  → POST /api/exports/run { labels: [...] }
    → web.py validates request (ManualExportRequest)
    → QueueManager.enqueue() → INSERT into export_queue
    → EventBus emits JOB_ENQUEUED
  → BackgroundWorker.poll()
    → QueueManager.claim_next() → atomic UPDATE...RETURNING
    → Worker._run_job()
      → Resolve Group → Account → Profile
      → OnshapeClient.fetch_labeled_documents()
      → ExportEngine.export_document() per Part Studio
      → FolderManager organizes output
      → Database.insert_history() records result
      → EventBus emits JOB_COMPLETED or JOB_FAILED
```

## Data Flow: Config Hot-Reload

```
ConfigWatcher thread loops every 5s
  → checks mtime of config.json, accounts.json, labels.json, profiles.json
  → if changed: clears ConfigManager cache, triggers reload
  → Scheduler.on_labels_changed() re-syncs jobs
  → Worker invalidates its config cache
```

## Thread Model

- **1 main thread** — uvicorn/FastAPI async event loop
- **1 config watcher thread** — polls for config file changes
- **N worker threads** (default 4) — process export jobs from queue
- **1 scheduler thread** — runs recurring export triggers
- **1 notification thread** — dispatches alerts

All shared mutable state is protected by `threading.Lock`:
- `ApiPool._lock` — credential round-robin
- `CredentialPool._lock` — organization credential selection
- `QueueManager` uses SQLite's built-in locking (WAL mode permits concurrent reads)
- `EventBus._lock` — thread-safe event emission

## Database Schema (v3)

```
schema_migrations  — version tracking
export_history     — completed/failed export runs
export_queue       — pending/running/retrying jobs
scheduler_jobs     — recurring schedule entries
application_state  — key-value store for setup/completion flags
auth_owner         — single owner account (id=1)
auth_sessions      — session token hashes
events             — persisted audit log
telemetry          — time-series metrics
```

## Security Model

- **Auth**: Single owner, scrypt password hashing, TOTP 2FA, SHA-256 session tokens
- **Cookies**: HttpOnly, Secure (in production), SameSite=Lax
- **Secrets**: API keys support `env:VARIABLE` references; never logged
- **Input**: Pydantic strict validation with `extra="forbid"`; HTML escaped by Alpine.js `x-text`
- **Rate limiting**: Token bucket — 5 login attempts/min, 120 API requests/min per IP
- **File access**: All export downloads validated against exports directory; no path traversal
