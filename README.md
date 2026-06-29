<div align="center">

# Onshape Export Manager

**Automated, multi-account Onshape export orchestration — with a premium web dashboard, a powerful CLI, and a production-grade core.**

Export STL, STEP, OBJ, IGES, and Parasolid from labelled Onshape documents across a pool of API accounts, with rate-limit-aware failover, a retrying job queue, scheduling, and a real-time analytics dashboard.

</div>

---

## Overview

Onshape Export Manager turns the original single-account "Onshape → Bambu Studio" proof-of-concept into a robust, production-quality application. It is designed for shops and teams that need to export many labelled Onshape documents repeatedly, reliably, and across multiple API accounts without hitting rate limits.

Three interfaces share one core:

- **Web dashboard** — a modern, dark/light SaaS-style UI (Tailwind + Alpine.js + Chart.js) with live statistics, charts, a command palette, global search, filterable tables, and an interactive log viewer.
- **CLI** — scriptable commands for initialisation, validation, status, profile management, and manual exports.
- **Core library** — configuration, SQLite persistence, the account pool, the Onshape client, the export engine, the queue, and the scheduler — all independently testable.

## Architecture

```
onshape_export_manager/
├── app.py                 # Application container & service wiring
├── cli.py                 # argparse command-line entrypoint
├── web.py                 # FastAPI app: pages + JSON/SSE API
├── core/
│   ├── configuration.py   # Pydantic JSON config (global/accounts/labels/profiles)
│   ├── database.py        # SQLite schema, migrations, history/queue/scheduler/state
│   ├── api_pool.py        # Rate-limit-aware account selection & failover
│   ├── onshape_client.py  # Authenticated Onshape API client (STL + translations)
│   ├── export_engine.py   # Orchestrates discovery → export → history
│   ├── export_formats.py  # Format registry & default options
│   ├── folder_manager.py  # Safe, timestamped, non-overwriting output folders
│   ├── queue_manager.py   # Retrying, delayed, claimable job queue
│   ├── scheduler.py       # Label-driven scheduled exports
│   ├── metrics.py         # Analytics, time series, health, disk usage, search
│   ├── logger.py          # Rotating, colorized, structured area logs
│   ├── profile_manager.py # Export-profile editing
│   ├── retry.py           # Shared backoff/retry policy
│   └── security.py        # Secret masking & env resolution
└── ui/                    # Templates (Jinja2) and static assets (CSS/JS)
```

The data flow for an export:

```
Label ──> ApiPool.lease() ──> OnshapeClient.fetch_documents_by_label()
      └─> for each document ──> list Part Studios ──> export each format
                                     │
                                     └─> FolderManager (timestamped folders)
                                     └─> ExportEngine records ExportHistory
                                     └─> ApiPool records success / failure / rate-limit
```

## Installation

Requires **Python 3.12+**.

```bash
pip install -r requirements.txt
python -m onshape_export_manager.cli --init
```

`--init` creates the runtime directory structure and default configuration files under `onshape_export_manager/`.

## Configuration

Configuration lives in `onshape_export_manager/config/` as human-editable JSON:

| File | Purpose |
| --- | --- |
| `config.json` | Global settings: folders, retry, scheduler, logging, UI, Bambu, worker count, timeouts. |
| `accounts.json` | Onshape API accounts (access/secret keys, enabled flag, description). |
| `labels.json` | Maps Onshape labels to accounts, export profiles, output folders, and schedules. |
| `export_profiles.json` | Export formats, per-format Onshape options, and per-profile Bambu settings. |

Secrets can be stored inline for local testing or referenced from the environment with `env:VARIABLE_NAME`:

```json
{
  "accounts": [
    {
      "name": "prod-east",
      "access_key": "env:ONSHAPE_ACCESS_KEY",
      "secret_key": "env:ONSHAPE_SECRET_KEY",
      "description": "Primary production account"
    }
  ]
}
```

Configuration is validated with Pydantic and cross-checked: every label must reference accounts and an export profile that actually exist. Run a validation pass any time:

```bash
python -m onshape_export_manager.cli --validate-config
```

### Default export profiles

`STL`, `STEP`, `OBJ`, `IGES`, `Parasolid`, `Mesh Bundle`, `CAD Bundle`, `Multi Format`, and `Bambu STL`. 3MF is intentionally excluded from the core Onshape flow and remains an optional Bambu post-processing setting (disabled by default).

## Quick start

```bash
# 1. Scaffold the project and database
python -m onshape_export_manager.cli --init
python -m onshape_export_manager.cli --init-db

# 2. Add your accounts and labels by editing config/accounts.json and config/labels.json
python -m onshape_export_manager.cli --validate-config

# 3. Inspect status
python -m onshape_export_manager.cli --accounts-status
python -m onshape_export_manager.cli --list-export-profiles

# 4. Run a manual export for a configured label
python -m onshape_export_manager.cli --run-export "Customer A" --profile "Multi Format"

# 5. Launch the web dashboard
python -m uvicorn onshape_export_manager.web:app --port 8000
# open http://127.0.0.1:8000
```

## Web dashboard

Start it with Uvicorn:

```bash
python -m uvicorn onshape_export_manager.web:app --host 127.0.0.1 --port 8000
```

Highlights:

- **Live dashboard** — headline stat cards, a 14-day export-activity area chart, account-health doughnut, success-rate gauge, queue breakdown, and storage usage, all refreshed in real time via Server-Sent Events (with polling fallback).
- **Dark & light themes** — persisted per browser, toggled instantly.
- **Command palette** — press `⌘K` / `Ctrl+K` (or `/`) to search accounts, labels, profiles, and export history from anywhere.
- **Filterable, sortable tables** for accounts, labels, profiles, the queue, the scheduler, and history.
- **Interactive log viewer** with per-area tabs and level highlighting.
- **Keyboard shortcuts** — `⌘K` palette, `⌘B` collapse sidebar, `/` search.
- **Toast notifications**, glassmorphism cards, animated transitions, and a fully responsive layout.

### REST API

The dashboard is powered by a JSON API that is equally usable for automation. OpenAPI docs are served at `/docs`.

| Endpoint | Description |
| --- | --- |
| `GET /health` | Liveness probe. |
| `GET /api/metrics` | Full analytics snapshot (summary, activity, health, queue, disk, recent history). |
| `GET /api/summary` | Lightweight headline counts (used for live polling). |
| `GET /api/stream` | Server-Sent Events stream of summary counts. |
| `GET /api/accounts` | Configured accounts with runtime health (secrets masked). |
| `GET /api/labels` | Configured labels. |
| `GET /api/profiles` | Export profiles. |
| `GET /api/formats` | Supported export formats. |
| `GET /api/queue` | Export queue entries. |
| `GET /api/history?limit=&label=&success=` | Export history with filters. |
| `GET /api/scheduler` | Scheduler jobs and running state. |
| `GET /api/logs/{area}?limit=` | Tail of a log area (`app`, `errors`, `api`, `export`, `scheduler`, `queue`, `web`, `worker`, `events`, `audit`, `notifications`). |
| `GET /api/search?q=` | Global search across resources. |
| `GET /api/events?category=&severity=&type=&actor=&limit=&offset=` | Persisted audit/event log with filters and pagination. |
| `GET /api/events/recent?limit=` | In-memory ring buffer of recent events (no SQL). |
| `GET /api/telemetry/metrics` | Metric names with recorded telemetry samples. |
| `GET /api/telemetry/{metric}?limit=` | Time series for one metric (historical charts). |
| `WS  /ws/events` | Live WebSocket stream of every event as it happens. |
| `GET/POST /api/notifications` | List or create notification channels. |
| `PUT/DELETE /api/notifications/{id}` | Update or delete a channel. |
| `POST /api/notifications/{id}/test` | Send a synthetic test message to a channel. |

### Event bus, audit log & telemetry (AI-ready foundation)

Every meaningful state change — a job starting, an export finishing, a credential
rate-limiting, a sign-in, a backup — is published as a structured `Event` onto a
process-wide **event bus** (`core/events.py`). Three subscribers fan it out:

- the **audit log** persists every event to SQLite (schema v3 `events` table) with
  filterable history, severity counts, and automatic retention;
- the **WebSocket stream** (`/ws/events`) pushes events to the browser **Activity**
  page in real time (with a polling fallback);
- **telemetry** samples (queue depth, export duration, throughput) are written to the
  `telemetry` time-series table for historical charts.

This is the substrate a future AI assistant consumes to observe and act — added now
so no major rearchitecture is needed later. Plugins can `subscribe()` to the same bus
and `emit()` their own events.

## CLI reference

| Command | Description |
| --- | --- |
| `--init`, `--init-config` | Create directories and default config files. |
| `--init-db` | Initialise / migrate the SQLite database. |
| `--validate-config` | Validate all configuration and cross-references. |
| `--database-status` | Schema version and table counts. |
| `--accounts-status` | Runtime status of each account (usage, failures, cooldowns). |
| `--queue-status` | Queue counts by state. |
| `--scheduler-status` | Scheduler running state and job counts. |
| `--list-export-formats` | Supported Part Studio formats. |
| `--list-export-profiles` | Configured export profiles. |
| `--run-export LABEL [--profile P] [--start ISO] [--end ISO] [--destination PATH]` | Run a manual export. |
| `--add-export-profile NAME --formats stl,step [--replace-profile] [--bambu-profile]` | Create/replace a profile. |

Examples:

```bash
python -m onshape_export_manager.cli --run-export "Customer A"
python -m onshape_export_manager.cli --run-export "Customer A" --profile "CAD Bundle"
python -m onshape_export_manager.cli --run-export "Customer A" \
    --profile "Multi Format" --start 2026-06-24T00:00:00Z --end 2026-06-25T23:59:59Z
python -m onshape_export_manager.cli --add-export-profile "Shop Bundle" --formats stl,step,obj
```

## Operating modes: Desktop & Server

The same codebase runs in two modes, selected by `config.json` (`server.mode`),
the `--mode` flag, or the `OEM_MODE` environment variable:

| Mode | Binds | Browser | Intended for |
| --- | --- | --- | --- |
| **desktop** | `127.0.0.1:8080` | auto-opens | Windows workstation use |
| **server** | `0.0.0.0:8080` | headless | Raspberry Pi / Linux appliance |

```bash
python app.py                 # uses config.json (default: desktop)
python app.py --mode server   # headless on all interfaces
python app.py --port 9000     # custom port
```

### Headless install on Raspberry Pi / Linux (systemd)

Runs on Raspberry Pi 4 & 5, Raspberry Pi OS, Ubuntu Server ARM64, and Debian
ARM64. The installer creates a virtual environment and a systemd service that
starts on boot:

```bash
git clone <repo> onshape-export-manager && cd onshape-export-manager
sudo ./deploy/install.sh          # installs deps + onshape-export-manager.service
```

Manage the service:

```bash
sudo ./deploy/manage.sh start | stop | restart | status | enable | disable | logs
# or directly:
sudo systemctl {start,stop,restart,status,enable,disable} onshape-export-manager
```

The service is tuned for low-power hardware (`Nice=5`, `MemoryMax=512M`,
`Restart=on-failure`). After boot, open `http://<pi-ip>:8080` from any device.

### Remote access (auto-detected on the System page)

The **System** dashboard page detects and displays whichever access method is
present — no manual configuration:

- **Tailscale** — `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`. The dashboard then shows `http://100.x.y.z:8080` and the MagicDNS URL.
- **Cloudflare Tunnel** — detected via the `cloudflared` service; status shown as Connected / Disconnected with the tunnel name.
- **Reverse proxy** — NGINX, Caddy, and Traefik are detected if installed; ready-made configs are in [`deploy/reverse-proxy.md`](deploy/reverse-proxy.md).
- **HTTPS** — Let's Encrypt certificates under `/etc/letsencrypt/live` are auto-detected; self-signed certs are supported.

### Raspberry Pi & system monitoring

The **System** page reports CPU %, RAM %, CPU temperature, disk usage, uptime,
worker count, running/queued jobs, hostname, device model, and database size —
using `psutil` when available and lightweight `/proc` readings otherwise. Cards
turn red when CPU, RAM, disk, or temperature cross safe thresholds.

### Backups

Create compressed ZIP snapshots of the configuration and SQLite database (and
optionally logs) from the System page or the API. Backups can be listed,
verified, restored (with an automatic pre-restore safety snapshot), and pruned
by retention count.

## Multi-account pool

The account pool keeps exports flowing even when an account is throttled:

- **Least-used selection** weighted by usage, failure count, and last-used time.
- **Automatic failover** to any other eligible account.
- **Rate-limit cooldowns** parsed from `Retry-After` / `X-RateLimit-Reset` headers, with automatic recovery when the cooldown expires.
- **Per-account health** (usage, failures, last error) persisted in the database and surfaced on the dashboard.

## Database

SQLite (WAL mode) with versioned migrations. Tables: `export_history`, `export_queue`, `scheduler_jobs`, `application_state`, and `schema_migrations`. Account runtime state and scheduler metadata are persisted in `application_state`.

## Logging

Structured, rotating logs are written to `onshape_export_manager/logs/`:

- Per-area files (`app`, `api`, `export`, `scheduler`, `queue`, `web`, `worker`) plus a consolidated `errors.log` for WARNING and above.
- Size-based rotation (5 MB × 5 backups), lazy file handles (no empty files, no leaked locks), optional JSON output, and colorized console output on a TTY.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `Configuration invalid: label '…' references missing …` | A label points to an account/profile that doesn't exist. Fix `labels.json` or run `--validate-config`. |
| `Missing required environment variable` | An `env:` secret reference has no matching environment variable. |
| `Every eligible Onshape account is currently rate limited` | All assigned accounts are in cooldown; the error includes the next-available time. |
| Empty STL export | The Part Studio produced no geometry, or the redirect download failed; check `logs/export.log`. |
| Web UI shows no charts | Ensure the browser can reach the CDN scripts (Tailwind/Alpine/Chart.js) or vendor them locally. |

## Verify

```bash
python -m compileall onshape_export_manager tests
python -m pytest                      # full suite (unittest-compatible)
python -m onshape_export_manager.cli --validate-config
python -m onshape_export_manager.cli --database-status
```

## Background worker

A background worker drains the export queue and advances the scheduler
automatically. In the web app it starts on launch (configurable via
`config.json` → `app.worker_autostart` / `app.worker_poll_seconds`) and can be
started/stopped from the **System** page. Manual exports are now launched
directly from the **Manual Export** page (queued and run in-browser); queued
jobs can be cancelled or retried from the **Queue** page.

Run it headless from the CLI for maintenance:

```bash
python -m onshape_export_manager.cli --run-worker    # run until Ctrl+C
python -m onshape_export_manager.cli --drain-once    # single tick, then exit
```

New API endpoints: `POST /api/exports/run`, `GET/POST /api/worker[/start|/stop]`,
`POST /api/queue/{id}/cancel`, `POST /api/queue/{id}/retry`.

### Notifications

Deliver events to **Discord, Slack, Microsoft Teams, email (SMTP), or any
webhook** — all configured from the browser **Notifications** page, no config
files. Each channel filters by minimum severity and (optionally) event category;
a **Test** button sends a synthetic message. The `NotificationService` subscribes
to the event bus, so any new event type is automatically deliverable. Delivery
runs on a background thread and never blocks the worker or a web request.

## Roadmap

- Storage providers (S3, SFTP, NAS) via the plugin system.
- Bambu Studio CLI integration for slicer post-processing.
- Export verification, checksums, and retention/cleanup policies.
- In-UI editing of accounts, labels, and profiles.

## License

MIT.
