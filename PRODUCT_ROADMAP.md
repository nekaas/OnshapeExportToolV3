# Product Roadmap

> **Version 1.0 definition**: A small, reliable, intuitive Onshape export automation tool that runs on a Raspberry Pi.
> Everything outside V1.0 is explicitly documented as future work — not partially implemented.

---

## Guiding Principles

1. **Core workflow first** — Accounts → Labels → Profiles → Export → Schedule → History → Notify
2. **CLI is the primary interface** — the web dashboard is a convenience, not a requirement
3. **Raspberry Pi is the target platform** — every decision considers 1GB RAM and SD card I/O
4. **No stubs** — nothing in V1.0 says "coming soon" or raises `NotImplementedError`
5. **Clean extension points** — design contracts for V2, but don't build half-implementations

---

## MILESTONE 1: MINIMUM VIABLE PRODUCT *(V0.1 → V1.0)*

### Goal
A reliable tool that exports labelled Onshape documents to files on disk, on a schedule, with failure notifications.

### Features Included

| Feature | Status | Notes |
|---|---|---|
| Flat account management (accounts.json) | ✅ Done | Single model — no organizations |
| Label management (labels.json) | ✅ Done | |
| Export profiles (export_profiles.json) | ✅ Done | 5 profiles: STL, STEP, OBJ, Multi Format, CAD Bundle |
| Manual export (CLI + API) | ✅ Done | |
| Queue with retry | ✅ Done | State machine, atomic claims, exponential backoff |
| Scheduler | ✅ Done | 15min/30min/hourly/daily/weekly/monthly intervals |
| Export history with filtering | ✅ Done | |
| Notifications (Discord, Slack, Teams, Email, Webhook) | ✅ Done | |
| CLI (all commands tested) | ⚠️ Needs tests | Core functionality works, tests missing |
| Worker (background daemon) | ✅ Done | With timeout enforcement, graceful shutdown |
| Authentication (scrypt + TOTP) | ✅ Done | |
| Configuration (Pydantic-validated JSON) | ✅ Done | |
| Database (SQLite WAL, versioned migrations) | ✅ Done | |
| Logging (rotating files, structured option) | ✅ Done | |
| Web dashboard (monitoring only) | ✅ Done | Read-only views of accounts, labels, queue, history |
| API pool (credential selection + failover) | ✅ Done | Single implementation |
| Retry with exponential backoff | ✅ Done | |
| Rate limiting (login + API) | ✅ Done | |

### Features Intentionally Excluded

| Feature | Why Excluded | Future |
|---|---|---|
| Organization model (organizations.json) | Overengineered for V1; flat accounts suffice | V2 plugin |
| Bambu Studio integration | Non-functional stub; not core to export pipeline | V2 export provider |
| Plugin loader/registry | No consumers exist; design extension points instead | V2 |
| Dashboard charts (Chart.js) | Visual polish; CLI shows same data as text | V3 |
| SSE streaming | Polling works fine; SSE adds complexity | V3 |
| WebSocket events | Polling works fine | V3 |
| Command palette (⌘K) | Power-user feature; not essential | V3 |
| Theme toggle | Default dark theme is sufficient | V3 |
| Remote access detection | Convenience; docs cover setup | V3 |
| Telemetry | Not needed for V1 | V3 (opt-in) |
| Multi-worker support | Single worker handles typical Pi workload | V2 |
| Per-format option schemas | `dict[str, Any]` is flexible enough for V1 | V2 |
| Mobile-responsive UI | Desktop-only is fine for a server application | V3 |

### Features to Remove Before V1.0

| Item | Action |
|---|---|
| `bambu.py` | Delete stub file |
| `plugins.py` | Delete stub file |
| `textual` from requirements.txt | Remove unused dependency |
| `apscheduler` from requirements.txt | Remove unused dependency |
| `cryptography` from requirements.txt | Remove unused dependency |
| Bambu config section from `config.json` defaults | Remove |
| "Bambu STL" from default export profiles | Remove |
| "Plugins" nav item from dashboard sidebar | Remove |
| HTMX CDN script tag | Already removed ✅ |
| `CredentialPool` in organizations.py | Merge into single ApiPool |

### Dependencies

- Python 3.12+
- requests, fastapi, uvicorn, jinja2, pydantic, python-multipart, psutil
- pytest, pytest-asyncio, httpx (dev only)

### Risks

| Risk | Mitigation |
|---|---|
| Onshape API changes break exports | Smoke tests + version pinning |
| SQLite corruption on SD card | WAL mode + backup/restore |
| Single-worker bottleneck | Acceptable for Pi; document as known limit |
| CLI untested | Must complete CLI tests before V1.0 |

### V1.0 Definition of Done

- [ ] All Category A features implemented and tested
- [ ] All Category D features removed
- [ ] CLI test coverage ≥80%
- [ ] Full integration test: init → configure → export → verify files
- [ ] Documentation: README accurate for V1.0 features only
- [ ] Dead dependencies removed from requirements.txt
- [ ] No `NotImplementedError` stubs anywhere
- [ ] Single credential management implementation

---

## MILESTONE 2: PRODUCTION READY *(V1.0 → V1.1)*

### Goal
Harden the application for months of unattended operation on Raspberry Pi.

### Features Added

| Feature | Rationale |
|---|---|
| CLI integration tests (all 20+ commands) | Primary interface must be reliable |
| Concurrency tests | Prove thread-safety fixes work |
| End-to-end test | Catch integration bugs |
| Database migration tests (v1→v2→v3) | Prevent upgrade data loss |
| Server-side document filtering (Onshape API) | Performance for large document sets |
| Multi-worker support | Parallel exports when API quota allows |
| Worker health monitoring (heartbeat + auto-restart) | Detect and recover from stalls |
| Stuck job detection + forced cancellation | Prevent hung exports from blocking queue |
| Docker containerization (amd64 + arm64) | One-command deployment |
| Cross-platform CI (macOS, Ubuntu, Pi OS) | Catch platform-specific bugs |
| Backup automation (scheduled + retention) | Operational safety |

### Features Still Excluded

- Organizations model
- Plugin system implementation
- Frontend build system
- Mobile UI
- Real-time streaming (SSE/WebSocket)
- Charts and visualizations
- Bambu Studio

---

## MILESTONE 3: POWER USER FEATURES *(V1.1 → V2.0)*

### Goal
Add features that make daily use significantly more productive.

### Features Added

| Feature | Rationale |
|---|---|
| Per-format export option schemas (Pydantic) | Prevent invalid export configs at save time |
| Label group exports (multiple labels per job) | Common workflow optimization |
| Export retention policies (auto-delete old files) | Prevent SD card exhaustion |
| Batch queue operations (multi-select, cancel all) | Queue management at scale |
| Duplicate detection via content hashing | Save API quota on unchanged docs |
| Export archive download (ZIP from UI) | Convenient file retrieval |
| Standardized API response envelope | Consistent frontend + external tooling |
| Database query pagination (cursor-based) | Browse full history |
| Config hot-reload (`watchdog`-based) | No-restart config changes |
| Keyboard shortcuts catalog | Power-user efficiency |
| Bulk import/export of settings | Migration between instances |
| Unified credential management (single provider) | Remove the last dual-model traces |

### Extension Points Defined (but not built)

- Notification provider interface (formalize existing senders)
- Export provider interface (for Bambu, PrusaSlicer, etc.)
- Storage provider interface (for S3, SFTP, NAS)
- Plugin protocol (activate/deactivate/register hooks)

---

## MILESTONE 4: ENTERPRISE FEATURES *(V2.0 → V2.1)*

### Goal
Support multi-team, multi-account deployments.

### Features Added

| Feature | Rationale |
|---|---|
| Organization model (hierarchical credentials) | Multi-team credential management |
| Role-based access (admin/operator/viewer) | Team deployments |
| Anonymous telemetry (opt-in) | Understand usage patterns |
| Audit log retention policies | Compliance |
| Export verification (checksums, file integrity) | Regulated industries |

---

## MILESTONE 5: PLUGIN ECOSYSTEM *(V2.1 → V3.0)*

### Goal
Enable community contributions without modifying core code.

### Features Added

| Feature | Rationale |
|---|---|
| Plugin loader + registry | Filesystem discovery, lifecycle management |
| Plugin marketplace (directory listing) | Discoverability |
| Bambu Studio plugin (reference implementation) | Prove the plugin system works |
| Storage provider plugins (S3, SFTP, NAS) | Community-contributed backends |
| Notification provider plugins | Custom notification channels |
| Frontend build system (ES modules, bundling) | Enables plugin UI injection |
| Accessibility (WCAG 2.1 AA) | Broader user base |
| Mobile-responsive UI | Phone/tablet monitoring |
| Real-time streaming (SSE + WebSocket) | Live dashboard updates |
| Dashboard widget customization | Personalized views |
| Dark/light theme + custom accents | Personalization |
| Guided onboarding tour | New user experience |

---

## V1.0 SCOPE BOUNDARY

```
┌─────────────────────────────────────────────────────┐
│                    V1.0 SCOPE                        │
│                                                      │
│  accounts.json ─→ labels.json ─→ profiles.json       │
│        │               │               │              │
│        ▼               ▼               ▼              │
│  ┌─────────────────────────────────────────┐        │
│  │           EXPORT PIPELINE                │        │
│  │  CLI ─→ Queue ─→ Worker ─→ Export Engine │        │
│  │          │         │           │          │        │
│  │          ▼         ▼           ▼          │        │
│  │      Retry    Scheduler   Onshape API    │        │
│  │          │         │           │          │        │
│  │          ▼         ▼           ▼          │        │
│  │      History   Notifications   Files     │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  + Web Dashboard (read-only monitoring)              │
│  + Auth (single owner)                               │
│  + Backups                                           │
│  + Logging                                           │
│  + Rate Limiting                                     │
│                                                      │
│  ─── V1.0 boundary ───                              │
│                                                      │
│  EXCLUDED: Orgs, Plugins, Bambu, Charts,             │
│  SSE, WebSocket, ⌘K, Themes, Mobile,                 │
│  Multi-worker, Telemetry                             │
└─────────────────────────────────────────────────────┘
```

---

## CLEANUP CHECKLIST FOR V1.0

### Remove these files
- [ ] `onshape_export_manager/core/bambu.py`
- [ ] `onshape_export_manager/core/plugins.py`

### Remove from requirements.txt
- [ ] `textual>=0.79`
- [ ] `apscheduler>=3.10`
- [ ] `cryptography>=42.0`

### Remove from config defaults
- [ ] `bambu` section in `config.json` defaults
- [ ] "Bambu STL" profile from `export_profiles.json` defaults

### Remove from UI
- [ ] "Plugins" from NAV_ITEMS in web.py
- [ ] HTMX script tag in base.html ✅ (already done)
- [ ] Command palette HTML from base.html
- [ ] Theme toggle JavaScript from app.js

### Simplify
- [ ] Merge `ApiPool` + `CredentialPool` into single `CredentialProvider`
- [ ] Remove `organizations.json` support (flat accounts only for V1)
- [ ] Consolidate per-area logs (10 files → 3: app, export, errors)

---

*V1.0 is small, reliable, intuitive, fast, easy to maintain, and internally consistent. Everything outside this boundary is explicitly documented for future milestones — not partially built.*
