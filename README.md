# Onshape Export Manager

> **Automated Onshape CAD export appliance.** Connects to Onshape API accounts, matches documents by labels, and exports them in multiple formats — on a schedule or on demand. Runs as a desktop app, headless server, or Raspberry Pi appliance.

---

## What This Application Is

A self-contained export automation tool for Onshape CAD documents. You configure Onshape API accounts, create Groups that map Onshape document labels to export settings, and the system handles the rest — fetching documents, converting formats, and organizing output.

**It is not** a CAD viewer, an Onshape plugin, or a cloud service. It runs on your hardware, talks directly to Onshape's REST API, and stores exports locally.

---

## Who It's For

- **CAD teams** exporting Onshape documents to STL/STEP for manufacturing
- **3D printing farms** needing automated STL batch exports
- **Engineers** who want scheduled, hands-off exports
- **IT/DevOps** running headless on Raspberry Pi or server hardware

---

## How Users Think

1. "I have Onshape documents tagged with labels — export them nightly."
2. "I need to export this label's documents right now."
3. "Which API key is healthy? Which exports failed?"
4. "Show me everything, organized by account."

---

## Core Concepts

### Onshape Account

An API credential pair (access key + secret key) for one Onshape instance. Each account has a health status (`healthy`, `degraded`, `rate_limited`, `failed`, `disabled`), usage tracking, and failure counting. Accounts can be organized into Organizations for credential management at scale.

**Config file:** `config/accounts.json` (flat list) or `config/organizations.json` (hierarchical orgs with credentials)

### Group

A Group connects an Onshape document label to export settings. It answers: "When documents tagged with label X are found, export them using profile Y with account Z."

A Group has:
- **Friendly name** — human-readable (e.g., "Robotics Team")
- **Onshape Label ID** — 24-character hex ID from Onshape's `/api/documents/{did}/labels`
- **Assigned accounts** — which Onshape API accounts to use
- **Export profile** — which format/profile to apply
- **Schedule** — optional recurring interval
- **Enabled/disabled** toggle

**Config file:** `config/labels.json`

Groups belong to Accounts in the UI tree view, but technically a Group can be assigned to multiple accounts.

### Export Profile

Defines WHAT format(s) to export and HOW. Includes:
- **Name** — e.g., "STL", "STEP", "Multi Format"
- **Formats** — one or more `ExportFormat` values (STL, STEP, PARASOLID, OBJ, IGES, DXF, PDF, CUSTOM)
- **Format options** — per-format settings (resolution, units, etc.)
- **Bambu settings** — optional Bambu Studio integration (3MF creation, auto-arrange)

**Config file:** `config/export_profiles.json`

### Manual Export

A user-initiated export run. You select one or more Groups, optionally override the profile and date range, and queue the export. The system previews estimated document count and API calls before you commit.

### Scheduler

Runs exports on a recurring interval per Group. Intervals: `15min`, `30min`, `hourly`, `daily`, `weekly`, `monthly`. Each scheduled job creates queue entries that workers pick up.

### Worker

Background thread pool (default 4 threads) that polls the export queue every 5 seconds. Each worker:
1. Claims the next pending queue entry atomically
2. Resolves the Group → account → profile → Onshape API
3. Fetches documents matching the label
4. Iterates through Part Studios and Assemblies
5. Exports each in the configured format(s)
6. Records results in export history

Workers support config caching (5s TTL), graceful shutdown (30s timeout), and job chaining (up to 3 depth).

### Notifications

Pluggable notification channels: Discord, Slack, Teams, Email, Webhook. Each channel filters by severity (info, success, warning, error, critical) and event categories.

---

## How the UI Is Organized

| Page | Purpose |
|------|---------|
| **Dashboard** | Overview — cards, charts, system health, recent exports |
| **API Keys** | Manage Onshape API accounts (organizations + credentials) |
| **Groups** | Tree view: Accounts → Groups. Create, delete, move, enable/disable, batch export |
| **Export** | Manual export — tree selector for batch + detailed form with preview |
| **History** | Export history table — filterable, sortable |
| **Settings** | General (theme, worker), Notifications, Backups, Remote Access, Logs, About |

---

## How Raspberry Pi Mode Works

When running on a Raspberry Pi as a headless appliance:
- Binds to `0.0.0.0` (accessible from LAN)
- System health metrics exposed (CPU, RAM, disk, temperature)
- Managed via `systemctl` or `deploy/manage.sh`
- Optional Tailscale/Cloudflare Tunnel integration for remote access
- Terminal UI mode (`--tui`) for on-device monitoring

---

## How Desktop Mode Works

- Binds to `localhost` only
- Opens browser automatically on startup
- Intended for single-user, on-machine use
- All data stored locally under the project directory

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, uvicorn |
| Database | SQLite (WAL mode, versioned migrations v1→v3) |
| Frontend | Jinja2 templates, Alpine.js 3.13, Chart.js 4.4, Tailwind CSS (CDN) |
| Config | JSON files with Pydantic validation |
| Auth | scrypt password hashing, TOTP 2FA, session tokens |
| Terminal | Rich, textual, qrcode |
| Testing | pytest 9.1, httpx 0.27 |

---

## How to Extend

1. **Add export format** — Add to `ExportFormat` enum, implement translator in `export_formats.py`
2. **Add notification channel** — Implement in `notifications.py`, add to `NotificationKinds`
3. **Add UI page** — Add to `NAV_ITEMS` in `web.py`, create template in `ui/templates/`, add Alpine.js data in `app.js`
4. **Add config section** — Create Pydantic model in `configuration.py`, add to `AppConfig`

**Key principle:** All state lives in JSON config files + SQLite. No external services required.

---

## Project Layout

```
onshape_export_manager/
├── app.py, web.py, cli.py          # Entry points
├── core/                           # Business logic (30+ modules)
├── config/                         # JSON config files
├── ui/                             # Web UI (templates + static)
├── terminal/                       # Terminal UI (commands, wizard)
├── database/                       # SQLite DB + export output
├── logs/                           # Log files
└── tests/                          # 183 tests
```

---

## Quick Start

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run (first time — opens setup wizard)
python app.py --mode desktop

# Run (headless server)
python app.py --mode server --port 8080

# Run tests
python -m pytest tests/ -q
```

---

## License

Proprietary. All rights reserved.
