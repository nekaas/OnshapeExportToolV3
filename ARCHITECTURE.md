# Onshape Export Manager — Architecture

> **Last updated**: 2026-07-26 — Post-simplification (TOTP, SSE, WebSocket, Chart.js, command palette removed)

## Current Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI 0.115, uvicorn |
| Database | SQLite (WAL mode, schema v3) |
| Frontend | Jinja2 templates, Alpine.js 3.13, Tailwind CSS CDN |
| Config | JSON files with Pydantic 2.7 validation |
| Auth | scrypt hashing, session tokens (TOTP removed) |
| Testing | pytest, 178 tests |

## Directory Structure

```
onshape_export_manager/
├── app.py              # Application bootstrap, create_app()
├── web.py              # FastAPI routes, middleware, ~2100 lines
├── cli.py              # CLI interface
├── core/               # Business logic (30+ modules)
│   ├── api_pool.py     # API key pool with health tracking
│   ├── audit.py        # Event auditing
│   ├── auth.py         # scrypt auth + session management
│   ├── backup.py       # Config/DB backup
│   ├── bambu.py        # Bambu Studio integration
│   ├── configuration.py # ConfigManager, Pydantic models
│   ├── database.py     # SQLite layer, 987 lines
│   ├── events.py       # EventBus pub/sub
│   ├── export_engine.py # Export orchestration, parallel
│   ├── export_formats.py # Format definitions
│   ├── folder_manager.py # Export directory structure
│   ├── jobs.py         # Job status enums
│   ├── logger.py       # Structured logging
│   ├── metrics.py      # Dashboard metrics
│   ├── models.py       # Core data models
│   ├── notifications.py # Discord/Slack/Email/webhook
│   ├── onshape_client.py # Onshape REST API client
│   ├── organizations.py # Organization/credential management
│   ├── plugins.py      # Plugin system (unused)
│   ├── profile_manager.py # Export profile CRUD
│   ├── provider.py     # Credential provider interface
│   ├── queue_manager.py # Export queue with retry
│   ├── remote_access.py # Tailscale/Cloudflare detection
│   ├── retry.py        # HTTP retry policy
│   ├── scheduler.py    # Cron-like scheduler
│   ├── security.py     # Input sanitization
│   ├── settings.py     # App paths
│   ├── system_monitor.py # CPU/RAM/disk stats
│   ├── validation.py   # Pydantic request validation
│   └── worker.py       # Background worker thread
├── config/             # JSON config files
│   ├── config.json
│   ├── accounts.json
│   ├── labels.json
│   ├── export_profiles.json
│   └── organizations.json
├── ui/                 # Web UI
│   ├── static/
│   │   ├── app.js      # Alpine.js controllers, 1626 lines
│   │   └── styles.css
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── login.html
│       ├── section.html # Main multi-page template, 945 lines
│       ├── wizard.html
│       └── not_found.html
├── terminal/           # Terminal UI
├── database/           # SQLite DB + export output
│   └── exports.db
├── exports/            # Exported files
├── logs/               # Log files
├── tests/              # 183 tests
└── deploy/             # Deployment scripts
```

## Data Flow

```
User → FastAPI → web.py → core/* → Onshape API
                  ↓
              SQLite DB
                  ↓
           Jinja2 Template
                  ↓
         Alpine.js (client)
```

## Export Pipeline

```
Queue Entry → Worker Thread → ExportEngine
  → ApiPool.lease(account) → OnshapeClient
    → fetch_documents_by_label()
    → list_part_studios()
    → export_part_studio() × N formats
    → FolderManager.create_export_folder()
  → ExportHistoryEntry
```

## Key Design Decisions

1. **SQLite, not PostgreSQL** — Single-user appliance, no network DB needed
2. **Background threads, not async workers** — Export is CPU-bound (file I/O), threads are simpler
3. **Alpine.js, not React** — Server-rendered with minimal client JS
4. **JSON config + SQLite**, not full ORM — Simple, inspectable, backup-friendly
5. **Organizations → Groups → Labels** hierarchy in JSON config, export history in SQLite

## Current Issues

1. **Schools vs Organizations** — Config uses "organizations" but concept is "schools"
2. **Mixed config sources** — Some data in JSON files, some in SQLite, no clear boundary
3. **Large web.py** — 2100 lines, should be split into routers
4. **app.js too large** — 1626 lines, needs component splitting
5. **No database migrations for config** — Config changes are manual JSON edits
6. **Limited format support** — Only 3 formats after cleanup, needs expansion
7. **Settings page incomplete** — Tabs exist but many have no functionality
