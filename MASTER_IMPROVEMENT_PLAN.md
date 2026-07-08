# Remaining Roadmap — Hardest First

> **58 items remain from the original 78. 20 already completed.**
> Ordered by implementation difficulty: hardest architectural changes first, quick wins last.

---

## STATUS KEY

| Mark | Meaning |
|---|---|
| ✅ **DONE** | Implemented and tested (165 tests pass) |
| ⬜ **TODO** | Not yet started |

---

## PHASE A: ARCHITECTURAL REFACTORS *(Hardest — weeks each)*

> These touch the entire codebase. Each one changes how developers think about the system.
> They must come first because later work depends on clean architecture.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 9 | Hard | 16h | **Unify ApiPool & CredentialPool** — Merge two near-duplicate credential management subsystems into one `CredentialProvider` interface with `FlatCredentialProvider` and `OrganizationCredentialProvider` backends |
| ⬜ 10 | Hard | 12h | **Dependency Injection Container** — Replace manual `Application` service locator with constructor injection; single `bootstrap()` wiring function with explicit ordering |
| ⬜ 11 | Hard | 12h | **Extract Route Modules from web.py** — Split 1,300+ line monolith into `routes/labels.py`, `routes/queue.py`, `routes/organizations.py`, etc. via FastAPI `APIRouter` |
| ⬜ 34 | Hard | 20h | **Plugin Loader & Registry** — Filesystem discovery via `importlib`, lifecycle hooks (`activate`/`deactivate`), EventBus registration, API route injection, UI injection |
| ⬜ 33 | Hard | 16h | **Bambu Studio Integration** — Complete the stub class; `subprocess` invocation, project file templates, auto-arrange, G-code/3MF output, error handling for missing executable |
| ⬜ 17 | Hard | 10h | **Bundled ES Modules with Build Step** — Replace CDN Alpine.js/Chart.js/Flatpickr with Vite/esbuild bundle; content-hash filenames, tree-shaking, minification |

**Why Phase A first?** Every later phase assumes clean, decoupled code. Without unified credentials, every account feature is built twice. Without DI, testing and extending services is fragile. Without modular routes, web.py grows unbounded. Without a build step, frontend work in later phases is constrained by CDN limitations.

---

## PHASE B: CORE ARCHITECTURE HARDENING *(Medium-Hard — days each)*

> Fix deep structural issues before extending functionality. Proves Phase A fixes work under load.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 41 | Medium | 8h | **Multi-Worker Support** — Spawn `worker_count` threads; atomic queue distribution via ✅ Item 1; shared ApiPool with ✅ Item 2 locking |
| ⬜ 18 | Medium | 10h | **Modularize app.js** — Split 1,500-line monolith into `services/api.js`, `components/toast.js`, `components/modal.js`, `pages/manual-export.js` |
| ⬜ 25 | Medium | 8h | **Complete Organizations Migration** — Auto-migrate `accounts.json` on startup; deprecation warning; remove old `ApiPool` code path after grace period |
| ⬜ 56 | Hard | 8h | **Server-Side Document Filtering** — Push label/date filtering to Onshape API instead of client-side fetch-all; revisit unreliable `?label=` parameter |
| ⬜ 72 | Medium | 8h | **Docker Containerization** — Multi-arch `Dockerfile` (amd64 + arm64), `docker-compose.yml` with persistent volumes, publish to GitHub Container Registry |
| ⬜ 65 | Hard | 12h | **Concurrency Tests** — Multi-worker queue contention, pool leasing races, WebSocket events during worker activity, rapid start/stop cycles |
| ⬜ 70 | Hard | 8h | **End-to-End Test** — Full workflow: `--init` → web start → create org/credential/label/profile → manual export → verify files on disk with fake Onshape client |
| ⬜ 5 | Medium | 8h | **Config Hot-Reload** — `watchdog`-based file monitoring on `config/` directory; re-validate on change; emit `CONFIG_UPDATED` events for subscribers |

**Why Phase B before feature work?** Multi-worker and server-side filtering are prerequisites for production deployment. Modular frontend enables Phase D's UX work. Concurrency tests prove Phase A fixes work under load. Hot-reload eliminates a common support issue.

---

## PHASE C: DOMAIN MODEL CLEANUP *(Medium — hours to days)*

> Fix inconsistencies in the core data model before new features are built on top.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 12 | Medium | 8h | **Standardized API Response Envelope** — Wrap all responses in `{"data": ..., "meta": {"page": 1, "total": N}, "error": null}`; coordinate frontend + backend |
| ⬜ 28 | Medium | 6h | **Per-Format Export Option Schemas** — Replace `dict[str, Any]` with strict Pydantic models: `StlOptions(mode, resolution, units)`, `StepOptions(...)`, etc. |
| ⬜ 31 | Medium | 6h | **Normalize Datetime Handling** — UTC-aware everywhere; single `utc_now()` source; `parse_dt()` always returns UTC-aware; add lint rule for naive datetimes |
| ⬜ 19 | Medium | 12h | **Extract Reusable UI Components** — `toastContainer`, `modalDialog` (with focus trapping), `dataTable` (sortable/filterable), `formField` (with validation), `chartWidget`, `confirmButton` |
| ⬜ 20 | Medium | 16h | **Accessibility Audit & Remediation** — WCAG 2.1 AA: ARIA labels on all interactive elements, `role` attributes, keyboard handlers, `aria-live` regions, contrast ratios ≥4.5:1, skip-to-content link |
| ⬜ 35 | Medium | 6h | **Label Group Exports** — Accept array of label names in `POST /api/exports/run`; process sequentially per job; per-label progress reporting |
| ⬜ 36 | Medium | 3h | **Export Retention Policies** — `retention_days` config; periodic scan of exports directory; delete folders older than threshold; audit-log deletions; default: 0 (disabled) |
| ⬜ 42 | Medium | 6h | **Worker Health Monitoring** — Heartbeat timestamps in `application_state`; watchdog thread checks every 30s; stall detection (2× tick interval + grace); auto-restart with alerting |
| ⬜ 47 | Medium | 4h | **Stuck Job Detection** — Track `started_at`; watchdog force-marks RUNNING jobs past `max_job_duration` as FAILED; restart stuck worker thread |
| ⬜ 59 | Medium | 4h | **SQLite Connection Reuse** — Shared read connection instead of per-call `connect()`; WAL mode concurrent reads; context manager preserved for writes |

**Why Phase C now?** The domain model must be correct before Phase D adds user-facing features. Export option schemas prevent runtime errors. Consistent datetimes prevent subtle timezone bugs. Accessibility is a requirement, not optional.

---

## PHASE D: USER-FACING FEATURES & UX *(Medium — hours to days)*

> The features users see and care about. Built on the clean foundation from A–C.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 51 | Medium | 6h | **Real-Time Per-File Export Progress** — Emit `EXPORT_FILE_STARTED`/`EXPORT_FILE_COMPLETED` events on EventBus; stream via WebSocket; progress bar with file-by-file status in UI |
| ⬜ 53 | Medium | 8h | **Undo for Destructive Actions** — Toast-based undo with 10s window for label/profile/channel deletion; soft-delete pattern; background cleanup of expired soft-deletes |
| ⬜ 50 | Medium | 8h | **Dashboard Widget Customization** — Drag-to-reorder in edit mode; show/hide toggle per widget; persist layout to `localStorage`; default layout unchanged |
| ⬜ 54 | Medium | 10h | **Guided Onboarding Tour** — Replace bare 9-step wizard with interactive tour: welcome screen, explanations with diagrams, progress indicator, "Skip for now" where defaults exist |
| ⬜ 55 | Medium | 8h | **Mobile-Responsive Layout** — Collapse sidebar to hamburger at <768px; horizontal scroll indicators on tables; single-column dashboard; 44px minimum touch targets |
| ⬜ 61 | Medium | 6h | **Database Query Pagination** — Cursor-based for history, events, queue; `next_cursor` + `has_more` in response `meta`; "Load More" in frontend |
| ⬜ 62 | Medium | 8h | **Lazy-Load Dashboard Sections** — Split `/api/metrics` into per-section endpoints; Intersection Observer triggers loading as sections scroll into view |
| ⬜ 22 | Medium | 8h | **Standardize Page States** — Skeleton loaders, illustrated empty states with CTAs, error cards with retry + details toggle, offline banner when SSE drops |

**Why Phase D after domain cleanup?** Users don't care about architecture — they care about progress bars, undo, and mobile support. These features make the application feel production-quality. They need the stable API from Phase C.

---

## PHASE E: PERFORMANCE OPTIMIZATION *(Easy-Medium — hours)*

> Optimize after the feature set stabilizes. Don't tune code that might be rewritten.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 24 | Medium | 4h | **Service Worker for Offline Shell** — Pre-cache static assets on install; cache-first strategy; offline fallback page; background cache updates |
| ⬜ 38 | Medium | 5h | **Batch Queue Operations** — Checkbox multi-select; "Cancel Selected", "Retry All Failed", "Delete Selected" toolbar; "Cancel All Pending" quick action |
| ⬜ 40 | Medium | 5h | **Duplicate Detection via Content Hashing** — SHA-256 hash exported files; store in history; check `modifiedAt` before re-export; skip unchanged documents (configurable) |
| ⬜ 44 | Medium | 4h | **Per-Worker Metrics** — `worker_id` on history entries + telemetry; per-worker throughput, error rate, avg duration, utilization; exposed via `/api/worker` |
| ⬜ 60 | Easy | 3h | **Frontend Asset Minification & Caching** — Content-hash filenames (`app.a1b2c3d.js`); `Cache-Control: public, max-age=31536000, immutable`; Gzip middleware |
| ⬜ 21 | Easy | 6h | **Client-Side Form Validation** — Real-time validation on blur; inline error messages per field; disable submit until valid; mirror server-side rules |

**Why Phase E last among feature work?** Performance optimizations on code that changes in Phase D are wasted effort. Only optimize after UX is stable.

---

## PHASE F: TESTING & QUALITY *(Easy-Medium — hours to days)*

> Test after interfaces stabilize. Tests written too early break during refactoring.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 63 | Medium | 12h | **Full CLI Integration Tests** — Test all 20+ commands via `subprocess.run()` in `tempfile.TemporaryDirectory`; verify filesystem and database state after each |
| ⬜ 67 | Medium | 16h | **pytest Fixtures & Parametrize Migration** — `conftest.py` with shared fixtures; `@pytest.mark.parametrize` for format/enum loops; progressive migration (old + new coexist) |
| ⬜ 64 | Medium | 4h | **SSE Streaming Endpoint Tests** — `httpx.stream("GET", "/api/stream")`; assert `data: {...}\n\n` format; test reconnection via `Last-Event-Id`; test config-change triggers |
| ⬜ 69 | Medium | 6h | **Property-Based Testing** — `hypothesis` strategies for retry backoff, scheduler interval parsing, format name parsing; catch edge cases automatically |
| ⬜ 73 | Medium | 6h | **Database Migration Integration Tests** — Fixture databases at v1/v2/v3 with realistic data; test v1→v2→v3 migration preserves data and adds correct schema |
| ⬜ 66 | Medium | 6h | **Real Onshape API Smoke Tests** — `@pytest.mark.integration` gated behind `ONSHAPE_ACCESS_KEY` env var; verify auth, document listing, STL/STEP export |
| ⬜ 75 | Medium | 4h | **Cross-Platform CI Matrix** — Test on `ubuntu-latest`, `macos-latest`, and Raspberry Pi OS via `arm64v8/python:3.12-slim` Docker emulation in GitHub Actions |

**Why Phase F after features?** Tests validate behavior. Writing tests before behavior is stable means rewriting tests alongside code. Interfaces settle in Phases A–E.

---

## PHASE G: QUICK WINS *(Easy — hours or less)*

> Independent, well-contained, low-risk. Can be done anytime. Great for new contributors.

| # | Difficulty | Effort | Item |
|---|---|---|---|
| ⬜ 29 | Easy | 3h | **Label Reference Integrity** — Check all labels before deleting account/profile; reject with list of referencing labels; offer to update references |
| ⬜ 32 | Easy | 4h | **Standardize ID Generation** — Single `generate_id()` → `uuid4().hex`; update all `str(uuid4())` and manual ID sites; consistent 32-char hex format |
| ⬜ 37 | Easy | 4h | **Export Archive Download** — Stream ZIP of export folder from history/queue page; configurable size limit; progress indicator for large archives |
| ⬜ 39 | Easy | 4h | **Export Job Chaining** — Optional `chain_to` field in request; enqueue chained job on parent success; depth-limited to prevent infinite loops |
| ⬜ 48 | Easy | 6h | **Keyboard Shortcuts Catalog** — `?` modal showing all shortcuts; `g d`/`g q`/`g h` navigation; `n l`/`n p` creation; customizable in `config.json` |
| ⬜ 49 | Easy | 5h | **Custom Theme Accent Colors** — 5-color palette (blue/green/purple/orange/red); CSS custom property generation; high-contrast mode toggle; persist to `localStorage` |
| ⬜ 52 | Easy | 5h | **Bulk Import/Export of Settings** — `GET /api/settings/export` → portable JSON; `POST /api/settings/import` with diff preview + confirmation; CLI `--export-settings`/`--import-settings` |
| ⬜ 23 | Easy | 3h | **Replace Flatpickr CDN** — Bundle Flatpickr as npm dependency (or evaluate native `<input type="date">`); remove one CDN dependency |
| ⬜ 74 | Medium | 8h | **Anonymous Telemetry Opt-In** — Explicit opt-in during setup wizard; send: version, OS, feature counts, error rates; NEVER: API keys, filenames, IPs, PII; respect `DO_NOT_TRACK` |
| ⬜ 77 | Easy | 4h | **Semantic Versioning & Automated Changelog** — Conventional Commits; `commitizen` for validation + bump; `CHANGELOG.md` auto-generated; GitHub Release workflow |

**Why Phase G last?** These are independent, well-understood items. They don't affect architecture, don't block other work, and are perfect for filling gaps between larger efforts.

---

## COMPLETE STATUS BY ORIGINAL PHASE

### Phase 1: Critical Architectural Fixes (7/8)
| # | Status | Item |
|---|---|---|
| 1 | ✅ | Atomic Queue Claim |
| 2 | ✅ | Thread-Safe ApiPool |
| 3 | ✅ | Thread-Safe CredentialPool |
| 4 | ✅ | Scheduler Re-Sync on Config Changes |
| 5 | ⬜ | Config Hot-Reload |
| 6 | ✅ | Database File Locking During Backup Restore |
| 7 | ✅ | Login Brute-Force Rate Limiting |
| 8 | ✅ | API-Wide Request Rate Limiting |

### Phase 2: Backend Redesign (4/8)
| # | Status | Item |
|---|---|---|
| 9 | ⬜ | Unify ApiPool & CredentialPool |
| 10 | ⬜ | Dependency Injection Container |
| 11 | ⬜ | Extract Route Modules from web.py |
| 12 | ⬜ | Standardized API Response Envelope |
| 13 | ✅ | Centralized Exception-to-HTTP Mapping |
| 14 | ✅ | Pydantic Validation Layer |
| 15 | ✅ | API Versioning Headers |
| 16 | ✅ | Remove Dead HTMX Dependency |

### Phase 3: Frontend Redesign (0/8)
| # | Status | Item |
|---|---|---|
| 17 | ⬜ | Bundled ES Modules with Build Step |
| 18 | ⬜ | Modularize app.js |
| 19 | ⬜ | Extract Reusable UI Components |
| 20 | ⬜ | Accessibility Audit & Remediation |
| 21 | ⬜ | Client-Side Form Validation |
| 22 | ⬜ | Standardize Page States |
| 23 | ⬜ | Replace Flatpickr CDN |
| 24 | ⬜ | Service Worker for Offline Shell |

### Phase 4: Domain Cleanup (3/8)
| # | Status | Item |
|---|---|---|
| 25 | ⬜ | Complete Organizations Migration |
| 26 | ✅ | Multi-Part-Studio Support |
| 27 | ✅ | Document Name Collision Prevention |
| 28 | ⬜ | Per-Format Export Option Schemas |
| 29 | ⬜ | Label Reference Integrity |
| 30 | ✅ | JobStatus State Machine |
| 31 | ⬜ | Normalize Datetime Handling |
| 32 | ⬜ | Standardize ID Generation |

### Phase 5: Core Functionality (0/8)
| # | Status | Item |
|---|---|---|
| 33 | ⬜ | Bambu Studio Integration |
| 34 | ⬜ | Plugin Loader & Registry |
| 35 | ⬜ | Label Group Exports |
| 36 | ⬜ | Export Retention Policies |
| 37 | ⬜ | Export Archive Download |
| 38 | ⬜ | Batch Queue Operations |
| 39 | ⬜ | Export Job Chaining |
| 40 | ⬜ | Duplicate Detection via Content Hashing |

### Phase 6: Worker Improvements (3/7)
| # | Status | Item |
|---|---|---|
| 41 | ⬜ | Multi-Worker Support |
| 42 | ⬜ | Worker Health Monitoring |
| 43 | ✅ | Graceful Worker Shutdown |
| 44 | ⬜ | Per-Worker Metrics |
| 45 | ✅ | Per-Export Timeout Enforcement |
| 46 | ✅ | Worker Pool Auto-Sizing |
| 47 | ⬜ | Stuck Job Detection |

### Phase 7: User Experience (0/8)
| # | Status | Item |
|---|---|---|
| 48 | ⬜ | Keyboard Shortcuts Catalog |
| 49 | ⬜ | Custom Theme Accent Colors |
| 50 | ⬜ | Dashboard Widget Customization |
| 51 | ⬜ | Real-Time Per-File Export Progress |
| 52 | ⬜ | Bulk Import/Export of Settings |
| 53 | ⬜ | Undo for Destructive Actions |
| 54 | ⬜ | Guided Onboarding Tour |
| 55 | ⬜ | Mobile-Responsive Layout |

### Phase 8: Performance (2/7)
| # | Status | Item |
|---|---|---|
| 56 | ⬜ | Server-Side Document Filtering |
| 57 | ✅ | Single-Query Queue Stats |
| 58 | ✅ | Export Engine Config Caching |
| 59 | ⬜ | SQLite Connection Reuse |
| 60 | ⬜ | Frontend Asset Minification |
| 61 | ⬜ | Database Query Pagination |
| 62 | ⬜ | Lazy-Load Page Sections |

### Phase 9: Testing (1/8)
| # | Status | Item |
|---|---|---|
| 63 | ⬜ | Full CLI Integration Tests |
| 64 | ⬜ | SSE Streaming Endpoint Tests |
| 65 | ⬜ | Concurrency Tests |
| 66 | ⬜ | Real Onshape API Smoke Tests |
| 67 | ⬜ | pytest Fixtures & Parametrize Migration |
| 68 | ✅ | Test Coverage Enforcement Config |
| 69 | ⬜ | Property-Based Testing |
| 70 | ⬜ | End-to-End Test |

### Phase 10: Production Readiness (3/8)
| # | Status | Item |
|---|---|---|
| 71 | ✅ | GitHub Actions CI/CD Pipeline |
| 72 | ⬜ | Docker Containerization |
| 73 | ⬜ | Database Migration Integration Tests |
| 74 | ⬜ | Anonymous Telemetry Opt-In |
| 75 | ⬜ | Cross-Platform CI Matrix |
| 76 | ✅ | Pre-Commit Hooks Config |
| 77 | ⬜ | Semantic Versioning & Changelog |
| 78 | ✅ | Security Vulnerability Scanning (SECURITY.md) |

---

## EXECUTION SUMMARY

| Phase | Name | Items | Done | Remaining Effort |
|---|---|---|---|---|
| **A** | Architectural Refactors | 6 | 0 | ~86h |
| **B** | Core Architecture Hardening | 8 | 0 | ~70h |
| **C** | Domain Model Cleanup | 10 | 0 | ~73h |
| **D** | User-Facing Features & UX | 8 | 0 | ~62h |
| **E** | Performance Optimization | 6 | 0 | ~27h |
| **F** | Testing & Quality | 7 | 0 | ~54h |
| **G** | Quick Wins | 10 | 0 | ~47h |
| **—** | Already Completed | **20** | **20** | — |
| **Total** | | **78** | **20** | **~419h** |

---

*Ordered hardest-first: architectural changes that affect everything come before features that depend on stable architecture. Quick wins are independent and can be done anytime by any contributor.*

---

## How to Read This Document

Each improvement follows a consistent structure:

- **Title** — One-line summary of the change
- **Problem** — What's broken or missing, with specific evidence from the codebase
- **Root Cause** — Why the problem exists (design decision, oversight, organic growth)
- **Impact** — Who and what is affected (users, developers, operators)
- **Proposed Solution** — Concrete implementation approach
- **Priority** — Critical / High / Medium / Low
- **Difficulty** — Easy (hours) / Medium (days) / Hard (weeks)
- **Dependencies** — What must be completed first
- **Files Affected** — Specific files that will be modified or created
- **Estimated Effort** — In developer-hours
- **Risk** — Likelihood and severity of regression
- **Expected Improvement** — Measurable outcome
- **Status** — Proposed (all items start here)

---

## Phase 1: Critical Architectural Fixes

> **Why Phase 1?** These items fix fundamental correctness and safety problems. Without them, efforts in later phases may be built on broken foundations. A queue that can double-process jobs, a scheduler that never re-syncs, and unguarded mutable state are bugs that undermine the entire application.

---

### Item 1: Atomic Queue Claim

**Title**: Make `claim_next()` atomic to prevent double-processing

**Problem**: `QueueManager.claim_next()` reads the next due job (`due_jobs(limit=1)`), then calls `update_queue_status(job_id, RUNNING)` in a separate database transaction. Between read and write, another worker could claim the same job. The docstring acknowledges that this "may race under concurrent workers."

**Root Cause**: The queue was designed for a single-worker model. `claim_next()` was written as a two-step read-then-write without considering that SQLite supports atomic `UPDATE ... RETURNING` in WAL mode.

**Impact**: Under any concurrent load (multiple workers, or web-initiated exports while worker is running), jobs may be exported twice, wasting API quota and producing duplicate files.

**Proposed Solution**: Replace the two-step claim with a single atomic SQL statement:
```sql
UPDATE queue
SET status = 'running', started_at = ?
WHERE id = (
    SELECT id FROM queue
    WHERE status = 'pending'
      AND (next_run_at IS NULL OR next_run_at <= ?)
    ORDER BY created_at ASC
    LIMIT 1
)
RETURNING *
```
SQLite's WAL mode makes this single-writer safe. The `RETURNING` clause eliminates the need for a separate read.

**Priority**: Critical
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/database.py`, `onshape_export_manager/core/queue_manager.py`
**Estimated Effort**: 3 hours
**Risk**: Low — the change is well-contained; existing tests validate queue behavior and will catch regressions
**Expected Improvement**: Queue becomes safe for concurrent workers. Eliminates the most significant correctness bug in the system.
**Status**: Proposed

---

### Item 2: Thread-Safe ApiPool State Mutation

**Title**: Add thread safety to `AccountRuntimeState` mutations in `ApiPool`

**Problem**: `ApiPool.lease()`, `record_success()`, `record_failure()`, and `record_rate_limited()` all mutate `AccountRuntimeState` attributes (`api_usage`, `failure_count`, `last_used`, `rate_limited_until`) without synchronization. The web dashboard queries account status via `/api/accounts` while the worker thread is recording export results. A read during a write may observe a partially-updated state.

**Root Cause**: `ApiPool` was designed when the application was single-threaded. The addition of the background worker thread (which calls `record_success`/`record_failure`) created a data race with the web thread (which calls `snapshot()` for the dashboard).

**Impact**: Dashboard may show stale or inconsistent account health data. In the worst case, a torn read of `rate_limited_until` could cause the web UI to show an account as available when it's actually rate-limited.

**Proposed Solution**: Add a `threading.Lock` to `ApiPool` and guard all `AccountRuntimeState` mutations and reads. Alternatively, make `AccountRuntimeState` immutable and use `ApiPool` as the sole owner of the mutable collection, with atomic replacement of the entire state dict.

**Priority**: Critical
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/api_pool.py`
**Estimated Effort**: 4 hours
**Risk**: Medium — locking can introduce deadlocks if not carefully ordered. The solution should use a single coarse lock initially, then profile before optimizing.
**Expected Improvement**: Consistent account health reporting. No torn reads of rate-limit state.
**Status**: Proposed

---

### Item 3: Thread-Safe CredentialPool State Mutation

**Title**: Add thread safety to `CredentialState` mutations in `CredentialPool`

**Problem**: Identical to Item 2 but for the organizations-based credential pool. `CredentialPool` tracks per-credential `requests_today`, `failure_count`, `last_used`, and `latency_ema` in mutable `CredentialState` objects. These are read by the dashboard and written by the worker without synchronization.

**Root Cause**: Same as Item 2 — the `CredentialPool` was added after the worker thread already existed, without considering thread safety.

**Impact**: Same as Item 2.

**Proposed Solution**: Apply the same locking strategy as Item 2. Since `ApiPool` and `CredentialPool` will eventually be unified (see Item 9), implement the lock in a way that's compatible with future unification.

**Priority**: Critical
**Difficulty**: Medium
**Dependencies**: None (but should be coordinated with Item 2 for consistency)
**Files Affected**: `onshape_export_manager/core/organizations.py`
**Estimated Effort**: 4 hours
**Risk**: Medium — same deadlock risk as Item 2
**Expected Improvement**: Consistent credential health reporting across organizations.
**Status**: Proposed

---

### Item 4: Scheduler Re-Sync on Config Changes

**Title**: Rebuild scheduler jobs when labels configuration changes

**Problem**: `BackgroundWorker._sync_scheduler_jobs()` runs once at worker startup. If a label is added, removed, enabled, disabled, or has its schedule changed while the worker is running, the scheduler's job list becomes stale. A deleted label with an active schedule will continue generating export jobs indefinitely until the worker is restarted.

**Root Cause**: The scheduler was designed with the assumption that labels are static after initial configuration. In practice, users modify labels through the web UI and expect changes to take effect immediately.

**Impact**: Users who modify label schedules through the web UI are confused when changes don't take effect. Deleted labels continue consuming API quota and generating failed exports.

**Proposed Solution**: Subscribe the `SchedulerService` to relevant events on the `EventBus` (e.g., `CONFIG_LABELS_CHANGED`). When such an event is emitted, call `sync_labels()` to rebuild the job list. The web API handlers that modify labels should emit these events after saving.

**Priority**: Critical
**Difficulty**: Medium
**Dependencies**: None (EventBus already exists)
**Files Affected**: `onshape_export_manager/core/scheduler.py`, `onshape_export_manager/core/worker.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 5 hours
**Risk**: Low — the `sync_labels()` method already works correctly; the change is only about when it's called
**Expected Improvement**: Label changes take effect within one tick cycle. No stale scheduler jobs from deleted labels.
**Status**: Proposed

---

### Item 5: Config File Change Detection and Hot-Reload

**Title**: Detect JSON config file changes and hot-reload without restart

**Problem**: The application reads all five JSON config files at startup and never re-reads them. Changes made by editing files directly (common on headless Raspberry Pi deployments) require a full application restart. The web UI writes changes through the API (which updates in-memory state), but there's no mechanism to detect external file changes.

**Root Cause**: The application assumes it is the sole writer of config files. In headless deployments, users often edit files via SSH + nano/vim, expecting changes to take effect on save.

**Impact**: Users on headless deployments must remember to restart the service after editing config files. Failure to do so leads to confusion when changes appear to be ignored.

**Proposed Solution**: Add a `watchdog`-based file watcher (or a simple polling approach using file modification times) that monitors the `config/` directory. When a change is detected, re-validate and reload the affected config. Emit events on the EventBus so subscribers (scheduler, UI) can react.

**Priority**: High
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/configuration.py`, `onshape_export_manager/app.py`
**Estimated Effort**: 8 hours
**Risk**: Medium — partial config reload during an in-flight export could cause inconsistency. The reload should be deferred if the worker is active.
**Expected Improvement**: Headless users can edit config files and see changes within seconds. Eliminates a common source of support requests.
**Status**: Proposed

---

### Item 6: Database File Locking During Backup Restore

**Title**: Prevent backup restore from corrupting the live database

**Problem**: `BackupManager.restore_backup()` overwrites the SQLite database file directly while the application is running. SQLite in WAL mode may have uncommitted writes in the WAL file that conflict with the restored database. There is no coordination with the `Database` instance to checkpoint and close connections.

**Root Cause**: The backup system was implemented as a filesystem-level ZIP tool without considering that the database is a live, in-use file.

**Impact**: Restoring a backup on a running instance could corrupt the database, requiring manual recovery. In the worst case, both the live database and the backup could be unusable.

**Proposed Solution**: Before restore, call `Database.checkpoint()` (to flush WAL to main database file), then close all connections. Perform the restore. Then re-open connections. The web UI should show a clear warning that restore requires a brief service interruption.

**Priority**: Critical
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/backup.py`, `onshape_export_manager/core/database.py`
**Estimated Effort**: 3 hours
**Risk**: Low — the change adds safety; the pre-restore snapshot mechanism already provides a recovery path
**Expected Improvement**: Backup restore is safe to perform on a running instance. No risk of database corruption.
**Status**: Proposed

---

### Item 7: Login Brute-Force Rate Limiting

**Title**: Add rate limiting to the login endpoint

**Problem**: The `/login` endpoint has no rate limiting. An attacker can submit unlimited password attempts. There is no account lockout, no progressive delay, and no CAPTCHA. Failed login attempts are logged to the application log but not to the audit event system, so operators have no visibility into attacks.

**Root Cause**: The application was designed for localhost use where brute-force attacks are not a concern. The reverse proxy documentation encourages internet exposure, which changes the threat model.

**Impact**: Credential brute-forcing is feasible for any attacker who can reach the login endpoint over the network. The scrypt password hashing provides some resistance (it's slow by design), but unlimited attempts eventually succeed against weak passwords.

**Proposed Solution**: Implement progressive delay: after 5 failed attempts, introduce a 1-second delay; after 10, 5 seconds; after 15, 30 seconds. Track attempts per IP in memory (or in the database for persistence across restarts). Emit audit events for failed logins so notifications can alert operators.

**Priority**: High
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/auth.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 4 hours
**Risk**: Low — rate limiting only affects the login path
**Expected Improvement**: Brute-force attacks become infeasible. Operators are alerted to attack attempts via the notification system.
**Status**: Proposed

---

### Item 8: API-Wide Request Rate Limiting

**Title**: Add rate limiting to all API endpoints

**Problem**: No API endpoint has rate limiting. A buggy client, a script in a loop, or a malicious actor can flood any endpoint — including expensive ones like `/api/metrics` (which walks the entire filesystem) or `/api/exports/run` (which enqueues jobs).

**Root Cause**: Rate limiting was never implemented. The application was designed for a single trusted user on localhost.

**Impact**: Accidental or malicious API flooding can degrade performance, fill the queue with garbage jobs, or cause disk I/O saturation from repeated metrics queries.

**Proposed Solution**: Add FastAPI middleware that applies token-bucket rate limiting per IP address. Configure generous limits for normal use (e.g., 60 requests/minute for read endpoints, 10/minute for write endpoints). Make limits configurable in `config.json`.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py`
**Estimated Effort**: 3 hours
**Risk**: Low — generous limits won't affect normal usage
**Expected Improvement**: Protection against accidental or malicious API flooding.
**Status**: Proposed

---

## Phase 2: Backend Redesign

> **Why Phase 2?** Phase 1 fixed correctness bugs. Phase 2 addresses structural design issues that make the codebase harder to extend, test, and maintain. These changes establish patterns that all future code should follow. Without them, each new feature adds to the architectural debt.

---

### Item 9: Unify ApiPool and CredentialPool

**Title**: Merge `ApiPool` (flat accounts) and `CredentialPool` (organizations) into a single credential management service

**Problem**: Two separate subsystems manage API credentials: `ApiPool` (backed by `accounts.json`) and `CredentialPool` (backed by `organizations.json`). They have different state tracking (simple counters vs. EMA latency), different persistence strategies, different selection algorithms, and different APIs. New features must be implemented twice or, in practice, only once — leaving the other pathway incomplete.

**Root Cause**: The organizations model was added as an "additive and backwards compatible" enhancement to the flat accounts model. The migration was started (import functionality exists) but never completed.

**Impact**: Code duplication (~300 lines), inconsistent behavior between the two credential pathways, maintenance burden, and confusion for developers about which system to use.

**Proposed Solution**:
1. Define a unified `CredentialProvider` interface with a single `lease()` method
2. Create `FlatCredentialProvider` (wrapping current `ApiPool` logic) and `OrganizationCredentialProvider` (wrapping current `CredentialPool` logic)
3. Both implement the same interface
4. `ConfigManager` decides which provider to instantiate based on whether `organizations.json` has entries
5. Mark `accounts.json` support as deprecated with a clear timeline for removal
6. Add a migration command that converts `accounts.json` to `organizations.json` automatically on startup

**Priority**: High
**Difficulty**: Hard
**Dependencies**: Items 2, 3 (thread safety should be implemented first, then unified)
**Files Affected**: `onshape_export_manager/core/api_pool.py`, `onshape_export_manager/core/organizations.py`, `onshape_export_manager/core/configuration.py`, `onshape_export_manager/app.py`, `onshape_export_manager/core/export_engine.py`
**Estimated Effort**: 16 hours
**Risk**: High — credential management is a critical path. The unified interface must be thoroughly tested with both providers. Backward compatibility with existing `accounts.json` configs must be maintained during the transition.
**Expected Improvement**: Single code path for credential management. Consistent selection algorithm. One place to add features. ~300 lines of duplicated code removed.
**Status**: Proposed

---

### Item 10: Dependency Injection Container

**Title**: Replace manual service locator with a typed dependency injection system

**Problem**: The `Application` dataclass serves as a manual service locator. Every service receives the entire `Application` and picks what it needs. There is no way to express "this component requires a `Database` and an `EventBus`" in the type system. Service construction order is implicit in `bootstrap()`. Testing requires constructing a full `Application` even when only one service is needed.

**Root Cause**: The project started small and grew organically. A dataclass with nullable fields was the simplest thing that worked at the time.

**Impact**: Hidden coupling between services, difficulty testing in isolation, no compile-time verification that all dependencies are satisfied, no clear initialization order.

**Proposed Solution**:
1. Define a `ServiceContainer` protocol or class that explicitly declares dependencies
2. Use constructor injection consistently: every service receives exactly what it needs, not the whole container
3. Wire dependencies in a single `bootstrap()` function with explicit ordering
4. Provide factory functions for optional dependencies (services that may be `None` when config is invalid)
5. This does NOT require a framework like `dependency-injector` — a simple function that constructs services in order and passes them is sufficient and keeps dependencies minimal

**Priority**: High
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/app.py`, all service files in `core/`, `onshape_export_manager/web.py`
**Estimated Effort**: 12 hours
**Risk**: Medium — this is a wide-reaching refactor. Tests provide a safety net, but the change touches every service constructor.
**Expected Improvement**: Explicit, typed, testable dependency graph. Services can be tested in isolation. New developers can understand the dependency structure by reading one function.
**Status**: Proposed

---

### Item 11: Extract Route Modules from web.py

**Title**: Split monolithic `web.py` (1,300+ lines) into domain-specific route modules

**Problem**: `web.py` contains 50+ endpoint handlers, authentication middleware, WebSocket management, SSE streaming, template rendering, and setup wizard logic. It is the largest file in the project and grows with every new feature. FastAPI's `APIRouter` composition features are unused.

**Root Cause**: The project started with a single route file and never refactored as the API surface grew.

**Impact**: Merge conflicts on every feature branch, difficulty understanding which handler belongs to which domain, no clear boundary between HTTP concerns and business logic.

**Proposed Solution**: Create a `routes/` package with domain-specific modules:
```
onshape_export_manager/routes/
    __init__.py          # Composes all routers into the FastAPI app
    organizations.py     # /api/organizations/*
    accounts.py          # /api/accounts
    labels.py            # /api/labels
    profiles.py          # /api/profiles, /api/formats
    exports.py           # /api/exports/*
    queue.py             # /api/queue/*
    scheduler.py         # /api/scheduler
    history.py           # /api/history
    worker.py            # /api/worker/*
    system.py            # /api/system, /api/remote-access
    events.py            # /api/events/*
    telemetry.py         # /api/telemetry/*
    notifications.py     # /api/notifications/*
    logs.py              # /api/logs/*
    search.py            # /api/search
    backups.py           # /api/backups
    setup.py             # /api/setup/*
    auth.py              # /login, /logout, auth middleware
    pages.py             # GET routes that render HTML templates
    ws.py                # WebSocket /ws/events
    sse.py               # SSE /api/stream
```
Each module receives dependencies via FastAPI's `Depends()` or by closing over an `Application` reference passed at router creation time.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 10 (DI container makes passing dependencies to routers cleaner)
**Files Affected**: `onshape_export_manager/web.py` (becomes `routes/__init__.py`), new files in `routes/`
**Estimated Effort**: 12 hours
**Risk**: Medium — large refactor, but existing integration tests in `test_web_api.py` validate all endpoints and should catch regressions
**Expected Improvement**: Each route file is 50-150 lines. Merge conflicts reduced. Clear boundaries between domains.
**Status**: Proposed

---

### Item 12: Standardized API Response Envelope

**Title**: Wrap all API responses in a consistent JSON envelope

**Problem**: API endpoints return inconsistent response shapes. Some return bare objects (`{"id": "...", "name": "..."}`), some return arrays at the top level, and error responses use FastAPI's default format. There is no standard way to include metadata, pagination info, or request context.

**Root Cause**: Endpoints were added incrementally without a response format standard.

**Impact**: Frontend code must handle multiple response shapes. Adding pagination or metadata to an endpoint requires changing both the backend response and all frontend consumers.

**Proposed Solution**: Define a standard envelope:
```json
{
    "data": { ... },
    "meta": {
        "page": 1,
        "page_size": 50,
        "total": 234,
        "request_id": "uuid"
    },
    "error": null
}
```
Error responses use the same envelope with `data: null` and `error: { "code": "...", "message": "...", "details": [...] }`. Implement as FastAPI middleware or a response model base class.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None (but should be implemented before Item 11 to avoid rewriting handlers twice)
**Files Affected**: `onshape_export_manager/web.py` (or new routes), `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 8 hours
**Risk**: Medium — requires coordinated frontend and backend changes. All API consumers must be updated.
**Expected Improvement**: Consistent API surface. Frontend can use a single response parser. Pagination and metadata are naturally supported.
**Status**: Proposed

---

### Item 13: Centralized Exception-to-HTTP Error Mapping

**Title**: Map all application exceptions to HTTP responses in one place

**Problem**: Error handling is inconsistent across endpoints. Some handlers return FastAPI `HTTPException`, some return JSON error dicts, some let exceptions propagate to FastAPI's default handler. There is no mapping from domain exceptions (`ConfigError`, `ApiPoolError`, `ExportEngineError`) to HTTP status codes.

**Root Cause**: Error handling was added per-endpoint without a global strategy.

**Impact**: Inconsistent error responses confuse API consumers. Adding a new exception type requires updating every handler that might raise it.

**Proposed Solution**: Add a FastAPI exception handler that maps domain exception types to HTTP status codes and response bodies. Define a registry:
```python
EXCEPTION_MAP = {
    ConfigError: (400, "CONFIG_INVALID"),
    ApiPoolError: (502, "UPSTREAM_UNAVAILABLE"),
    NoEnabledAccountsError: (503, "NO_ACCOUNTS_AVAILABLE"),
    ExportEngineError: (500, "EXPORT_FAILED"),
    # ...
}
```
Individual handlers should NOT catch exceptions for HTTP mapping — let them propagate to the global handler.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 12 (response envelope format should be used by the error handler)
**Files Affected**: `onshape_export_manager/web.py`, all `core/*.py` files that define exceptions
**Estimated Effort**: 4 hours
**Risk**: Low — additive change; existing behavior can be preserved during transition
**Expected Improvement**: Consistent error responses. Adding a new exception type requires only one registry entry.
**Status**: Proposed

---

### Item 14: Request/Response Validation Layer

**Title**: Add Pydantic models for all API request bodies and query parameters

**Problem**: Some endpoints use raw `request: Request` and manually parse JSON, while others use Pydantic models. There is no consistent validation layer. Query parameters for filtering and pagination are validated manually with ad-hoc defaults.

**Root Cause**: FastAPI's Pydantic integration was adopted inconsistently as endpoints were added.

**Impact**: Inconsistent validation, duplicated parsing logic, missing error messages for invalid input, no automatic OpenAPI schema generation for some endpoints.

**Proposed Solution**: Create Pydantic models for every request body and every set of query parameters. Use FastAPI's `Query()`, `Body()`, and `Path()` with validation constraints (`min_length`, `regex`, `gt`, `lt`). FastAPI automatically generates OpenAPI schemas and validation errors from these models.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py` (or new route files)
**Estimated Effort**: 6 hours
**Risk**: Low — additive change; stricter validation may reject previously-accepted invalid input, which is the desired behavior
**Expected Improvement**: Automatic request validation. Complete OpenAPI schema. Consistent error messages for invalid input.
**Status**: Proposed

---

### Item 15: API Versioning via URL Prefix

**Title**: Add `/api/v1/` prefix to all API routes and support versioned endpoints

**Problem**: All API endpoints live at `/api/...` with no version prefix. Any breaking change (renamed field, changed response shape, removed endpoint) breaks all existing API consumers simultaneously. There is no mechanism to support old and new API versions side by side.

**Root Cause**: The API was built for a single frontend that is always deployed together with the backend.

**Impact**: The API cannot evolve without breaking changes. External tooling or scripts that use the API are fragile. The frontend and backend are tightly coupled by deployment timing.

**Proposed Solution**: Move all current endpoints under `/api/v1/`. Add redirects from `/api/...` to `/api/v1/...` for backward compatibility (with deprecation warnings in response headers). When a breaking change is needed, create `/api/v2/...` alongside `/api/v1/...`.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None (but ideally after Item 11 so route modules are already extracted)
**Files Affected**: `onshape_export_manager/web.py` (or route modules), `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 4 hours
**Risk**: Low — the old paths can redirect to new paths; existing scripts continue to work
**Expected Improvement**: API can evolve without breaking consumers. Clear deprecation path.
**Status**: Proposed

---

### Item 16: Remove Dead HTMX Dependency

**Title**: Remove the HTMX CDN script tag from templates

**Problem**: `base.html` loads HTMX (v1.9.10) via CDN, but no template uses `hx-*` attributes. This is dead code — 28KB of JavaScript loaded on every page with zero benefit.

**Root Cause**: HTMX was likely added during early prototyping with the intention of using it for dynamic page updates, but Alpine.js ended up handling all interactivity instead. The script tag was never removed.

**Impact**: Every page load fetches an unused 28KB JavaScript file from a CDN. Slightly slower page loads, unnecessary external dependency, and confusion for developers who wonder why HTMX is included.

**Proposed Solution**: Remove the `<script src="...htmx...">` tag from `base.html`. Remove `htmx.org` from any Content-Security-Policy if one exists.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/ui/templates/base.html`
**Estimated Effort**: 15 minutes
**Risk**: None — verify no template uses `hx-*` before removing
**Expected Improvement**: One fewer CDN dependency. Cleaner template code.
**Status**: Proposed

---

## Phase 3: Frontend Redesign

> **Why Phase 3?** The backend API surface must be stable before the frontend can be restructured to consume it. Phase 2 establishes the API contract (versioning, envelope, route organization). Phase 3 modernizes the frontend to match.

---

### Item 17: Bundled ES Modules with Build Step

**Title**: Replace CDN-loaded Alpine.js with bundled ES modules and a build step

**Problem**: Alpine.js, Chart.js, Flatpickr, and Tailwind CSS are all loaded from CDN. This means: no tree-shaking, no minification, no dependency version locking (CDN scripts use fuzzy versions like `@3`), and no offline capability. Every page load fetches 5+ separate CDN resources.

**Root Cause**: The project started as a prototype where CDN scripts were the fastest way to get a working UI.

**Impact**: Slower page loads, dependency on internet connectivity (the app runs on a local network but the frontend requires CDN access), no control over when dependencies update, larger total JavaScript payload than necessary.

**Proposed Solution**: Add a lightweight build step using Vite or esbuild:
1. Create `ui/package.json` with pinned dependencies
2. Use ES module imports in JavaScript
3. Bundle to a single `ui/static/dist/` output
4. Serve bundled assets with content-hash filenames for cache-busting
5. Keep Tailwind via CDN or bundle it with purgecss to remove unused styles

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New `ui/package.json`, `ui/src/` directory, `ui/static/app.js` → `ui/src/`, template `base.html` (script tags)
**Estimated Effort**: 10 hours
**Risk**: Medium — requires node.js in the development workflow; the build output is static files that don't change the deployment model
**Expected Improvement**: Faster page loads (single bundled file), offline-capable (assets served locally), pinned dependency versions, smaller total payload via tree-shaking.
**Status**: Proposed

---

### Item 18: Modularize app.js

**Title**: Split monolithic `app.js` (~1,500 lines) into domain-specific modules

**Problem**: `app.js` contains all three Alpine.js components (`appShell`, `dashboardPage`, `sectionPage`), all API call functions, inline SVG icons, the command palette, toast system, and manual export wizard — in a single file with no module boundaries.

**Root Cause**: Organic growth from prototype to full application without refactoring.

**Impact**: Merge conflicts, difficulty finding specific code, no clear ownership of functions, impossible to unit test individual modules.

**Proposed Solution**: Split into ES modules:
```
ui/src/
    main.js              # Alpine.js init, global setup
    components/
        app-shell.js     # appShell component
        dashboard.js     # dashboardPage component
        section-page.js  # sectionPage component
    services/
        api.js           # fetchJSON wrapper, all API calls
        sse.js           # SSE stream management
        ws.js            # WebSocket management
        search.js        # Command palette search
        toast.js         # Toast notification system
    utils/
        icons.js         # Inline SVG icon definitions
        format.js        # Date/number formatting
        storage.js       # localStorage wrapper
    pages/
        manual-export.js # Manual export wizard logic
        wizard.js        # Setup wizard logic
```

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 17 (ES module structure depends on build step)
**Files Affected**: `onshape_export_manager/ui/static/app.js` → multiple files
**Estimated Effort**: 10 hours
**Risk**: Medium — large refactor but no behavior change; manual testing of all pages required
**Expected Improvement**: Each module is 50-200 lines. Clear ownership. Testable in isolation.
**Status**: Proposed

---

### Item 19: Extract Reusable UI Components

**Title**: Create a shared component library for toast, modal, table, form, and chart elements

**Problem**: UI patterns are duplicated across pages. Toast notifications, modal dialogs, data tables, and form layouts are re-implemented inline in each Alpine.js component. There is no shared component abstraction.

**Root Cause**: Alpine.js components were written per-page without extracting shared patterns.

**Impact**: Inconsistent behavior between similar UI elements. Fixing a bug in one component doesn't fix it in the copy. Changing the design of a shared element requires changes in multiple places.

**Proposed Solution**: Create reusable Alpine.js components using `Alpine.data()`:
- `toastContainer` — Global toast stack with enter/exit transitions
- `modalDialog` — Accessible modal with focus trapping and Escape to close
- `dataTable` — Sortable, filterable table with column configuration
- `formField` — Input with label, error message, and validation state
- `chartWidget` — Chart.js wrapper with loading, empty, and error states
- `confirmButton` — Button with confirmation dialog before destructive actions

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Items 17, 18
**Files Affected**: New files in `ui/src/components/`, modified page components
**Estimated Effort**: 12 hours
**Risk**: Low — additive; existing pages continue to work while being migrated to components
**Expected Improvement**: Consistent UI behavior. Single place to fix bugs. Single place to apply design changes.
**Status**: Proposed

---

### Item 20: Accessibility Audit and Remediation

**Title**: Make the entire UI accessible (WCAG 2.1 AA)

**Problem**: The UI has no accessibility features: no ARIA labels, no `role` attributes, no focus trapping in modals, no keyboard navigation beyond the command palette, no screen reader announcements for dynamic content updates, low-contrast text in several places.

**Root Cause**: Accessibility was not a consideration during prototype development.

**Impact**: The application is unusable by keyboard-only users and screen reader users. This is both an ethical concern and, in some jurisdictions, a legal compliance issue.

**Proposed Solution**:
1. Add ARIA labels to all interactive elements (buttons, links, inputs)
2. Add `role` attributes to custom components (modals have `role="dialog"`, toasts have `role="status"`)
3. Implement focus trapping in modals and the command palette
4. Add keyboard handlers for all mouse-driven interactions (Enter/Space for buttons, Escape for closing, arrow keys for navigation)
5. Add `aria-live` regions for dynamic content (SSE updates, toast notifications, queue status changes)
6. Increase contrast ratios on secondary text to meet WCAG AA (4.5:1 for normal text, 3:1 for large text)
7. Add skip-to-content link as the first focusable element
8. Ensure all form inputs have associated `<label>` elements

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Items 18, 19 (accessibility is easier to implement in modular components)
**Files Affected**: All `ui/templates/*.html`, `ui/static/*.css`, `ui/src/components/`
**Estimated Effort**: 16 hours
**Risk**: Low — additive changes; no visual redesign required
**Expected Improvement**: WCAG 2.1 AA compliance. Usable by keyboard-only and screen reader users.
**Status**: Proposed

---

### Item 21: Client-Side Form Validation

**Title**: Add real-time form validation with inline error messages

**Problem**: Forms in the UI (label creation, profile editing, notification channel config) have no client-side validation. Users submit invalid data, receive a generic JSON error from the server, and must decode it to understand what went wrong.

**Root Cause**: Validation was implemented server-side only, with the assumption that the API would provide clear error messages. Server error messages are technical (e.g., "extra fields not permitted") rather than user-friendly.

**Impact**: Poor user experience. Increased server load from invalid submissions. Users must guess at format requirements.

**Proposed Solution**: Create a lightweight validation framework in JavaScript:
1. Define validation rules per form field (required, minLength, pattern, custom validator)
2. Validate on blur and on submit attempt
3. Show inline error messages below each field
4. Disable submit button until all fields are valid
5. Mirror server-side validation rules so client and server agree on what's valid

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Items 17, 18
**Files Affected**: New `ui/src/utils/validation.js`, modified form components
**Estimated Effort**: 6 hours
**Risk**: Low — additive; forms still submit to server for final validation
**Expected Improvement**: Immediate feedback on input errors. Fewer invalid submissions. Better user experience.
**Status**: Proposed

---

### Item 22: Standardize Loading, Empty, Error, and Offline States

**Title**: Create consistent UI patterns for all page states

**Problem**: Pages handle loading, empty, error, and offline states inconsistently. Some show spinners, some show nothing, some show raw error text. There is no standard skeleton loader, empty state illustration, error boundary, or offline indicator.

**Root Cause**: Each page was developed independently without shared state management patterns.

**Impact**: Jarring user experience when navigating between pages. Empty states are confusing (is it loading or is there really no data?). Errors are sometimes silent.

**Proposed Solution**: Create four standard Alpine.js patterns used by every page:
- **Loading**: Skeleton loader matching the page layout
- **Empty**: Illustrated empty state with a call-to-action ("Create your first label")
- **Error**: Error card with retry button and error details toggle
- **Offline**: Banner at top of page when SSE connection drops; disable action buttons
Each `sectionPage` instance should have `loading`, `error`, `offline` reactive properties that templates check.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: Items 17, 18
**Files Affected**: `ui/src/components/`, all page templates
**Estimated Effort**: 8 hours
**Risk**: Low — additive; pages that don't use the patterns continue to work
**Expected Improvement**: Consistent, predictable UX across all pages. No more "is it loading or broken?" confusion.
**Status**: Proposed

---

### Item 23: Replace Flatpickr CDN with Bundled Date Picker

**Title**: Bundle Flatpickr (or a lighter alternative) into the application build

**Problem**: Flatpickr is loaded from CDN and used only on the manual export page. This adds a CDN dependency for a feature used on one page. The CDN version is unversioned (`@4`).

**Root Cause**: Same as Item 17 — prototype convenience over production discipline.

**Impact**: Extra CDN dependency, version ambiguity, no offline support for date picker.

**Proposed Solution**: Install Flatpickr (or a lighter alternative like a native `<input type="date">` with polyfill) as an npm dependency and bundle it with the application. Consider whether the native date input (supported in all modern browsers) is sufficient for the date range picker use case.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: Item 17
**Files Affected**: `ui/package.json`, `ui/src/pages/manual-export.js`, `ui/templates/section.html`
**Estimated Effort**: 3 hours
**Risk**: Low — behavior unchanged
**Expected Improvement**: One fewer CDN dependency. Pinned Flatpickr version.
**Status**: Proposed

---

### Item 24: Service Worker for Offline Shell

**Title**: Add a service worker for offline asset caching and shell rendering

**Problem**: The application has no offline capability. If the network connection to the server drops, the browser shows a generic "cannot connect" page. Static assets (CSS, JS, icons) are re-fetched on every page load.

**Root Cause**: Service workers were not considered for what is primarily a locally-served application.

**Impact**: No offline resilience. Repeat visits fetch the same static assets.

**Proposed Solution**: Add a simple service worker that:
1. Pre-caches static assets (CSS, JS, icon SVGs) on install
2. Serves cached assets on subsequent visits (cache-first strategy)
3. Shows a cached "offline" shell when the server is unreachable
4. Updates cache in the background when new versions are detected

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: Item 17 (build step generates hashed asset filenames for cache invalidation)
**Files Affected**: New `ui/src/sw.js`, `ui/src/main.js` (registration)
**Estimated Effort**: 4 hours
**Risk**: Low — service workers are progressive enhancement; browsers that don't support them are unaffected
**Expected Improvement**: Faster repeat page loads. Graceful offline indication. One step closer to PWA capability.
**Status**: Proposed

---

## Phase 4: Domain Cleanup

> **Why Phase 4?** The domain model — accounts, labels, profiles, jobs — is the foundation of all business logic. Before extending functionality in Phase 5, the domain must be correct, consistent, and free of the shortcuts taken during prototyping.

---

### Item 25: Complete Organizations Migration

**Title**: Fully deprecate `accounts.json` in favor of `organizations.json`

**Problem**: The migration from flat accounts to hierarchical organizations was started but never completed. Both models coexist, creating the dual credential management problem (Item 9). New features that touch credentials must consider both models.

**Root Cause**: The organizations model was added incrementally without a plan for deprecating the old model.

**Impact**: Ongoing maintenance burden. Two code paths for every credential operation. Confusion for users about which config file to use.

**Proposed Solution**:
1. On startup, if `accounts.json` exists and `organizations.json` is empty, auto-migrate with a log message
2. Mark `accounts.json` as deprecated — the application reads it but logs a warning
3. After a deprecation period (2 minor versions), remove `accounts.json` support entirely
4. Update all documentation, the setup wizard, and the CLI to reference only organizations
5. Remove `ApiPool` in favor of the unified provider from Item 9

**Priority**: High
**Difficulty**: Medium
**Dependencies**: Item 9 (unified credential provider)
**Files Affected**: `onshape_export_manager/core/configuration.py`, `onshape_export_manager/core/api_pool.py`, `onshape_export_manager/web.py`, `onshape_export_manager/cli.py`, all documentation
**Estimated Effort**: 8 hours
**Risk**: Medium — must handle existing installations with `accounts.json` gracefully during transition
**Expected Improvement**: Single credential model. ~300 lines of duplicated code removed. Clear path forward.
**Status**: Proposed

---

### Item 26: Multi-Part-Studio Document Support

**Title**: Export all Part Studios in a document, not just the first one

**Problem**: `_export_documents()` in `export_engine.py` exports only the first Part Studio found in each document. The docstring explicitly acknowledges this is "preserving proof-of-concept behavior." Documents with multiple Part Studios (common in assemblies) have all but the first silently skipped.

**Root Cause**: During development, exporting one Part Studio per document was sufficient for testing. The iteration was never implemented.

**Impact**: Users with assembly documents get incomplete exports. No warning or error indicates that Part Studios were skipped.

**Proposed Solution**: Iterate all Part Studios (and potentially Assemblies, if supported by export formats) in each document. Export each one as a separate file with the Part Studio name in the filename. Track per-Part-Studio success/failure in the export result.

**Priority**: High
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/export_engine.py`
**Estimated Effort**: 3 hours
**Risk**: Low — additive; existing single-Part-Studio behavior is a subset of the new behavior
**Expected Improvement**: Complete document exports. No silently skipped content.
**Status**: Proposed

---

### Item 27: Document Name Collision Prevention

**Title**: Handle documents with identical names within the same label

**Problem**: `_export_documents()` uses the document name in the export filename. If two documents in the same label have the same name, the second export will overwrite the first (unless `never_overwrite` is enabled, in which case it gets a `_2` suffix from `unique_path()`). The collision is not reported to the user.

**Root Cause**: Document names are not guaranteed unique within an Onshape label.

**Impact**: Silent data loss (overwritten export) or confusing filenames (`Part_2.stl`).

**Proposed Solution**: Include the Onshape document ID (a short hash) in the export filename or folder path. This guarantees uniqueness without relying on user-chosen document names. Report collisions as warnings in the export summary.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/export_engine.py`, `onshape_export_manager/core/folder_manager.py`
**Estimated Effort**: 2 hours
**Risk**: Low — filename format change; existing export paths are timestamped so there's no backward compatibility concern
**Expected Improvement**: No silent overwrites. Clear, unique filenames.
**Status**: Proposed

---

### Item 28: Per-Format Export Option Schemas

**Title**: Replace `dict[str, Any]` export options with strict per-format Pydantic models

**Problem**: `ExportProfileConfig.options` is typed as `dict[str, Any]`, allowing any keys and values. There is no validation that STL options include `mode`, `resolution`, and `units`, or that STEP options are valid. Invalid options are passed through to the Onshape API and fail at request time with a confusing error.

**Root Cause**: Different export formats have different option schemas, and modeling all of them with Pydantic was deferred.

**Impact**: Users can configure invalid export options that fail at runtime. No guidance in the UI about what options are available for each format.

**Proposed Solution**: Define Pydantic models for each format's options:
```python
class StlOptions(StrictConfigModel):
    mode: Literal["binary", "ascii"] = "binary"
    resolution: Literal["coarse", "medium", "fine"] = "medium"
    units: Literal["inch", "millimeter"] = "millimeter"

class StepOptions(StrictConfigModel):
    ...
```
Use a discriminated union on `ExportProfileConfig` to validate options against the format list. Expose option schemas via the `/api/formats` endpoint so the UI can render appropriate option fields.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/configuration.py`, `onshape_export_manager/core/export_formats.py`, `onshape_export_manager/core/models.py`
**Estimated Effort**: 6 hours
**Risk**: Low — stricter validation may reject previously-accepted invalid config, but that's the intended behavior
**Expected Improvement**: Invalid export options caught at config load time, not at export time. UI can show format-specific option fields.
**Status**: Proposed

---

### Item 29: Label Reference Integrity

**Title**: Prevent deletion of accounts or profiles that are referenced by labels

**Problem**: Deleting an account or export profile does not check whether any labels reference it. If a label's `assigned_accounts` includes a deleted account, exports for that label will fail with an unclear error. The UI allows deletion without warning.

**Root Cause**: Config files are independent JSON documents with no referential integrity enforcement.

**Impact**: Users can accidentally break their export configuration by deleting a referenced resource. The failure occurs at export time, possibly hours or days after the deletion.

**Proposed Solution**: Before deleting an account or profile, check all labels for references. If references exist, either:
1. Reject the deletion with a clear error listing the referencing labels
2. Offer to update the referencing labels to remove the reference (with explicit user confirmation)

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/configuration.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 3 hours
**Risk**: Low — additive safety check
**Expected Improvement**: No accidental breakage of export configuration. Clear error messages when deletion would cause problems.
**Status**: Proposed

---

### Item 30: Formalize Job Status State Machine

**Title**: Enforce valid state transitions for export jobs

**Problem**: `JobStatus` is a `StrEnum` with five values, but there is no enforcement of valid transitions. Code in `QueueManager` manually checks "if status is PENDING, change to RUNNING" in multiple places. A bug could transition a job from COMPLETED to RUNNING or from RUNNING to PENDING.

**Root Cause**: The status enum was added for type safety, but the transition logic was never centralized.

**Impact**: Bugs in status transitions could cause jobs to be processed multiple times, stuck in impossible states, or reported incorrectly in the dashboard.

**Proposed Solution**: Define valid transitions explicitly:
```python
VALID_TRANSITIONS = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.FAILED: {JobStatus.PENDING},  # retry
    JobStatus.COMPLETED: set(),  # terminal
    JobStatus.CANCELLED: set(),  # terminal
}
```
Create a single `transition_job(job_id, new_status)` method in `QueueManager` that validates the transition before updating the database. Remove scattered status update calls.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/queue_manager.py`, `onshape_export_manager/core/jobs.py`
**Estimated Effort**: 3 hours
**Risk**: Low — behavioral change only if invalid transitions were happening (which would be bugs)
**Expected Improvement**: Impossible to create jobs in invalid states. Single place to audit all status transitions.
**Status**: Proposed

---

### Item 31: Normalize Datetime Handling

**Title**: Use timezone-aware datetimes consistently throughout the codebase

**Problem**: The codebase mixes timezone-aware and timezone-naive datetimes. `utc_now()` in `database.py` returns a UTC-aware datetime, but `parse_dt()` in `api_pool.py` returns a naive datetime. Some comparisons work accidentally because both values are naive; others would raise `TypeError` if one is aware and the other naive.

**Root Cause**: Python's datetime handling was added incrementally without a project-wide standard.

**Impact**: Potential for incorrect time comparisons, especially around DST transitions or when comparing timestamps from different sources (Onshape API, local filesystem, database).

**Proposed Solution**:
1. Standardize on UTC-aware datetimes everywhere
2. Make `utc_now()` the single source of "current time"
3. Ensure all `parse_dt()` functions return UTC-aware datetimes
4. Add a linting rule (or mypy plugin) to forbid naive datetimes
5. Store all timestamps in ISO 8601 with timezone in the database

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/database.py`, `onshape_export_manager/core/api_pool.py`, `onshape_export_manager/core/models.py`, `onshape_export_manager/core/export_engine.py`
**Estimated Effort**: 6 hours
**Risk**: Medium — datetime changes are subtle and can break time-dependent logic; existing tests with `Clock` should catch regressions
**Expected Improvement**: No timezone-related bugs. Consistent timestamp handling across the entire stack.
**Status**: Proposed

---

### Item 32: Standardize ID Generation

**Title**: Use a single ID generation strategy across the codebase

**Problem**: IDs are generated inconsistently: some use `uuid4()`, some use `hashlib.sha256(str(time.time()))`, some are manually constructed strings. Different ID formats make it harder to validate, compare, and debug. The database schema uses TEXT for IDs, which is slow for indexing with some formats.

**Root Cause**: No project-wide decision was made about ID format.

**Impact**: Inconsistent ID formats complicate debugging. Variable-length IDs make database indexes less efficient. Manual ID construction risks collisions.

**Proposed Solution**: Standardize on UUID4 for all generated IDs. Use `uuid.uuid4().hex` (32-char hex, no dashes) for database storage efficiency. Create a single `generate_id()` function in a shared utility module. Update all ID generation sites to use it.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: Many files across `core/` and `web.py`
**Estimated Effort**: 4 hours
**Risk**: Low — existing IDs are not affected; only new IDs use the standard format
**Expected Improvement**: Consistent, indexable IDs. Single source of truth for ID generation.
**Status**: Proposed

---

## Phase 5: Core Functionality

> **Why Phase 5?** The domain is clean, the architecture is sound, and the frontend is modernized. Now it's time to implement the features that were deferred as stubs or planned for future releases.

---

### Item 33: Implement Bambu Studio Integration

**Title**: Complete the Bambu Studio slice-and-export pipeline (currently stub)

**Problem**: `bambu.py` contains only a stub class (`BambuStudioRunner`) with a `create_project()` method that raises `NotImplementedError`. The configuration system supports Bambu settings (machine profile, process profile, auto-arrange, create 3MF), but the integration itself does nothing.

**Root Cause**: Bambu integration was marked as "Stage 14" and deferred.

**Impact**: Users who selected a Bambu-enabled export profile (there is a "Bambu STL" profile in the default config) get STL files but no Bambu Studio post-processing. The feature appears to be available but silently does nothing.

**Proposed Solution**:
1. Implement `BambuStudioRunner` to locate the Bambu Studio executable (from config or PATH)
2. Use `subprocess` to invoke Bambu Studio with the configured project file template
3. Support: import STL, auto-arrange on plate, slice with configured profiles, export G-code and/or 3MF
4. Report Bambu processing results in the export summary and history
5. Handle Bambu Studio not installed / not found with a clear error (not a crash)

**Priority**: Medium
**Difficulty**: Hard
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/bambu.py`, `onshape_export_manager/core/export_engine.py`, `onshape_export_manager/core/configuration.py`
**Estimated Effort**: 16 hours
**Risk**: High — subprocess management is error-prone; Bambu Studio CLI behavior may vary across versions and platforms
**Expected Improvement**: Complete STL→G-code pipeline for 3D printing users. One of the most requested features.
**Status**: Proposed

---

### Item 34: Plugin Loader and Registry

**Title**: Implement filesystem-based plugin discovery, loading, and lifecycle management

**Problem**: `plugins.py` defines a `Plugin` protocol but there is no loader, registry, or discovery mechanism. The plugin system is a specification without an implementation.

**Root Cause**: Plugins were designed as a future extension point. The protocol was defined to establish the contract, but the infrastructure to use it was deferred.

**Impact**: No way to extend the application without modifying core source code. The plugin system is documented as a feature but is not functional.

**Proposed Solution**:
1. Create a `PluginManager` that scans a `plugins/` directory for Python packages
2. Each package must have a `plugin.py` with a class implementing the `Plugin` protocol
3. Load plugins dynamically using `importlib`
4. Call `activate()` on load, `deactivate()` on unload
5. Expose an API for plugins to register hooks on the EventBus, add API routes, and inject UI components
6. Add CLI commands: `--list-plugins`, `--enable-plugin NAME`, `--disable-plugin NAME`
7. Add a Plugins section to the web UI showing installed plugins and their status

**Priority**: Medium
**Difficulty**: Hard
**Dependencies**: Item 10 (DI container simplifies plugin access to services)
**Files Affected**: `onshape_export_manager/core/plugins.py`, new `plugins/` directory, `onshape_export_manager/app.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 20 hours
**Risk**: High — dynamic code loading has security implications; plugin isolation and error handling must be carefully designed
**Expected Improvement**: Extensible application. Community can contribute integrations without modifying core code.
**Status**: Proposed

---

### Item 35: Label Group Exports

**Title**: Support exporting multiple labels in a single job

**Problem**: Each export job is tied to a single label. To export multiple labels (e.g., "Adriana_API" and "Bob_Projects"), users must create two separate manual export jobs or two separate scheduled jobs. There is no way to group them.

**Root Cause**: The one-label-per-job model was the simplest initial design.

**Impact**: Inconvenient for users who want to export all their labeled documents at once. Doubles the queue entries and API calls.

**Proposed Solution**: Allow `POST /api/exports/run` to accept an array of label names. The worker processes each label sequentially within a single job, reporting per-label progress. Scheduled jobs already map 1:1 to labels; add a "label group" concept to the scheduler that triggers multiple label exports on one schedule.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/export_engine.py`
**Estimated Effort**: 6 hours
**Risk**: Low — additive feature; single-label jobs continue to work as before
**Expected Improvement**: Users can trigger exports for all their labels in one action.
**Status**: Proposed

---

### Item 36: Export Retention Policies

**Title**: Auto-delete export files older than a configurable age

**Problem**: Exported files accumulate indefinitely. On a Raspberry Pi with limited storage, this eventually fills the SD card. There is no mechanism to automatically clean up old exports.

**Root Cause**: Retention was not implemented. The assumption was that users would manually manage disk space.

**Impact**: Risk of disk-full failures on long-running deployments. Manual cleanup is tedious.

**Proposed Solution**: Add `retention_days` to `config.json` under `folders`. On worker startup and periodically (daily), scan the exports directory and delete folders older than the retention period. Log deletions and emit audit events. Default to 0 (disabled — never delete).

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/configuration.py`, `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/settings.py`
**Estimated Effort**: 3 hours
**Risk**: Medium — auto-deletion is dangerous if configured incorrectly. Require explicit opt-in (not default). Double-check that the path being deleted is within the exports directory.
**Expected Improvement**: No disk-full failures. Automatic storage management for long-running deployments.
**Status**: Proposed

---

### Item 37: Export Archive Download

**Title**: Allow downloading completed export folders as ZIP archives from the web UI

**Problem**: There is no way to download exported files through the web UI. Users must access the filesystem directly (SSH, SMB, or physical access to the Raspberry Pi) to retrieve their exports.

**Root Cause**: The web UI was designed for monitoring and control, not file delivery.

**Impact**: Inconvenient for users who access the application remotely. The files must be transferred through a separate mechanism.

**Proposed Solution**: Add a download link to each history entry and queue entry (for completed jobs). The link streams a ZIP archive of the export folder. For large exports, show a progress indicator. Add a size limit (configurable) to prevent streaming multi-gigabyte archives.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/ui/templates/section.html`
**Estimated Effort**: 4 hours
**Risk**: Low — additive feature; streaming ZIP avoids memory issues with large files
**Expected Improvement**: Users can retrieve exports directly from the web UI.
**Status**: Proposed

---

### Item 38: Batch Queue Operations

**Title**: Support selecting multiple queue items and performing batch actions

**Problem**: The queue UI shows individual items with per-item cancel and retry buttons. To cancel 50 pending jobs, the user must click Cancel 50 times. There is no "Cancel All" or multi-select capability.

**Root Cause**: The queue UI was built for small numbers of jobs.

**Impact**: Painful user experience when the queue has many items (e.g., after a label with many documents is exported).

**Proposed Solution**: Add checkbox selection to queue items with a batch action toolbar: "Cancel Selected", "Retry Selected", "Delete Selected". Add "Cancel All Pending" and "Retry All Failed" quick actions.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py` (batch endpoint), `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 5 hours
**Risk**: Low — additive UI feature
**Expected Improvement**: Efficient management of large queues.
**Status**: Proposed

---

### Item 39: Export Job Chaining

**Title**: Allow one export job to trigger another on completion

**Problem**: Export jobs are independent. If a user wants to export label A and then label B (because B depends on A's output), they must manually coordinate timing or use separate schedules.

**Root Cause**: Jobs were designed as independent units of work.

**Impact**: Cannot express export dependencies. Users must use external scripting for multi-step workflows.

**Proposed Solution**: Add an optional `chain_to` field to the export job request, specifying a label and profile to export after successful completion. The worker enqueues the chained job when the parent completes successfully. Limit chain depth to prevent infinite loops.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/web.py`, `onshape_export_manager/core/models.py`
**Estimated Effort**: 4 hours
**Risk**: Medium — chaining could create long-running job chains that block the worker; depth limiting and timeout are essential
**Expected Improvement**: Multi-step export workflows can be expressed declaratively.
**Status**: Proposed

---

### Item 40: Duplicate Detection with Content Hashing

**Title**: Skip re-exporting files that have already been exported with identical content

**Problem**: If a scheduled export runs and no documents have changed, the same files are exported again, consuming API quota and disk space. There is no mechanism to detect that a document hasn't changed since the last export.

**Root Cause**: Export is based on label membership, not document modification state.

**Impact**: Wasted API quota, redundant disk usage, slower exports.

**Proposed Solution**: After exporting a Part Studio, compute a content hash (SHA-256) of the exported file. Store the hash in the export history. Before exporting again, fetch the document's `modifiedAt` timestamp from Onshape. If the timestamp hasn't changed since the last successful export, skip the document. Make this behavior optional (configurable) since some users want fresh exports regardless of modification state.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/export_engine.py`, `onshape_export_manager/core/database.py`, `onshape_export_manager/core/onshape_client.py`
**Estimated Effort**: 5 hours
**Risk**: Low — optional feature; off by default
**Expected Improvement**: Reduced API quota usage for scheduled exports of stable documents.
**Status**: Proposed

---

## Phase 6: Worker Improvements

> **Why Phase 6?** The worker is the heart of the application — it performs the actual exports. Phase 1 fixed its correctness (atomic queue, thread safety). Phase 6 improves its robustness, observability, and scalability.

---

### Item 41: True Multi-Worker Support

**Title**: Enable multiple concurrent workers with safe queue distribution

**Problem**: The `worker_count: 4` setting exists in `config.json` but has no effect. The `BackgroundWorker` is a single daemon thread. Starting multiple workers would trigger the TOCTOU race in `claim_next()` (addressed in Item 1).

**Root Cause**: Multi-worker support was aspirational but never implemented.

**Impact**: Export throughput is limited to one job at a time, sequentially. A single slow export (large assembly, slow Onshape API) blocks all other exports.

**Proposed Solution**: After Item 1 makes queue claims atomic:
1. Spawn `worker_count` worker threads, each with its own asyncio event loop
2. Each worker independently claims jobs from the shared queue
3. The atomic `UPDATE ... RETURNING` ensures no two workers claim the same job
4. Add `max_concurrent_exports` config to cap total parallelism
5. The web UI shows per-worker status in the worker page

**Priority**: High
**Difficulty**: Medium
**Dependencies**: Item 1 (atomic queue claim)
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/app.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 8 hours
**Risk**: Medium — concurrent workers share the ApiPool (addressed in Item 2) and the SQLite database; thorough concurrency testing required
**Expected Improvement**: Parallel exports. N× throughput improvement (up to API rate limits). The `worker_count` config setting finally works.
**Status**: Proposed

---

### Item 42: Worker Health Monitoring

**Title**: Add heartbeat, stall detection, and auto-restart for workers

**Problem**: If a worker thread hangs (e.g., infinite loop in Onshape API, deadlock, unhandled exception that kills the event loop), there is no detection or recovery. The worker silently stops processing jobs. The dashboard may show the worker as "running" when it's actually stalled.

**Root Cause**: No health monitoring was implemented for the worker thread.

**Impact**: Silent export failures. Users discover the problem when they check the queue and see jobs stuck in "pending" state.

**Proposed Solution**:
1. Each worker thread writes a heartbeat timestamp to the database every tick
2. A watchdog (in the main thread or a separate lightweight thread) checks heartbeats every 30 seconds
3. If a worker's heartbeat is older than 2× the tick interval + grace period, the worker is considered stalled
4. The watchdog logs an error, emits an audit event, and attempts to restart the stalled worker
5. After 3 restart attempts, stop trying and alert the operator via notifications

**Priority**: High
**Difficulty**: Medium
**Dependencies**: Item 41 (the monitoring design must support multiple workers)
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/database.py`
**Estimated Effort**: 6 hours
**Risk**: Low — additive monitoring; does not change worker behavior
**Expected Improvement**: Stalled workers are detected and recovered automatically. Operators are alerted when auto-recovery fails.
**Status**: Proposed

---

### Item 43: Graceful Worker Shutdown

**Title**: Complete in-flight jobs before stopping the worker

**Problem**: When the worker is stopped (via web UI, CLI, or systemd), in-progress exports are abandoned. The job remains in RUNNING state indefinitely. There is no mechanism to complete the current job before shutting down.

**Root Cause**: Worker stop sets a flag, and the next tick check exits the loop immediately.

**Impact**: Abandoned jobs block the queue (RUNNING jobs are not re-claimed). Manual intervention is required to reset them to PENDING or FAILED.

**Proposed Solution**:
1. On stop signal, set a "draining" flag instead of stopping immediately
2. Complete the current in-flight job(s)
3. Do not claim new jobs
4. After all in-flight jobs complete (with a timeout), exit the worker thread
5. Mark any jobs that were RUNNING at shutdown and not completed as FAILED

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/worker.py`
**Estimated Effort**: 5 hours
**Risk**: Medium — shutdown logic is tricky; the timeout must prevent indefinite hangs
**Expected Improvement**: Clean worker shutdown. No abandoned RUNNING jobs.
**Status**: Proposed

---

### Item 44: Per-Worker Metrics

**Title**: Track throughput, error rate, and utilization per worker

**Problem**: The metrics system provides aggregate export statistics but cannot break them down by worker. With multiple workers (Item 41), it's impossible to tell if one worker is performing poorly.

**Root Cause**: Metrics were designed for a single-worker model.

**Impact**: Performance issues cannot be isolated to a specific worker. Load balancing effectiveness cannot be measured.

**Proposed Solution**: Add a `worker_id` field to export history entries and telemetry points. Track per-worker: jobs completed/hour, error rate, average job duration, current utilization. Expose via `/api/worker` and the dashboard.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: Item 41 (multi-worker support)
**Files Affected**: `onshape_export_manager/core/metrics.py`, `onshape_export_manager/core/database.py`, `onshape_export_manager/web.py`
**Estimated Effort**: 4 hours
**Risk**: Low — additive metrics
**Expected Improvement**: Visibility into per-worker performance. Ability to detect slow or stuck workers.
**Status**: Proposed

---

### Item 45: Per-Export Timeout Enforcement

**Title**: Kill exports that exceed their configured timeout

**Problem**: `config.json` has `export_timeout_seconds: 120`, but the worker does not enforce this. An export that hangs (waiting for a translation, stuck on a redirect loop) will block the worker indefinitely.

**Root Cause**: Timeout configuration was added but enforcement was not implemented.

**Impact**: A single hung export blocks all subsequent exports on that worker. With a single worker, the entire export pipeline stalls.

**Proposed Solution**: Wrap each export in `asyncio.wait_for()` with the configured timeout. On timeout, cancel the export task, mark the job as FAILED with a timeout reason, and move to the next job. The Onshape client's per-request timeout (30s) provides a lower-level safety net, but the export-level timeout catches multi-step pipeline hangs.

**Priority**: High
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/export_engine.py`
**Estimated Effort**: 2 hours
**Risk**: Low — additive safety measure
**Expected Improvement**: Hung exports no longer block the worker. The configured timeout is actually enforced.
**Status**: Proposed

---

### Item 46: Worker Pool Sizing Based on System Resources

**Title**: Auto-configure worker count based on available CPU cores and memory

**Problem**: `worker_count` is a static config value. On a Raspberry Pi 4 (4 cores, 4GB RAM), 4 workers might be appropriate. On a Raspberry Pi Zero (1 core, 512MB RAM), 4 workers would thrash. Users must know their hardware to configure this correctly.

**Root Cause**: Worker count was a simple config value without auto-detection.

**Impact**: Suboptimal performance on unknown hardware. Too many workers cause memory pressure; too few leave CPU idle.

**Proposed Solution**: If `worker_count` is set to 0 or "auto", detect available CPU cores and memory at startup and set a reasonable default (e.g., `min(cores, memory_gb * 2)`). Show the auto-detected value in the worker status page. Allow manual override via config.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/system_monitor.py`
**Estimated Effort**: 2 hours
**Risk**: Low — additive; manual config still works
**Expected Improvement**: Good default performance on any hardware without manual tuning.
**Status**: Proposed

---

### Item 47: Stuck Job Detection and Forced Cancellation

**Title**: Detect jobs that have been RUNNING for too long and force-cancel them

**Problem**: Even with per-export timeout (Item 45), a worker thread itself could hang in a way that `asyncio.wait_for()` cannot interrupt (e.g., blocking I/O in a C extension, a deadlocked lock). There is no mechanism to detect and recover from truly stuck jobs.

**Root Cause**: The worker's timeout enforcement assumes cooperative cancellation via asyncio, but not all code paths are cancellable.

**Impact**: A stuck job permanently claims a worker slot. With limited workers, this degrades throughput.

**Proposed Solution**: Track the `started_at` timestamp for RUNNING jobs. A separate watchdog (in the main thread) checks for jobs that have been RUNNING longer than `max_job_duration` (configurable, e.g., 10 minutes). Force-mark these jobs as FAILED with reason "timeout_hard". The stuck worker thread is restarted (leveraging Item 42's health monitoring).

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 42 (worker health monitoring provides the infrastructure)
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/queue_manager.py`
**Estimated Effort**: 4 hours
**Risk**: Medium — force-cancelling a job requires careful state management
**Expected Improvement**: Truly stuck jobs are eventually recovered without manual intervention.
**Status**: Proposed

---

## Phase 7: User Experience

> **Why Phase 7?** The application is correct (Phases 1-2), clean (Phases 3-4), functional (Phase 5), and reliable (Phase 6). Now it's time to make it delightful to use.

---

### Item 48: Configurable Keyboard Shortcuts

**Title**: Add a keyboard shortcuts system with a catalog page

**Problem**: Only the command palette (`⌘K`) has a keyboard shortcut. Other common actions (navigate to pages, create items, refresh data) require mouse interaction. Power users cannot operate the application efficiently via keyboard alone.

**Root Cause**: Keyboard shortcuts were only implemented for the command palette.

**Impact**: Slower workflows for power users. The application cannot be used keyboard-only (accessibility issue, also covered by Item 20).

**Proposed Solution**: Define a shortcut registry:
- `?` — Show keyboard shortcuts catalog (modal overlay)
- `g d` — Go to Dashboard
- `g q` — Go to Queue
- `g h` — Go to History
- `g s` — Go to Settings
- `n l` — New Label
- `n p` — New Profile
- `/` — Focus search/command palette
- `Esc` — Close modal / cancel action
Store shortcuts in `config.json` under `ui.keyboard_shortcuts` so users can customize them. Show available shortcuts in a ?-triggered modal.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 20 (keyboard accessibility)
**Files Affected**: `onshape_export_manager/ui/static/app.js`, `onshape_export_manager/ui/templates/base.html`
**Estimated Effort**: 6 hours
**Risk**: Low — additive feature
**Expected Improvement**: Power users can navigate and operate the application without touching the mouse.
**Status**: Proposed

---

### Item 49: Custom Theme Accent Colors and High-Contrast Mode

**Title**: Allow users to customize the UI accent color and enable a high-contrast accessibility theme

**Problem**: The UI has a single fixed color scheme (blue accent on dark background). Users cannot customize colors, and there is no high-contrast mode for visually impaired users.

**Root Cause**: The theme system was built with a dark/light toggle but no further customization.

**Impact**: No personalization. Visually impaired users may struggle with the default contrast levels.

**Proposed Solution**:
1. Add `accent_color` to `config.json` under `ui` with a set of predefined options (blue, green, purple, orange, red)
2. Generate CSS custom properties for the accent color palette
3. Add a "High Contrast" theme toggle that increases text contrast, adds visible focus rings, and enlarges touch targets
4. Persist theme preferences per-user in `localStorage`

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/ui/static/styles.css`, `onshape_export_manager/ui/static/app.js`, `onshape_export_manager/core/configuration.py`
**Estimated Effort**: 5 hours
**Risk**: Low — additive CSS changes
**Expected Improvement**: Personalized appearance. Better accessibility for visually impaired users.
**Status**: Proposed

---

### Item 50: Dashboard Widget Customization

**Title**: Allow users to reorder, show, and hide dashboard widgets

**Problem**: The dashboard layout is fixed. All users see the same stat cards, charts, and tables in the same order, regardless of what's relevant to their workflow.

**Root Cause**: The dashboard was designed as a single static layout.

**Impact**: Users scroll past irrelevant widgets to find what they need. The dashboard feels cluttered to users who only care about a few metrics.

**Proposed Solution**: Add a "Customize" button to the dashboard that enters edit mode. In edit mode, widgets can be dragged to reorder and toggled on/off. Persist layout to `localStorage`. Default layout remains the current one.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: Items 17, 18
**Files Affected**: `onshape_export_manager/ui/templates/dashboard.html`, `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 8 hours
**Risk**: Low — additive; default layout unchanged
**Expected Improvement**: Dashboard shows only what's relevant to each user.
**Status**: Proposed

---

### Item 51: Real-Time Per-File Export Progress

**Title**: Stream per-file export progress to the dashboard via WebSocket

**Problem**: During a manual export, the UI shows a spinner and "Export queued" message. There is no progress indication — the user doesn't know which document is being processed, how many files have been exported, or how many remain.

**Root Cause**: The export engine runs synchronously and reports only a final summary.

**Impact**: Poor user experience during long exports. Users wonder if the export is still running or has stalled.

**Proposed Solution**: Emit events on the EventBus as each document and file is exported (e.g., `EXPORT_FILE_STARTED`, `EXPORT_FILE_COMPLETED`, `EXPORT_FILE_FAILED`). The WebSocket handler already streams events to the activity page — expand it to include a per-job progress topic. The manual export page subscribes to progress events for its job and renders a progress bar with file-by-file status.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None (EventBus already exists; just add events)
**Files Affected**: `onshape_export_manager/core/export_engine.py`, `onshape_export_manager/core/events.py`, `onshape_export_manager/ui/templates/section.html`, `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 6 hours
**Risk**: Low — additive events; existing behavior unchanged
**Expected Improvement**: Users can see export progress in real time. No more "is it still working?" uncertainty.
**Status**: Proposed

---

### Item 52: Bulk Import/Export of Settings

**Title**: Allow exporting all configuration as a single portable JSON file and importing it on another instance

**Problem**: Setting up a new instance requires manually recreating labels, profiles, accounts, and settings. There is no way to migrate configuration between instances (e.g., from a development Pi to a production Pi).

**Root Cause**: No settings import/export was implemented.

**Impact**: Tedious manual setup for new instances. No backup of configuration separate from the full ZIP backup (which includes database and logs).

**Proposed Solution**: Add endpoints:
- `GET /api/settings/export` — Returns a single JSON file containing all config data (accounts, labels, profiles, organizations, app settings). Secrets are masked.
- `POST /api/settings/import` — Accepts a JSON file and merges it into the current configuration. Validate before applying. Show a diff/preview before confirming.
Add corresponding CLI commands: `--export-settings PATH` and `--import-settings PATH`.

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/cli.py`, `onshape_export_manager/core/configuration.py`
**Estimated Effort**: 5 hours
**Risk**: Medium — import must be careful not to corrupt existing config; preview/diff step is essential
**Expected Improvement**: Easy migration between instances. Portable configuration backup.
**Status**: Proposed

---

### Item 53: Undo Support for Destructive Actions

**Title**: Add undo capability for delete and cancel operations

**Problem**: Deleting a label, organization, notification channel, or export profile is immediate and irreversible. Cancelling a queue job cannot be undone. Users who click the wrong button have no recovery path.

**Root Cause**: No undo infrastructure was built.

**Impact**: Accidental deletions cause data loss and frustration. Users become hesitant to use the UI.

**Proposed Solution**: Implement a toast-based undo system:
1. When a destructive action is performed, show a toast: "Label 'X' deleted. [Undo]" with a 10-second timeout
2. Clicking "Undo" restores the deleted item
3. After the timeout, the deletion is permanent
4. This requires soft-delete: mark items as deleted but don't remove them until the undo window expires
5. A background task cleans up soft-deleted items after the undo window

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Items 18, 19 (toast component must exist)
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/ui/static/app.js`, `onshape_export_manager/core/configuration.py`
**Estimated Effort**: 8 hours
**Risk**: Medium — soft-delete adds complexity to query logic (must filter out soft-deleted items)
**Expected Improvement**: No more irreversible mistakes. Users can confidently use the UI.
**Status**: Proposed

---

### Item 54: Guided Onboarding Tour

**Title**: Replace the bare setup wizard with an interactive guided tour

**Problem**: The setup wizard (`wizard.html`) is a 9-step form that collects owner credentials and storage configuration. It's functional but unguided — users see one form after another without context about what the application does or why each step matters.

**Root Cause**: The wizard was built as a minimal viable setup flow.

**Impact**: New users may not understand what they're configuring or why. The setup feels like paperwork rather than onboarding.

**Proposed Solution**: Replace the linear wizard with an interactive tour:
1. Welcome screen explaining what Onshape Export Manager does
2. Each step includes a brief explanation of WHY this configuration matters
3. Illustrations or diagrams for key concepts (labels, profiles, organizations)
4. Progress indicator showing where the user is in the setup
5. "Skip for now" options where sensible defaults exist
6. After setup, show a quick tour of the dashboard highlighting key areas

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/ui/templates/wizard.html`, `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 10 hours
**Risk**: Low — additive; existing wizard continues to work
**Expected Improvement**: New users understand the application within minutes. Reduced support burden.
**Status**: Proposed

---

### Item 55: Mobile-Responsive Layout

**Title**: Make the sidebar, tables, and dashboard responsive for mobile viewports

**Problem**: The application assumes a desktop viewport. On phones and tablets, the sidebar obscures content, tables overflow horizontally with no scroll indicator, and the dashboard widget grid becomes a single narrow column.

**Root Cause**: The UI was designed for desktop use (the app typically runs on a local network accessed from a desktop browser).

**Impact**: Unusable on mobile devices. Users who want to check export status from their phone cannot.

**Proposed Solution**:
1. Collapse the sidebar into a hamburger menu on viewports < 768px
2. Add horizontal scroll with visual indicators to data tables
3. Restack dashboard widgets into a single column on narrow viewports
4. Increase touch target sizes (minimum 44px) for mobile
5. Test on common phone and tablet viewport sizes

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: Item 17 (responsive design is easier with a build step and CSS organization)
**Files Affected**: `onshape_export_manager/ui/static/styles.css`, `onshape_export_manager/ui/templates/base.html`, `onshape_export_manager/ui/templates/dashboard.html`
**Estimated Effort**: 8 hours
**Risk**: Low — additive CSS changes; desktop layout unchanged
**Expected Improvement**: Usable on phones and tablets. Users can check export status from anywhere.
**Status**: Proposed

---

## Phase 8: Performance

> **Why Phase 8?** Performance optimization before the feature set is complete leads to premature optimization — optimizing code that later changes. Phase 8 comes after the feature set is stable (Phase 5) and the worker is reliable (Phase 6), so optimization effort is not wasted.

---

### Item 56: Server-Side Document Filtering

**Title**: Push label and date filtering to the Onshape API instead of client-side fetch-all

**Problem**: `fetch_documents_by_label()` loads ALL visible documents from Onshape, then filters by label and date range locally. For an organization with thousands of documents, this is O(n) in document count and wastes API quota and bandwidth.

**Root Cause**: The Onshape API's `?label=` query parameter was found to be unreliable during prototyping, so filtering was done client-side as a workaround.

**Impact**: Slow exports for organizations with many documents. Wasted API quota. The Onshape API may throttle or timeout on large responses.

**Proposed Solution**: Revisit the Onshape API's label filtering. If the API issue was specific to a version that has since been fixed, use server-side filtering. If not, implement paginated fetching with early termination (stop fetching pages once documents are older than the date range). Cache the document list with a short TTL to avoid re-fetching on every export.

**Priority**: High
**Difficulty**: Hard
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/onshape_client.py`
**Estimated Effort**: 8 hours
**Risk**: Medium — changes to Onshape API interaction require testing against the live API
**Expected Improvement**: Dramatically faster exports for organizations with large document counts. Reduced API quota usage.
**Status**: Proposed

---

### Item 57: Single-Query Queue Stats

**Title**: Replace 5 separate SQL queries for queue stats with a single GROUP BY query

**Problem**: `QueueManager.stats()` queries the queue table once per `JobStatus` value (5 queries), each opening a new database connection. A single `SELECT status, COUNT(*) FROM queue GROUP BY status` would return the same data.

**Root Cause**: The stats method was written to iterate over statuses and count each one, without considering SQL aggregation.

**Impact**: Unnecessary database overhead. Each dashboard refresh triggers 5 queue queries.

**Proposed Solution**: Replace the per-status counting with a single GROUP BY query. Handle the case where some statuses have zero entries (the GROUP BY query won't include them).

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/queue_manager.py`, `onshape_export_manager/core/database.py`
**Estimated Effort**: 1 hour
**Risk**: Low — behavior unchanged
**Expected Improvement**: 5× fewer database queries for queue stats. Faster dashboard loading.
**Status**: Proposed

---

### Item 58: Export Engine Config Caching

**Title**: Cache loaded configuration in the export engine with TTL and explicit invalidation

**Problem**: `_build_request()` in `worker.py` calls `config_manager.load()` on every single job, reading and parsing all five JSON config files from disk. This is redundant — config rarely changes between jobs.

**Root Cause**: The worker was written to always get fresh config rather than implementing a caching strategy.

**Impact**: Unnecessary disk I/O and JSON parsing. For a burst of 50 queued jobs, 50 full config reloads.

**Proposed Solution**: Cache the loaded config in the worker with a short TTL (e.g., 5 seconds). On config file change (detected by Item 5's file watcher), invalidate the cache. The worker checks cache validity before loading. This preserves correctness (config changes are picked up within 5 seconds) while eliminating redundant loads.

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 5 (config change detection provides invalidation trigger)
**Files Affected**: `onshape_export_manager/core/worker.py`, `onshape_export_manager/core/configuration.py`
**Estimated Effort**: 2 hours
**Risk**: Low — caching with invalidation; correctness is preserved
**Expected Improvement**: Near-zero config load overhead for burst exports.
**Status**: Proposed

---

### Item 59: SQLite Connection Reuse

**Title**: Reuse database connections across requests instead of opening a new connection per call

**Problem**: Every `Database` method opens a new SQLite connection via the `connect()` context manager, executes one query, and closes it. While SQLite connections are cheap, the overhead adds up under load — especially for the dashboard, which makes many small queries.

**Root Cause**: The context manager pattern was chosen for simplicity and correctness.

**Impact**: Slightly higher latency for multi-query operations. More file descriptor churn.

**Proposed Solution**: Add an optional connection pool or single reusable connection for read queries. Keep the context manager for write operations (which need transaction boundaries). Use WAL mode's concurrent read capability to allow multiple readers on a shared connection. This is a modest optimization — SQLite on a local SSD is already fast — but it reduces overhead on Raspberry Pi SD cards where I/O is slower.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `onshape_export_manager/core/database.py`
**Estimated Effort**: 4 hours
**Risk**: Medium — connection management must be correct; SQLite's threading model requires careful handling
**Expected Improvement**: Modest latency reduction for dashboard queries on slow storage.
**Status**: Proposed

---

### Item 60: Frontend Asset Bundling and Caching

**Title**: Bundle, minify, and add content-hash cache busting to frontend assets

**Problem**: `app.js` and `styles.css` are served as-is with a simple `?v={{ asset_version }}` cache buster. There is no minification, no compression, and no content-hash based cache invalidation. Browsers may serve stale assets if the version string isn't updated.

**Root Cause**: The asset pipeline was built for development convenience, not production performance.

**Impact**: Larger-than-necessary file sizes. Potential for stale asset caching. No Brotli or Gzip compression.

**Proposed Solution**:
1. Use the build step (Item 17) to minify JS and CSS
2. Generate content hashes for output filenames (`app.a1b2c3d.js`)
3. Update `asset_version` to use content hashes automatically
4. Configure Uvicorn to serve static files with `Cache-Control: public, max-age=31536000, immutable` for hashed assets
5. Enable Gzip middleware in FastAPI

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: Item 17 (build step)
**Files Affected**: `ui/package.json`, `onshape_export_manager/web.py`
**Estimated Effort**: 3 hours
**Risk**: Low — build output only; development workflow unchanged
**Expected Improvement**: Smaller, cacheable assets. No stale cache issues.
**Status**: Proposed

---

### Item 61: Database Query Result Pagination

**Title**: Add pagination to large data queries (history, events, queue)

**Problem**: `/api/history` returns up to 500 entries with `?limit=`. `/api/events` returns up to 200 entries. There is no offset-based or cursor-based pagination. For long-running instances, 500 entries may represent only a fraction of the data, but loading more is not supported.

**Root Cause**: The API was designed for small datasets without pagination.

**Impact**: Users cannot browse beyond the most recent entries. The API cannot efficiently serve large datasets.

**Proposed Solution**: Add cursor-based pagination (more efficient than offset for SQLite) to history, events, and queue endpoints:
- Response includes `next_cursor` and `has_more` fields
- Client passes `?cursor=...` to get the next page
- Limit defaults to 100, max 1000
- The frontend implements "Load More" buttons or infinite scroll

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 12 (standardized response envelope for pagination metadata)
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/core/database.py`, `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 6 hours
**Risk**: Low — additive; existing behavior preserved for first page
**Expected Improvement**: Users can browse complete history, not just recent entries.
**Status**: Proposed

---

### Item 62: Lazy-Load Page Sections

**Title**: Load dashboard sections on demand instead of all at once

**Problem**: `GET /api/metrics` returns the full dashboard payload including summary, activity time series, account health, queue stats, recent history, disk usage, and format definitions — all in one response. The dashboard page loads everything on mount, even sections the user may not scroll to.

**Root Cause**: The metrics endpoint was designed for simplicity: one request, all data.

**Impact**: Slower initial dashboard load. Unnecessary database and filesystem queries for sections the user never views.

**Proposed Solution**: Split the metrics endpoint into individual section endpoints:
- `/api/metrics/summary` — Always loaded (lightweight)
- `/api/metrics/activity` — Loaded when the activity chart scrolls into view
- `/api/metrics/accounts` — Loaded when the account health section scrolls into view
- etc.
Use Intersection Observer in the frontend to trigger loading as sections become visible.

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: Items 17, 18 (modular frontend)
**Files Affected**: `onshape_export_manager/web.py`, `onshape_export_manager/core/metrics.py`, `onshape_export_manager/ui/static/app.js`
**Estimated Effort**: 8 hours
**Risk**: Low — additive; the single endpoint can still exist for backward compatibility
**Expected Improvement**: Faster initial dashboard render. Fewer unnecessary queries.
**Status**: Proposed

---

## Phase 9: Testing

> **Why Phase 9?** Comprehensive testing after interfaces stabilize (Phases 2-4) prevents writing tests that break during refactoring. The application's behavior is now well-defined, making tests valuable and durable.

---

### Item 63: Full CLI Integration Tests

**Title**: Add integration tests for all CLI commands

**Problem**: `test_cli.py` has only two tests: `parse_cli_datetime()` and `export_window()` date validation. None of the 20+ CLI commands are tested. This is the single largest testing gap in the project.

**Root Cause**: CLI testing was deferred during development.

**Impact**: CLI regressions go undetected. The CLI is the primary interface for headless deployments — bugs here have high impact.

**Proposed Solution**: Write integration tests for every CLI command:
- `--version` — prints version
- `--init` — creates directory structure and default configs
- `--init-config` — creates missing config files only
- `--init-db` — initializes database
- `--validate-config` — validates all configs, reports errors
- `--database-status` — shows schema version and table counts
- `--accounts-status` — shows account health
- `--queue-status` — shows queue counts
- `--scheduler-status` — shows scheduler state
- `--list-export-formats` — lists all formats
- `--list-export-profiles` — lists configured profiles
- `--run-export LABEL` — runs a manual export end-to-end
- `--add-export-profile` — creates a new profile
- `--run-worker` — starts worker (test by running briefly with mocked Onshape)
- `--drain-once` — processes one batch of queue items
Each test should use `tempfile.TemporaryDirectory` and `subprocess.run()` to invoke the CLI, then verify filesystem and database state.

**Priority**: High
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `tests/test_cli.py` (significant expansion)
**Estimated Effort**: 12 hours
**Risk**: Low — tests are additive; they don't change application behavior
**Expected Improvement**: CLI regressions caught before release. Confidence in headless deployment path.
**Status**: Proposed

---

### Item 64: SSE Streaming Endpoint Tests

**Title**: Add integration tests for the `/api/stream` SSE endpoint

**Problem**: The SSE streaming endpoint for live dashboard updates is not tested. SSE is tricky to test because it's a long-lived connection that streams multiple events.

**Root Cause**: SSE testing was deferred as "hard to test."

**Impact**: SSE regressions (connection drops, format errors, missing events) go undetected.

**Proposed Solution**: Use `httpx` streaming client in tests:
1. Connect to `/api/stream` with `httpx.stream("GET", ...)`
2. Read the first few SSE events
3. Assert event format (`data: {...}\n\n`)
4. Assert event content (summary fields are present)
5. Assert reconnection via `Last-Event-Id`
6. Test that SSE continues to stream after a config change

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: `tests/test_web_api.py` (add SSE test cases)
**Estimated Effort**: 4 hours
**Risk**: Low — additive tests
**Expected Improvement**: SSE endpoint is verified to work correctly.
**Status**: Proposed

---

### Item 65: Concurrency Tests

**Title**: Add tests for concurrent queue access, pool leasing, and worker scenarios

**Problem**: There are no tests for concurrent behavior: multiple workers claiming from the same queue, simultaneous API pool leasing, WebSocket events during worker activity. These are the scenarios most likely to expose race conditions.

**Root Cause**: Concurrency testing is harder than sequential testing and was deferred.

**Impact**: Race conditions (like the TOCTOU in queue claiming) go undetected until they cause production bugs.

**Proposed Solution**: Write tests using `threading` or `asyncio.gather()`:
1. Two workers simultaneously claiming queue items (verifies Item 1 fix)
2. Worker recording API results while dashboard queries account health (verifies Item 2 fix)
3. Multiple concurrent SSE or WebSocket connections
4. Config file change during active export
5. Rapid start/stop of worker
Use `time.sleep(0)` / `asyncio.sleep(0)` to interleave operations deterministically where possible.

**Priority**: High
**Difficulty**: Hard
**Dependencies**: Items 1, 2, 3 (fixes being tested)
**Files Affected**: New `tests/test_concurrency.py`
**Estimated Effort**: 12 hours
**Risk**: Low — additive tests
**Expected Improvement**: Race conditions caught in CI, not in production.
**Status**: Proposed

---

### Item 66: Real Onshape API Smoke Tests

**Title**: Add optional smoke tests against the live Onshape API

**Problem**: All tests use mock Onshape clients. There is no verification that the application actually works against the real Onshape API. API changes, authentication format changes, or endpoint deprecations are not detected.

**Root Cause**: Testing against a live API requires credentials and network access, which CI environments may not have.

**Impact**: The application may break due to Onshape API changes with no warning.

**Proposed Solution**: Add a `pytest` marker `@pytest.mark.integration` for tests that require live Onshape credentials. Tests should:
1. Verify authentication (list documents)
2. Fetch a known label's documents
3. Export a known Part Studio in each format
4. Verify downloaded files are valid (not HTML error pages, correct file size)
Run these tests manually or in a scheduled CI job, not on every commit. Skip them gracefully if `ONSHAPE_ACCESS_KEY` environment variable is not set.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New `tests/test_onshape_integration.py`
**Estimated Effort**: 6 hours
**Risk**: Low — tests are optional and don't run in normal CI
**Expected Improvement**: Onshape API compatibility verified before releases.
**Status**: Proposed

---

### Item 67: pytest Fixtures and Parametrize Migration

**Title**: Migrate tests from `unittest.TestCase` to pytest-native style with fixtures

**Problem**: Despite requiring `pytest>=8.2`, all tests use `unittest.TestCase` patterns: `self.assertEqual()`, `self.assertRaises()`, `setUp()`/`tearDown()`. There are no pytest fixtures, no `@pytest.mark.parametrize`, no `conftest.py`. The project is using pytest as a test runner, not as a test framework.

**Root Cause**: Tests were initially written with unittest patterns (familiar to many developers) and never migrated.

**Impact**: Test code is more verbose than necessary. Common setup (temp directories, database initialization, app creation) is duplicated across test files. Parametrized test cases (e.g., testing all export formats) are written as loops inside test methods instead of declarative parametrize.

**Proposed Solution**:
1. Create `tests/conftest.py` with shared fixtures: `temp_dir`, `app_paths`, `config_manager`, `database`, `event_bus`, `application`
2. Convert test classes to functions using fixtures
3. Replace loops with `@pytest.mark.parametrize` (e.g., `@pytest.mark.parametrize("format", ExportFormat)`)
4. Use `pytest.raises()` instead of `self.assertRaises()`
5. This is a progressive migration — old tests and new tests can coexist during the transition

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: All `tests/*.py` files, new `tests/conftest.py`
**Estimated Effort**: 16 hours
**Risk**: Low — tests should pass identically; behavior not changed
**Expected Improvement**: Less test boilerplate. Better test isolation. Easier to add new tests.
**Status**: Proposed

---

### Item 68: Test Coverage Enforcement

**Title**: Add coverage measurement and enforce minimum coverage thresholds

**Problem**: There is no coverage measurement. Developers don't know which code paths are tested and which are not. Untested modules (`bambu.py`, `plugins.py`, `security.py`) have no visibility.

**Root Cause**: Coverage was not set up in the project tooling.

**Impact**: Untested code accumulates without awareness. Regressions in uncovered paths are not caught.

**Proposed Solution**:
1. Add `pytest-cov` to dev dependencies
2. Configure `.coveragerc` to exclude test files, migrations, and `__init__.py`
3. Add `--cov=onshape_export_manager --cov-report=term --cov-report=html` to the test command
4. Set minimum coverage thresholds: 80% line coverage overall, 60% per-module minimum
5. Fail CI if coverage drops below threshold (Item 71)
6. Start tracking coverage trends over time

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 71 (CI pipeline)
**Files Affected**: `requirements.txt`, `.coveragerc`, CI config
**Estimated Effort**: 2 hours
**Risk**: Low — additive tooling
**Expected Improvement**: Visibility into test coverage. Incentive to test new code.
**Status**: Proposed

---

### Item 69: Property-Based Testing

**Title**: Add property-based tests for retry policy, scheduler intervals, and format parsing

**Problem**: Retry backoff, schedule interval parsing, and format name parsing are tested with a few hand-picked examples. Edge cases (unusual interval strings, boundary conditions on retry counts, unusual format names) are not systematically explored.

**Root Cause**: Example-based testing was used exclusively.

**Impact**: Edge case bugs in core algorithms may go undetected.

**Proposed Solution**: Add property-based tests using `hypothesis`:
- Retry policy: for any attempt count, `delay >= base` and `delay <= max`
- Scheduler intervals: for any valid interval string, `parse_interval()` returns a known value
- Format parsing: for any valid format list string, parsing produces a valid list of `ExportFormat` values
- Retry decisions: for any HTTP status, `retry_decision()` is consistent with `is_retryable_http_status()`

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New tests or additions to `test_retry.py`, `test_scheduler.py`, `test_profile_manager.py`
**Estimated Effort**: 6 hours
**Risk**: Low — additive tests; hypothesis may find bugs in existing code
**Expected Improvement**: Edge case bugs in core algorithms caught automatically.
**Status**: Proposed

---

### Item 70: End-to-End Test

**Title**: Add a full end-to-end test: CLI init → web start → manual export → verify files

**Problem**: There is no test that exercises the entire application workflow end to end. Integration tests cover individual components; unit tests cover individual functions. But no test verifies that a user can initialize the application, start the web server, configure a label, run an export, and find files on disk.

**Root Cause**: End-to-end tests are complex to set up and slow to run.

**Impact**: Integration bugs between components (config → export engine → folder manager, or web → queue → worker → filesystem) are only caught by manual testing.

**Proposed Solution**: Write a single end-to-end test that:
1. Runs `--init` in a temp directory
2. Starts the web server on a random port
3. Uses `httpx` to create an organization, credential, label, and export profile
4. Triggers a manual export
5. Waits for the worker to process the job (poll `/api/queue`)
6. Verifies exported files exist on disk with correct format extensions
7. Verifies export history entry is created
Use a fake Onshape client to avoid needing real API credentials. This test will be slow (~5-10 seconds) and should be marked with `@pytest.mark.slow`.

**Priority**: Medium
**Difficulty**: Hard
**Dependencies**: Items 63-69 (other testing improvements)
**Files Affected**: New `tests/test_end_to_end.py`
**Estimated Effort**: 8 hours
**Risk**: Low — additive test
**Expected Improvement**: Confidence that the full application workflow works. Catches integration bugs.
**Status**: Proposed

---

## Phase 10: Production Readiness

> **Why Phase 10?** The application is correct, clean, functional, reliable, delightful, performant, and well-tested. Phase 10 wraps it in the operational tooling needed for real-world deployment and ongoing maintenance.

---

### Item 71: GitHub Actions CI/CD Pipeline

**Title**: Set up continuous integration with linting, type checking, testing, and building

**Problem**: There is no CI/CD pipeline. Code is tested manually by developers. There is no automated verification that commits pass tests, no linting enforcement, no type checking, and no build verification.

**Root Cause**: CI/CD was not set up during initial development.

**Impact**: Bugs reach the main branch that would be caught by automated checks. Code style drifts without enforcement. No confidence that the application builds and tests pass on a clean environment.

**Proposed Solution**: Create `.github/workflows/ci.yml`:
- **Lint**: Run `ruff` (or `flake8` + `isort`) on all Python files
- **Type check**: Run `mypy` on the codebase (start with lenient settings, tighten over time)
- **Test**: Run `pytest` with coverage on Python 3.12, 3.13
- **Build**: Verify that the application can be installed from `requirements.txt`
- Run on every push to `main` and every pull request
- Cache pip dependencies and test artifacts

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 68 (coverage configuration)
**Files Affected**: New `.github/workflows/ci.yml`, `.github/dependabot.yml`
**Estimated Effort**: 6 hours
**Risk**: Low — additive; does not change application code
**Expected Improvement**: Automated quality gates. Bugs caught before merge. Consistent code style.
**Status**: Proposed

---

### Item 72: Docker Containerization

**Title**: Create a multi-architecture Docker image (amd64 + arm64 for Raspberry Pi)

**Problem**: Installation requires Python 3.12+, pip, and manual setup. There is no containerized deployment option. Users who run other services in Docker cannot easily add this application to their stack.

**Root Cause**: The application was designed for bare-metal Raspberry Pi deployment. Docker was not a priority.

**Impact**: Higher barrier to entry for Docker users. No easy way to run the application in container orchestration (Docker Compose, Kubernetes, Portainer).

**Proposed Solution**: Create `Dockerfile`:
- Multi-stage build: builder stage installs dependencies, runtime stage is minimal
- Based on `python:3.12-slim` for amd64, `python:3.12-slim-bookworm` for arm64
- Expose port 8000
- Volume mounts for `/app/config`, `/app/exports`, `/app/database`, `/app/logs`, `/app/backups`
- Entrypoint runs the web server
- Create `docker-compose.yml` for easy local deployment with persistent volumes
- Build multi-arch images with `docker buildx`
- Publish to GitHub Container Registry

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New `Dockerfile`, `docker-compose.yml`, `.dockerignore`
**Estimated Effort**: 8 hours
**Risk**: Low — additive; bare-metal installation still supported
**Expected Improvement**: One-command deployment for Docker users. Multi-arch support for both x86 and ARM.
**Status**: Proposed

---

### Item 73: Database Migration Integration Tests

**Title**: Test database migrations from v1 → v2 → v3 with real data

**Problem**: Database schema migrations are tested by creating a fresh database at each version. There is no test that starts with a v1 database containing real data, migrates through v2 to v3, and verifies data integrity at each step.

**Root Cause**: Migration testing was done manually during development.

**Impact**: A migration bug could corrupt existing user databases during an upgrade.

**Proposed Solution**: Create test fixtures representing databases at each schema version with realistic data (export history, queue entries, scheduler jobs, application state). Write tests that:
1. Open the v1 fixture database
2. Run migration to v2
3. Verify all v1 data is intact and v2 schema additions exist
4. Run migration to v3
5. Verify all data is intact through both migrations
6. Verify indices and constraints are correct

**Priority**: High
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New `tests/test_migrations.py`, test fixture databases in `tests/fixtures/`
**Estimated Effort**: 6 hours
**Risk**: Low — additive tests
**Expected Improvement**: Confidence that upgrades won't corrupt user databases.
**Status**: Proposed

---

### Item 74: Anonymous Telemetry Opt-In

**Title**: Add optional, anonymous usage telemetry with explicit opt-in

**Problem**: The development team has no data about how the application is used: which features are popular, which export formats are most common, what error rates look like in the field, what hardware the application runs on. Decisions about what to improve are based on assumptions.

**Root Cause**: Telemetry was not a priority for an early-stage project.

**Impact**: Development priorities may not align with actual user needs. Bugs that affect many users may go unnoticed.

**Proposed Solution**: Implement an opt-in telemetry system:
1. On first run (setup wizard), explicitly ask: "Help improve Onshape Export Manager by sending anonymous usage data?" [Yes] [No]
2. If opted in, periodically send: application version, OS, Python version, Raspberry Pi model (if applicable), number of accounts/labels/profiles, export counts by format, error rates, feature usage (which pages are visited)
3. NEVER send: API keys, document names, file contents, IP addresses, or any personally identifiable information
4. Use a simple HTTPS POST to a telemetry endpoint
5. Show exactly what data is being sent in the Settings page
6. Allow opt-out at any time
7. Respect `DO_NOT_TRACK` environment variable

**Priority**: Low
**Difficulty**: Medium
**Dependencies**: None
**Files Affected**: New `onshape_export_manager/core/telemetry.py` (replaces/extends metrics), `onshape_export_manager/web.py`, setup wizard
**Estimated Effort**: 8 hours
**Risk**: Medium — telemetry is politically sensitive; must be transparent, minimal, and genuinely optional
**Expected Improvement**: Data-driven development decisions. Understanding of real-world usage patterns.
**Status**: Proposed

---

### Item 75: Cross-Platform CI Matrix

**Title**: Test on macOS, Ubuntu, and Raspberry Pi OS in CI

**Problem**: Tests run only on the developer's machine (macOS). There is no verification that the application works on Linux (the primary deployment target) or Raspberry Pi OS (the primary hardware target).

**Root Cause**: Multi-platform CI was not set up.

**Impact**: Platform-specific bugs (path handling, subprocess behavior, filesystem permissions, `/proc` vs `psutil` fallbacks) are not caught before release.

**Proposed Solution**: Extend the CI pipeline (Item 71) to run tests on:
- `ubuntu-latest` (GitHub Actions runner, x86_64)
- `macos-latest` (GitHub Actions runner)
- Raspberry Pi OS via Docker emulation (`arm64v8/python:3.12-slim` with QEMU)
Run the full test suite on each platform. Mark platform-specific tests with appropriate skip conditions.

**Priority**: Medium
**Difficulty**: Medium
**Dependencies**: Item 71 (CI pipeline), Item 72 (Docker image for ARM emulation)
**Files Affected**: `.github/workflows/ci.yml`
**Estimated Effort**: 4 hours
**Risk**: Low — additive CI configuration
**Expected Improvement**: Platform-specific bugs caught before release. Confidence in cross-platform compatibility.
**Status**: Proposed

---

### Item 76: Pre-Commit Hooks

**Title**: Add pre-commit hooks for formatting, linting, and type checking

**Problem**: Developers can commit code that fails tests, has syntax errors, violates style conventions, or has type errors without any automated gate. Code review must catch these issues manually.

**Root Cause**: Pre-commit hooks were not configured in the repository.

**Impact**: Inconsistent code style. Time wasted in code review on mechanical issues. Bugs from untyped code.

**Proposed Solution**: Add `.pre-commit-config.yaml` with hooks:
- `ruff` (or `black` + `isort` + `flake8`) — Code formatting and linting
- `mypy` — Type checking (with lenient initial config)
- `check-yaml`, `check-json`, `check-toml` — Config file validation
- `end-of-file-fixer`, `trailing-whitespace` — Whitespace hygiene
- `detect-private-key` — Prevent accidentally committing secrets
- `pytest` — Run fast tests (not the full suite, just quick checks)

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 71 (CI should also run these checks)
**Files Affected**: New `.pre-commit-config.yaml`
**Estimated Effort**: 2 hours
**Risk**: Low — additive tooling; developers opt in by running `pre-commit install`
**Expected Improvement**: Consistent code style. Fewer mechanical issues in code review. Secrets never committed.
**Status**: Proposed

---

### Item 77: Semantic Versioning and Automated Changelog

**Title**: Adopt semantic versioning and generate changelogs from conventional commits

**Problem**: The version is hardcoded as `0.1.0` in `__init__.py`. There is no changelog, no release process, and no versioning strategy. Users don't know what changed between versions.

**Root Cause**: The project is pre-release and versioning was not formalized.

**Impact**: Users cannot determine if an update contains breaking changes. No release notes for operators to review before upgrading.

**Proposed Solution**:
1. Adopt [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH
2. Adopt [Conventional Commits](https://www.conventionalcommits.org): `feat:`, `fix:`, `docs:`, `refactor:`, etc.
3. Use `commitizen` or `semantic-release` to:
   - Validate commit messages in pre-commit hooks
   - Bump version automatically based on commit types
   - Generate `CHANGELOG.md` from commit history
4. Add a release workflow to CI that publishes a GitHub Release with the changelog

**Priority**: Low
**Difficulty**: Easy
**Dependencies**: Item 71 (CI pipeline), Item 76 (pre-commit hooks)
**Files Affected**: `onshape_export_manager/__init__.py`, new `CHANGELOG.md`, `.github/workflows/release.yml`
**Estimated Effort**: 4 hours
**Risk**: Low — additive process change
**Expected Improvement**: Clear version semantics. Automated release notes. Professional release process.
**Status**: Proposed

---

### Item 78: Security Vulnerability Scanning

**Title**: Add automated vulnerability scanning for dependencies

**Problem**: Python dependencies (`requests`, `fastapi`, `uvicorn`, `jinja2`, `pydantic`, `cryptography`) may have known vulnerabilities. There is no automated scanning to detect them.

**Root Cause**: Vulnerability scanning was not set up.

**Impact**: Known vulnerabilities in dependencies go unnoticed. Users may be running insecure versions.

**Proposed Solution**:
1. Add `pip-audit` to CI (Item 71) to scan for known vulnerabilities in Python packages
2. Enable Dependabot on GitHub for automated dependency update PRs
3. Configure Dependabot to check `requirements.txt` weekly
4. Add a `SECURITY.md` with vulnerability reporting instructions
5. Consider adding `bandit` for static security analysis of the application code

**Priority**: Medium
**Difficulty**: Easy
**Dependencies**: Item 71 (CI pipeline)
**Files Affected**: `.github/workflows/ci.yml`, `.github/dependabot.yml`, new `SECURITY.md`
**Estimated Effort**: 2 hours
**Risk**: Low — additive scanning
**Expected Improvement**: Known vulnerabilities detected and flagged automatically. Dependencies kept up to date.
**Status**: Proposed

---

## Summary

| Phase | Items | Focus | Effort (hours) |
|---|---|---|---|
| 1 | 8 | Critical Architectural Fixes | 26 |
| 2 | 8 | Backend Redesign | 68 |
| 3 | 8 | Frontend Redesign | 73 |
| 4 | 8 | Domain Cleanup | 47 |
| 5 | 8 | Core Functionality | 79 |
| 6 | 7 | Worker Improvements | 45 |
| 7 | 8 | User Experience | 55 |
| 8 | 7 | Performance | 42 |
| 9 | 8 | Testing | 63 |
| 10 | 8 | Production Readiness | 42 |
| **Total** | **78** | | **~540 hours** |

**Total estimated effort**: ~540 developer-hours (approximately 13-14 weeks for a single full-time developer, or 4-5 weeks for a team of three).

### Priority Breakdown
- **Critical**: 4 items (Items 1, 2, 3, 6) — Must fix before any production use
- **High**: 13 items — Should fix before recommending to others
- **Medium**: 39 items — Should fix before considering the project "complete"
- **Low**: 22 items — Nice to have; can be deferred indefinitely

### Risk Profile
- **Hard** difficulty items have the highest risk and should be tackled by experienced developers
- **Medium** difficulty items have moderate risk and can be handled by developers familiar with the codebase
- **Easy** difficulty items have low risk and are suitable for new contributors

---

*This roadmap was produced through systematic analysis of all 28 core modules, 24 test files, 5 configuration schemas, deployment infrastructure, and the full UI layer. Every item represents a real, specific engineering improvement identified from codebase analysis — no filler.*
