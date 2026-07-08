# Feature Inventory & Rationalization Audit

> **Primary Mission**: Manage Onshape accounts → labels → profiles → export reliably → schedule → track history → notify.
> If a feature does not directly improve this workflow, it must justify its existence.

---

## FEATURE INVENTORY

Every feature in the application, assessed against the primary mission.

---

### 1. Onshape Account Management

| Attribute | Assessment |
|---|---|
| **Purpose** | Store and manage Onshape API access/secret key pairs |
| **Who uses it** | Every user — this is how the app connects to Onshape |
| **Frequency** | Setup once, occasionally add new accounts |
| **Dependencies** | Configuration system, security (secret masking), API pool |
| **Status** | Implemented — flat `accounts.json` + hierarchical `organizations.json` (dual model) |
| **Maintenance cost** | HIGH — two code paths (ApiPool + CredentialPool) doing the same thing |
| **Complexity** | HIGH — two selection algorithms, two state tracking mechanisms, two persistence strategies |
| **Expansion potential** | LOW — two models means every new credential feature must be built twice |
| **Technical debt** | HIGH — dual model is the single largest source of duplication |
| **Overall value** | CORE — but the dual implementation undermines it |

### 2. Organization Model

| Attribute | Assessment |
|---|---|
| **Purpose** | Group credentials hierarchically (school/company/department/customer/workshop/team) |
| **Who uses it** | Multi-team deployments with many API keys |
| **Frequency** | Rarely — most users have 1-3 accounts |
| **Dependencies** | CredentialPool, organizations.json, OrganizationManager |
| **Status** | Implemented but incomplete — parallel to flat accounts |
| **Maintenance cost** | HIGH — entire parallel subsystem |
| **Complexity** | HIGH — priority ordering, EMA latency, rolling daily counters |
| **Expansion potential** | MEDIUM — but the org model is overengineered for V1 |
| **Technical debt** | HIGH — the migration from flat accounts was started but never completed |
| **Overall value** | IMPORTANT for multi-tenant, but CORE can use flat accounts alone |

### 3. Labels

| Attribute | Assessment |
|---|---|
| **Purpose** | Bridge Onshape document labels to export configuration |
| **Who uses it** | Every user — labels define WHAT to export |
| **Frequency** | Set up once per label, occasionally modify |
| **Dependencies** | Accounts (which can export), profiles (what format), scheduler (when) |
| **Status** | Implemented — labels.json with Pydantic validation |
| **Maintenance cost** | LOW — clean model, single code path |
| **Complexity** | LOW |
| **Expansion potential** | HIGH — label groups, label inheritance, dynamic labels |
| **Technical debt** | LOW |
| **Overall value** | **CORE** — without labels, nothing can be exported |

### 4. Export Profiles

| Attribute | Assessment |
|---|---|
| **Purpose** | Define export formats and options (STL binary/ASCII, resolution, units) |
| **Who uses it** | Every user — profiles define HOW to export |
| **Frequency** | Set up once, rarely change |
| **Dependencies** | Export formats registry, export engine, Bambu settings (optional) |
| **Status** | Implemented — 9 default profiles, export_profiles.json |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM — options are `dict[str, Any]` (untyped) |
| **Expansion potential** | MEDIUM — per-format option schemas would tighten validation |
| **Technical debt** | LOW — untyped options are the main gap |
| **Overall value** | **CORE** |

### 5. Manual Export

| Attribute | Assessment |
|---|---|
| **Purpose** | Trigger ad-hoc exports from web UI or CLI |
| **Who uses it** | Every user |
| **Frequency** | Daily — this is the primary action |
| **Dependencies** | Labels, profiles, accounts, queue, worker, export engine |
| **Status** | Implemented — web UI wizard + CLI `--run-export` |
| **Maintenance cost** | LOW |
| **Complexity** | MEDIUM — date range picker, preview, templates |
| **Expansion potential** | HIGH |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 6. Queue

| Attribute | Assessment |
|---|---|
| **Purpose** | Manage export jobs: enqueue, claim, retry, cancel, track status |
| **Who uses it** | System (worker) + users (monitor/cancel) |
| **Frequency** | Every export flows through the queue |
| **Dependencies** | Database, retry policy, export engine, worker |
| **Status** | Implemented — SQLite-backed with retry/backoff |
| **Maintenance cost** | LOW |
| **Complexity** | MEDIUM — state machine, retry logic, atomic claims (now fixed) |
| **Expansion potential** | MEDIUM |
| **Technical debt** | LOW (recently hardened) |
| **Overall value** | **CORE** |

### 7. Scheduler

| Attribute | Assessment |
|---|---|
| **Purpose** | Automatically export labels on a recurring schedule |
| **Who uses it** | Users who want hands-off exports |
| **Frequency** | Configured per label, runs automatically |
| **Dependencies** | Labels, queue, worker |
| **Status** | Implemented — 15min/30min/hourly/daily/weekly/monthly intervals |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM |
| **Expansion potential** | MEDIUM — cron expressions, calendar-based scheduling |
| **Technical debt** | LOW (recently fixed: re-syncs on label changes) |
| **Overall value** | **CORE** — automation is the primary value prop |

### 8. Export History

| Attribute | Assessment |
|---|---|
| **Purpose** | Record every export with results, timing, and errors |
| **Who uses it** | Users auditing exports, debugging failures |
| **Frequency** | Consulted when something goes wrong or for reporting |
| **Dependencies** | Database, export engine |
| **Status** | Implemented — export_history table with filters |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | MEDIUM — analytics, trends, storage forecasting |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 9. Notifications

| Attribute | Assessment |
|---|---|
| **Purpose** | Alert users via Discord/Slack/Teams/Email/Webhook when exports complete or fail |
| **Who uses it** | Operators who don't watch the dashboard |
| **Frequency** | On export events |
| **Dependencies** | EventBus, notification channels config |
| **Status** | Implemented — 5 channel types, severity filtering, test button |
| **Maintenance cost** | MEDIUM — 5 separate sender implementations |
| **Complexity** | MEDIUM — delivery thread, queue, loop guard |
| **Expansion potential** | HIGH — could become a plugin provider |
| **Technical debt** | LOW |
| **Overall value** | **CORE** — notification of failures is essential for unattended operation |

### 10. Web Dashboard

| Attribute | Assessment |
|---|---|
| **Purpose** | Visual monitoring and control of exports, accounts, queue, scheduler |
| **Who uses it** | Every user who wants a GUI |
| **Frequency** | Daily |
| **Dependencies** | FastAPI, Jinja2, Alpine.js, Chart.js, Tailwind CSS, Flatpickr |
| **Status** | Implemented — ~15 pages, real-time updates, dark/light theme |
| **Maintenance cost** | HIGH — 1,500-line app.js, 1,300-line web.py, 5 CDN dependencies |
| **Complexity** | HIGH — SSR + SPA hybrid, SSE + WebSocket, 15 sections |
| **Expansion potential** | HIGH |
| **Technical debt** | MEDIUM — monolithic JS, CDN dependencies, no a11y, no mobile |
| **Overall value** | **IMPORTANT** — but the CLI can do everything the dashboard does. The dashboard is a convenience, not a requirement. |

### 11. CLI

| Attribute | Assessment |
|---|---|
| **Purpose** | Scriptable commands for init, validation, status, export, worker control |
| **Who uses it** | Headless/Pi deployments, power users, automation scripts |
| **Frequency** | Setup once, `--run-export` frequently |
| **Dependencies** | argparse, all core services |
| **Status** | Implemented — 20+ commands, but barely tested (2 trivial tests) |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | HIGH |
| **Technical debt** | HIGH — virtually untested |
| **Overall value** | **CORE** — CLI is the primary interface for headless deployments |

### 12. Worker

| Attribute | Assessment |
|---|---|
| **Purpose** | Background daemon that drains the queue and advances the scheduler |
| **Who uses it** | System — runs automatically |
| **Frequency** | Continuous (tick every 5s) |
| **Dependencies** | Queue, scheduler, export engine, database |
| **Status** | Implemented — daemon thread with asyncio loop |
| **Maintenance cost** | LOW-MEDIUM |
| **Complexity** | MEDIUM |
| **Expansion potential** | HIGH — multi-worker, health monitoring |
| **Technical debt** | LOW (recently hardened with timeout, graceful shutdown, config caching) |
| **Overall value** | **CORE** — without the worker, nothing gets exported |

### 13. Authentication & Security

| Attribute | Assessment |
|---|---|
| **Purpose** | Single-owner auth: scrypt password, TOTP 2FA, session tokens |
| **Who uses it** | The one owner/operator |
| **Frequency** | Login once per session |
| **Dependencies** | Database, hashlib/hmac (stdlib only) |
| **Status** | Implemented — scrypt, TOTP, session management |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM |
| **Expansion potential** | LOW — single-owner model is intentional |
| **Technical debt** | LOW |
| **Overall value** | **CORE** — required for any network-accessible deployment |

### 14. Configuration System

| Attribute | Assessment |
|---|---|
| **Purpose** | JSON config files validated by Pydantic |
| **Who uses it** | Every user (edit configs) + system (reads configs) |
| **Frequency** | Read on every operation, edited occasionally |
| **Dependencies** | Pydantic, 5 JSON files |
| **Status** | Implemented — atomic writes, cross-reference validation, env secret references |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM |
| **Expansion potential** | MEDIUM |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 15. Database

| Attribute | Assessment |
|---|---|
| **Purpose** | SQLite persistence for history, queue, scheduler, state, events, telemetry |
| **Who uses it** | Every service |
| **Frequency** | Constant |
| **Dependencies** | sqlite3 (stdlib), WAL mode |
| **Status** | Implemented — 7 tables, versioned migrations, typed row mapping |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM |
| **Expansion potential** | LOW — SQLite is the right choice for Pi |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 16. Logging

| Attribute | Assessment |
|---|---|
| **Purpose** | Per-area rotating logs, structured JSON option, colorized console |
| **Who uses it** | Developers and operators debugging issues |
| **Frequency** | Constant (writes), occasional (reads) |
| **Dependencies** | stdlib logging, RotatingFileHandler |
| **Status** | Implemented — 10 area logs + errors.log + console |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **CORE** — essential for debugging |

### 17. Backups

| Attribute | Assessment |
|---|---|
| **Purpose** | ZIP snapshots of config, database, and optionally logs |
| **Who uses it** | Operators before upgrades or migrations |
| **Frequency** | Rarely (manual or scheduled) |
| **Dependencies** | zipfile (stdlib), filesystem |
| **Status** | Implemented — create, list, verify, restore, prune |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | MEDIUM — S3/SFTP backup targets |
| **Technical debt** | LOW (recently fixed: WAL checkpoint before restore) |
| **Overall value** | **IMPORTANT** — not needed for exports to work, but critical for operational safety |

### 18. System Monitoring

| Attribute | Assessment |
|---|---|
| **Purpose** | CPU, RAM, disk, temperature, uptime, Raspberry Pi detection |
| **Who uses it** | Operators checking Pi health |
| **Frequency** | Occasional |
| **Dependencies** | psutil (optional), /proc fallback |
| **Status** | Implemented |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **IMPORTANT** — critical for Pi deployments, but exports work without it |

### 19. Event Bus & Audit Log

| Attribute | Assessment |
|---|---|
| **Purpose** | Publish/subscribe event system; persisted audit trail |
| **Who uses it** | Notifications, WebSocket, audit log, telemetry, future plugins |
| **Frequency** | Every state change |
| **Dependencies** | collections.deque, asyncio, threading |
| **Status** | Implemented — typed events, ring buffer, category/severity filtering |
| **Maintenance cost** | LOW |
| **Complexity** | MEDIUM — thread-safe pub/sub, coroutine scheduling |
| **Expansion potential** | HIGH — plugin hooks, AI assistant substrate |
| **Technical debt** | LOW |
| **Overall value** | **IMPORTANT** — enables notifications + audit, but exports work without it |

### 20. API Pool (Credential Selection)

| Attribute | Assessment |
|---|---|
| **Purpose** | Select least-used, non-rate-limited account; failover; cooldown tracking |
| **Who uses it** | Export engine (every export) |
| **Frequency** | Every export |
| **Dependencies** | Database (state persistence), Onshape accounts |
| **Status** | Implemented — but DUPLICATED in ApiPool + CredentialPool |
| **Maintenance cost** | HIGH — two implementations |
| **Complexity** | HIGH — two selection algorithms |
| **Expansion potential** | LOW — selection logic doesn't need to be complex |
| **Technical debt** | HIGH — dual implementation |
| **Overall value** | **CORE** — essential for multi-account reliability |

### 21. Retry & Backoff

| Attribute | Assessment |
|---|---|
| **Purpose** | Exponential backoff for API calls and queue jobs |
| **Who uses it** | OnshapeClient, QueueManager |
| **Frequency** | On failure |
| **Dependencies** | None (pure logic) |
| **Status** | Implemented — configurable base, max, max_attempts, HTTP statuses |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW — confusing alias (`delay_for_attempt` vs `delay_seconds_for_attempt`) |
| **Overall value** | **CORE** — without retry, transient failures become permanent |

### 22. Export Engine

| Attribute | Assessment |
|---|---|
| **Purpose** | Orchestrate document discovery → account leasing → format export → file organization → history |
| **Who uses it** | Worker, CLI manual export |
| **Frequency** | Every export |
| **Dependencies** | ApiPool, OnshapeClient, FolderManager, Database, export formats |
| **Status** | Implemented — now exports all Part Studios (was only first) |
| **Maintenance cost** | LOW-MEDIUM |
| **Complexity** | MEDIUM |
| **Expansion potential** | MEDIUM |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 23. Onshape API Client

| Attribute | Assessment |
|---|---|
| **Purpose** | Authenticated HTTP client for Onshape REST API |
| **Who uses it** | Export engine |
| **Frequency** | Every export |
| **Dependencies** | requests library, retry policy |
| **Status** | Implemented — STL direct + translation pipeline for STEP/OBJ/IGES |
| **Maintenance cost** | LOW-MEDIUM |
| **Complexity** | MEDIUM — CDN redirects, translation polling, re-authentication |
| **Expansion potential** | LOW |
| **Technical debt** | MEDIUM — fetches ALL documents and filters locally (O(n) issue) |
| **Overall value** | **CORE** |

### 24. Folder Manager

| Attribute | Assessment |
|---|---|
| **Purpose** | Create timestamped, non-overwriting export folders with format subdirectories |
| **Who uses it** | Export engine |
| **Frequency** | Every export |
| **Dependencies** | pathlib, re |
| **Status** | Implemented — safe filenames, unique paths |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **CORE** |

### 25. Rate Limiting (Login + API)

| Attribute | Assessment |
|---|---|
| **Purpose** | Prevent brute-force login and API flooding |
| **Who uses it** | System (automatic enforcement) |
| **Frequency** | Every request |
| **Dependencies** | In-memory dict, time.monotonic |
| **Status** | Implemented — 5/min login, 120/min API |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **IMPORTANT** — exports work without it, but security requires it |

### 26. Remote Access Detection

| Attribute | Assessment |
|---|---|
| **Purpose** | Auto-detect Tailscale, Cloudflare Tunnel, NGINX/Caddy/Traefik, HTTPS |
| **Who uses it** | Operators setting up remote access |
| **Frequency** | Once per deployment |
| **Dependencies** | subprocess, shutil |
| **Status** | Implemented — 15s cached snapshot |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **OPTIONAL** — nice convenience, but exports work without it |

### 27. Telemetry / Metrics

| Attribute | Assessment |
|---|---|
| **Purpose** | Time-series metrics for dashboard charts and analytics |
| **Who uses it** | Dashboard (charts) |
| **Frequency** | Every worker tick |
| **Dependencies** | Database (telemetry table), MetricsService |
| **Status** | Implemented |
| **Maintenance cost** | LOW |
| **Complexity** | LOW-MEDIUM |
| **Expansion potential** | MEDIUM — could power external monitoring |
| **Technical debt** | LOW |
| **Overall value** | **OPTIONAL** — nice for dashboard, but exports work without it |

### 28. Dashboard Charts (Chart.js)

| Attribute | Assessment |
|---|---|
| **Purpose** | Activity line chart, account health doughnut, success gauge, queue bars |
| **Who uses it** | Dashboard viewers |
| **Frequency** | Every dashboard visit |
| **Dependencies** | Chart.js CDN, MetricsService, TelemetryStore |
| **Status** | Implemented |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW — but depends on CDN |
| **Overall value** | **OPTIONAL** — nice visualization, but not essential |

### 29. SSE Streaming

| Attribute | Assessment |
|---|---|
| **Purpose** | Push live summary counts to dashboard every 4 seconds |
| **Who uses it** | Dashboard shell (appShell component) |
| **Frequency** | Continuous while dashboard is open |
| **Dependencies** | FastAPI StreamingResponse, asyncio |
| **Status** | Implemented — with polling fallback |
| **Maintenance cost** | LOW |
| **Complexity** | LOW |
| **Expansion potential** | LOW |
| **Technical debt** | LOW |
| **Overall value** | **OPTIONAL** — polling alone is sufficient |

### 30. WebSocket Events

| Attribute | Assessment |
|---|---|
| **Purpose** | Stream live audit events to the Activity page |
| **Who uses it** | Activity page viewers |
| **Frequency** | While activity page is open |
| **Dependencies** | FastAPI WebSocket, EventBus |
| **Status** | Implemented — with polling fallback every 6s |
| **Complexity** | MEDIUM — connection management, reconnection |
| **Overall value** | **OPTIONAL** — polling alone is sufficient |

### 31. Command Palette (⌘K Search)

| Attribute | Assessment |
|---|---|
| **Purpose** | Global search across accounts, labels, profiles, history, queue |
| **Who uses it** | Power users |
| **Frequency** | Occasionally |
| **Dependencies** | Alpine.js, `/api/search` endpoint |
| **Status** | Implemented |
| **Complexity** | LOW |
| **Overall value** | **OPTIONAL** — nice power-user feature, not essential |

### 32. Dark/Light Theme Toggle

| Attribute | Assessment |
|---|---|
| **Purpose** | Switch between dark and light UI themes |
| **Who uses it** | Users with preference |
| **Frequency** | Once (persisted to localStorage) |
| **Dependencies** | CSS custom properties, Alpine.js |
| **Status** | Implemented |
| **Complexity** | LOW |
| **Overall value** | **OPTIONAL** — nice, but not essential |

### 33. Setup Wizard

| Attribute | Assessment |
|---|---|
| **Purpose** | Guide first-time users through owner creation and storage config |
| **Who uses it** | First-time users (once) |
| **Frequency** | Once per installation |
| **Dependencies** | Alpine.js, wizard.html, 9-step flow |
| **Status** | Implemented |
| **Complexity** | MEDIUM |
| **Overall value** | **IMPORTANT** — reduces friction for new users |

### 34. Bambu Studio Integration

| Attribute | Assessment |
|---|---|
| **Purpose** | Post-process STL exports through Bambu Studio slicer |
| **Who uses it** | 3D printing users |
| **Frequency** | Per export (when enabled) |
| **Dependencies** | Bambu Studio executable, subprocess |
| **Status** | **STUB** — `BambuStudioRunner.create_project()` raises `NotImplementedError` |
| **Complexity** | HIGH (if implemented) |
| **Overall value** | **REMOVE from V1** — stub that does nothing; can return as plugin |

### 35. Plugin System

| Attribute | Assessment |
|---|---|
| **Purpose** | Extensibility protocol for third-party integrations |
| **Who uses it** | No one (not implemented) |
| **Frequency** | Never |
| **Dependencies** | Plugin protocol (defined), no loader/registry/discovery |
| **Status** | **STUB** — `Plugin` protocol exists but nothing uses it |
| **Complexity** | HIGH (if implemented) |
| **Overall value** | **REMOVE from V1** — stub with zero functionality; design extension points, implement later |

### 36. Textual TUI Dependency

| Attribute | Assessment |
|---|---|
| **Purpose** | Terminal UI framework listed in requirements.txt |
| **Who uses it** | No one (not used anywhere in codebase) |
| **Frequency** | Never |
| **Dependencies** | textual>=0.79 in requirements.txt |
| **Status** | **UNUSED** — imported nowhere |
| **Overall value** | **REMOVE** — dead dependency |

### 37. APScheduler Dependency

| Attribute | Assessment |
|---|---|
| **Purpose** | Cron-style scheduling library in requirements.txt |
| **Who uses it** | The custom SchedulerService (not APScheduler itself) |
| **Frequency** | Never (the custom implementation doesn't use it) |
| **Dependencies** | apscheduler>=3.10 in requirements.txt |
| **Status** | **UNUSED** — the app has its own SchedulerService |
| **Overall value** | **REMOVE** — dead dependency; custom scheduler does the job |

### 38. Cryptography Dependency

| Attribute | Assessment |
|---|---|
| **Purpose** | Listed in requirements.txt |
| **Who uses it** | No one — auth uses stdlib hashlib/hmac only |
| **Frequency** | Never |
| **Status** | **UNUSED** — all crypto is stdlib (intentional design choice for Pi) |
| **Overall value** | **REMOVE** — dead dependency |

---

## FEATURE AUDIT: DOES IT SUPPORT THE PRIMARY MISSION?

| # | Feature | Primary mission? | Removed unnoticed? | Real problem? | Well implemented? | Duplicate? | Complicates architecture? | Should be plugin? | V2? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Accounts | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Dual impl | ⚠️ Yes (ApiPool+CredentialPool) | ✅ Yes | No | No |
| 2 | Organizations | ⚠️ Indirectly | ✅ Most users | ❌ For multi-tenant only | ⚠️ Incomplete migration | ⚠️ Duplicates flat accounts | ✅ Yes | ⚠️ Yes | ✅ Yes |
| 3 | Labels | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 4 | Export Profiles | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 5 | Manual Export | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 6 | Queue | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 7 | Scheduler | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 8 | History | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 9 | Notifications | ✅ Yes | ⚠️ Some users | ✅ Yes | ✅ Yes | No | No | ⚠️ Could be | No |
| 10 | Web Dashboard | ⚠️ Indirectly | ⚠️ CLI users wouldn't | ✅ Yes | ⚠️ Monolithic | No | ⚠️ Yes (1,300-line web.py) | No | No |
| 11 | CLI | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Untested | No | No | No | No |
| 12 | Worker | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 13 | Auth | ✅ Yes | ❌ No (networked) | ✅ Yes | ✅ Yes | No | No | No | No |
| 14 | Config | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 15 | Database | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 16 | Logging | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 17 | Backups | ⚠️ Indirectly | ✅ Most users | ✅ Yes | ✅ Yes | No | No | No | No |
| 18 | System Monitor | ❌ No | ✅ Most users | ⚠️ Only on Pi | ✅ Yes | No | No | No | No |
| 19 | Event Bus | ⚠️ Indirectly | ✅ Most users | ✅ Yes (enables notifications) | ✅ Yes | No | No | No | No |
| 20 | API Pool | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Dual impl | ⚠️ Yes | ✅ Yes | No | No |
| 21 | Retry | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 22 | Export Engine | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 23 | Onshape Client | ✅ Yes | ❌ No | ✅ Yes | ⚠️ O(n) filtering | No | No | No | No |
| 24 | Folder Manager | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | No | No | No | No |
| 25 | Rate Limiting | ⚠️ Indirectly | ✅ Most users | ✅ Yes | ✅ Yes | No | No | No | No |
| 26 | Remote Access | ❌ No | ✅ Most users | ❌ Not really | ✅ Yes | No | No | ✅ Yes | ✅ Yes |
| 27 | Telemetry | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | ✅ Yes | ✅ Yes |
| 28 | Charts | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | No | No |
| 29 | SSE Streaming | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | No | No |
| 30 | WebSocket | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | No | No |
| 31 | ⌘K Search | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | No | No |
| 32 | Theme Toggle | ❌ No | ✅ Most users | ❌ No | ✅ Yes | No | No | No | No |
| 33 | Setup Wizard | ⚠️ Indirectly | ⚠️ CLI users wouldn't | ✅ Yes | ✅ Yes | No | No | No | No |
| 34 | Bambu Studio | ❌ No | ✅ Everyone (it's a stub) | ❌ No | ❌ Stub | No | No | ✅ Yes | ✅ Yes |
| 35 | Plugin System | ❌ No | ✅ Everyone (it's a stub) | ❌ No | ❌ Stub | No | No | N/A | ✅ Yes |
| 36 | Textual TUI | ❌ No | ✅ Everyone (unused) | ❌ No | ❌ Unused dep | No | No | N/A | ❌ Remove |
| 37 | APScheduler | ❌ No | ✅ Everyone (unused) | ❌ No | ❌ Unused dep | No | No | N/A | ❌ Remove |
| 38 | Cryptography | ❌ No | ✅ Everyone (unused) | ❌ No | ❌ Unused dep | No | No | N/A | ❌ Remove |

---

## FEATURE CLASSIFICATION

### CATEGORY A: CORE *(Required for V1.0)*

Without these, the application fails its primary mission.

| # | Feature | Rationale |
|---|---|---|
| 1 | **Onshape Accounts** (flat model only) | Must connect to Onshape |
| 3 | **Labels** | Must know WHAT to export |
| 4 | **Export Profiles** | Must know HOW to export |
| 5 | **Manual Export** | The primary user action |
| 6 | **Queue** | All exports flow through it |
| 7 | **Scheduler** | Automation is the value prop |
| 8 | **Export History** | Must track what happened |
| 9 | **Notifications** | Must alert on failures (unattended operation) |
| 11 | **CLI** | Primary interface for headless/Pi |
| 12 | **Worker** | The engine that runs exports |
| 13 | **Authentication** | Required for network access |
| 14 | **Configuration** | Everything is configurable |
| 15 | **Database** | Persistence for all state |
| 16 | **Logging** | Essential for debugging |
| 20 | **API Pool** (single implementation) | Multi-account reliability |
| 21 | **Retry & Backoff** | Resilience against transient failures |
| 22 | **Export Engine** | Orchestrates the export pipeline |
| 23 | **Onshape API Client** | Talks to Onshape |
| 24 | **Folder Manager** | Organizes exported files |

**19 features — the minimum viable product.**

### CATEGORY B: IMPORTANT *(Should remain, can follow core)*

Adds significant value without bloating the core.

| # | Feature | Rationale |
|---|---|---|
| 10 | **Web Dashboard** | Convenient monitoring, but CLI works without it |
| 17 | **Backups** | Operational safety, not needed for exports |
| 18 | **System Monitoring** | Critical for Pi, not needed for exports |
| 19 | **Event Bus & Audit** | Enables notifications + future plugins |
| 25 | **Rate Limiting** | Security, not export functionality |
| 33 | **Setup Wizard** | Reduces first-run friction |

**6 features — keep, but don't let them drive architecture.**

### CATEGORY C: OPTIONAL *(Should not block V1, may become plugins)*

Useful but not essential. Good candidates for plugins or future milestones.

| # | Feature | Rationale |
|---|---|---|
| 2 | **Organization Model** | Overengineered for V1; flat accounts suffice |
| 26 | **Remote Access Detection** | Convenience; can be a plugin |
| 27 | **Telemetry / Metrics** | Nice dashboard feature; not core |
| 28 | **Dashboard Charts** | Visual polish; not essential |
| 29 | **SSE Streaming** | Polling works fine |
| 30 | **WebSocket Events** | Polling works fine |
| 31 | **⌘K Command Palette** | Power-user convenience |
| 32 | **Dark/Light Theme** | Visual preference |

**8 features — defer or make optional.**

### CATEGORY D: REMOVE *(Cut from codebase)*

Provides little value, duplicates functionality, or is an unimplemented stub.

| # | Feature | Rationale | Action |
|---|---|---|---|
| 34 | **Bambu Studio Integration** | Stub that raises `NotImplementedError`. Exists only in config and a 20-line stub class. | Remove stub. Design as future plugin. Remove Bambu config from default profiles. |
| 35 | **Plugin System** | `Plugin` protocol with no loader, registry, or consumers. Zero functionality. | Remove stub. Design clean extension points for V2. |
| 36 | **Textual TUI** | Listed in requirements.txt, never imported. Dead dependency. | Remove from requirements.txt. |
| 37 | **APScheduler** | Listed in requirements.txt. App has its own `SchedulerService`. Dead dependency. | Remove from requirements.txt. |
| 38 | **Cryptography** | Listed in requirements.txt. All crypto is stdlib (scrypt, HMAC). Dead dependency. | Remove from requirements.txt. |
| — | **Organizations dual model** | `ApiPool` + `CredentialPool` are near-duplicates. Double maintenance for same functionality. | Merge into single `CredentialProvider`. Keep flat model only for V1. Defer hierarchical orgs to V2 plugin. |

**6 items to cut — 3 dead dependencies, 2 non-functional stubs, 1 architectural simplification.**

---

## SIMPLIFICATION PLAN

### Merge

| Current | Proposed | Why |
|---|---|---|
| `ApiPool` + `CredentialPool` | Single `CredentialProvider` | Same job, two implementations = double bugs |
| `accounts.json` + `organizations.json` | Single `accounts.json` (flat) | Organizations are overengineered for V1 |
| 15 dashboard pages | 5 consolidated pages (Dashboard, Exports, Config, System, Logs) | Reduce navigation complexity |
| SSE + polling for summary | Polling only | SSE adds complexity for no user-visible benefit |
| WebSocket + polling for events | Polling only | Same reason |

### Remove

| Item | Why |
|---|---|
| `bambu.py` | Stub that does nothing |
| `plugins.py` | Protocol with no implementation |
| `textual` dep | Never imported |
| `apscheduler` dep | Custom scheduler used instead |
| `cryptography` dep | All crypto is stdlib |
| Bambu config from default profiles | References non-existent functionality |
| Plugin nav item from sidebar | Links to empty page |
| ⌘K command palette | Unnecessary complexity for V1 |
| Theme toggle | Default dark theme is sufficient |

### Simplify

| Current | Proposed |
|---|---|
| `AccountRuntimeState` (mutable, per-account) | Simple counters on `OnshapeAccount` dataclass |
| `CredentialState` (EMA latency, rolling counters) | Same simple counters |
| 9 default export profiles | 5 (STL, STEP, OBJ, Multi Format, CAD Bundle) |
| Per-area log files (10 files) | 3 files (app.log, export.log, errors.log) |
| `config.json` with 50+ keys | Trim to essential keys only |

---

## EXTENSION POINTS *(Design now, implement in V2)*

These interfaces should exist as clean contracts, not partially-built features:

| Extension Point | Contract | V2 Use |
|---|---|---|
| **Notification Provider** | `send(event: Event) -> bool` | Discord, Slack, Teams, Email, Webhook (already built — just formalize) |
| **Export Provider** | `export(doc, format, options) -> Path` | Bambu Studio, PrusaSlicer, custom post-processors |
| **Storage Provider** | `store(path: Path) -> str` | S3, SFTP, NAS, Google Drive |
| **Plugin** | `activate(app) / deactivate(app)` | Third-party integrations |
| **Event Hook** | `on_event(event_type, callback)` | Already exists as EventBus — just document it |

---

## DEAD CODE & DEPENDENCIES TO REMOVE NOW

```bash
# Remove from requirements.txt:
textual>=0.79        # Never imported
apscheduler>=3.10    # Custom scheduler used instead
cryptography>=42.0   # All crypto is stdlib

# Remove from codebase:
onshape_export_manager/core/bambu.py         # Stub
onshape_export_manager/core/plugins.py       # Stub (keep protocol design in docs)

# Remove from templates:
ui/templates/base.html — command palette HTML  # ~30 lines
ui/templates/base.html — theme toggle (keep dark mode only)

# Remove from config defaults:
config/export_profiles.json — Bambu STL profile
config/config.json — bambu section
```
