# Technical Debt Register — Onshape Export Manager

> **Date**: 2026-07-08  
> **Auditor**: Systems Engineering & Software Architecture  
> **Scope**: Every architectural shortcut, code smell, duplication, and violation of SOLID/DRY in the current codebase  
> **Methodology**: Static analysis of all source files, dependency graph tracing, test coverage analysis, comparison against production-grade benchmarks

---

## Debt Classification

| Grade | Meaning |
|---|---|
| **Critical** | Will cause data loss, security breach, or complete system failure under predictable conditions |
| **High** | Actively degrades development velocity; every new feature must work around it |
| **Medium** | Slows development or creates bugs under specific conditions; should be fixed within 2 sprints |
| **Low** | Cosmetic or minor; fix opportunistically |
| **Legacy** | Historical artifact that may be removed when migration is complete |

---

## 1. Architectural Debt

### 🔴 ARCH-01: Dual Credential Management (ApiPool + CredentialPool)

**Location**: `core/api_pool.py`, `core/organizations.py`  
**Description**: Two complete implementations of credential selection, health tracking, and rate-limit management exist in parallel. `ApiPool` uses flat `accounts.json` with mutable dataclass attributes. `CredentialPool` uses hierarchical `organizations.json` with EMA-based latency tracking. Both implement `lease()`, `snapshot()`, and health checking — with different algorithms, different state tracking, and different persistence.

**Impact**: Every feature touching credentials must be implemented twice (or only once, leaving the other pathway incomplete). Tests must cover both systems. Onboarding documentation must explain both models. The migration from flat→org was started but never completed.

**Resolution**: Choose one model (organizations). Complete the migration. Remove `ApiPool` and `accounts.json`. Items #9 and #25 in the improvement plan track this.

### 🔴 ARCH-02: Manual Service Locator Anti-Pattern

**Location**: `app.py` (`Application` dataclass)  
**Description**: The `Application` dataclass holds all singleton services as mutable attributes. Components receive the entire `Application` and extract what they need (`application.database`, `application.event_bus`). There is no interface-based dependency injection, no constructor injection, and no type-safe way to express "this component needs a Database."

**Impact**: 
- Impossible to instantiate services in isolation for testing without creating the full `Application`
- Adding a new service requires modifying the `Application` dataclass
- Circular dependency risk as service count grows
- Callers can access any service at any time, bypassing intended dependency boundaries

**Resolution**: Implement a proper DI container with constructor injection. Define clear interfaces. Item #10 in the improvement plan.

### 🔴 ARCH-03: Monolithic Route Handler (web.py at 1,400+ lines)

**Location**: `web.py`  
**Description**: All 50+ API endpoints, authentication middleware, WebSocket management, SSE streaming, template rendering, setup wizard logic, and utility functions live in a single file. FastAPI's `APIRouter` composition is unused.

**Impact**: 
- File is unreadable without extensive scrolling
- Merge conflicts are guaranteed with multiple developers
- Business logic is entangled with HTTP concerns (e.g., `_create_label()` directly reads/writes JSON config files)
- No separation between "route definition" and "request handling"

**Resolution**: Extract route modules by domain (`routes/labels.py`, `routes/queue.py`, `routes/organizations.py`) using `APIRouter`. Extract business logic into service methods. Item #11.

### 🟠 ARCH-04: TOCTOU Race in Queue Claim

**Location**: `core/queue_manager.py` — `claim_next()`  
**Description**: The method reads the next due job (SELECT), then updates its status to RUNNING (UPDATE) in a separate operation. Between the read and write, nothing prevents another worker from claiming the same job.

**Impact**: Single-worker deployment is safe by accident. Adding multi-worker support (a roadmap item) would cause duplicate exports. This is a textbook concurrency bug.

**Resolution**: Use `UPDATE ... WHERE status = 'pending' RETURNING *` to atomically claim jobs. SQLite supports RETURNING since 3.35. Item #1 in the original improvement plan tracks this.

### 🟠 ARCH-05: Scheduler Never Re-Syncs

**Location**: `core/worker.py` — `_sync_scheduler_jobs()`  
**Description**: Scheduler jobs are synced from label configuration once at startup. If labels are added, removed, or modified while the worker is running, scheduler jobs become stale. A deleted label with a daily schedule continues generating export jobs.

**Impact**: Stale scheduled jobs produce exports for non-existent labels, creating confusion and wasted API calls. The only fix is restarting the worker.

**Resolution**: Subscribe to `LABELS_CHANGED` events and re-sync scheduler jobs on change. Or poll for label changes on each tick.

---

## 2. Code Duplication

### 🟠 DUP-01: Serialization Logic Duplicated

**Location**: `database.py`, `api_pool.py`, `metrics.py`  
**Description**: `serialize_dt()` appears in both `database.py` and `api_pool.py` with slightly different type signatures. `AccountRuntimeState.from_dict()` in `api_pool.py` duplicates serialization logic that `database.py` already handles. The `_selection_key` pattern for choosing the "best" credential appears in both `ApiPool.lease()` (tuple comparison) and `CredentialPool.order_credentials()` (multi-criteria sort).

**Impact**: Bugs fixed in one copy may persist in another. Adding a new selection criterion requires changes in two places.

**Resolution**: Extract shared serialization and selection logic into a shared module. Define a single `serialize_dt()` with a consistent signature.

### 🟠 DUP-02: Config Reload on Every Job

**Location**: `core/worker.py` — `_build_request()`  
**Description**: The worker calls `config_manager.load()` on every single job — reading and parsing all five JSON config files from disk. For a burst of 50 queued jobs, this means 50 full re-parses of identical data.

**Impact**: Wasteful I/O and CPU, especially on Raspberry Pi with slow SD cards. Does not cause bugs but is a gratuitous performance sink.

**Resolution**: Cache the config in the worker for the duration of a tick. Re-read only if a `CONFIG_UPDATED` event fires. Item #5 in the improvement plan.

### 🟡 DUP-03: Five Separate SQL Queries for Queue Stats

**Location**: `core/queue_manager.py` — `stats()`  
**Description**: `QueueManager.stats()` runs five separate `SELECT COUNT(*) FROM queue WHERE status = ?` queries, each opening a new SQLite connection. A single `SELECT status, COUNT(*) FROM queue GROUP BY status` would return the same data.

**Impact**: Linear slowdown as queue grows. Each query is a separate filesystem operation on SQLite.

**Resolution**: Replace with a single GROUP BY query. Use the shared database connection (duplicate debt: ARCH-06).

### 🟡 DUP-04: `retry.py` Has Confusing Aliases

**Location**: `core/retry.py`  
**Description**: `delay_for_attempt()` and `delay_seconds_for_attempt()` are documented as "compatibility aliases" for each other. This suggests an API change was made without cleaning up the old name.

**Impact**: Two function names for the same thing creates confusion. Developers don't know which to import. Tests may use one while production code uses the other.

**Resolution**: Deprecate one alias. Remove after a grace period. Standardize on one name.

---

## 3. Type Safety & Static Analysis

### 🟠 TYPE-01: No mypy/pyright Configuration

**Location**: Project root (missing `mypy.ini` or `pyproject.toml [tool.mypy]`)  
**Description**: Despite extensive type hints throughout the codebase, there is no type checker configuration, no CI step for type checking, and no evidence that types have been verified. Several functions use `Any` as a parameter type.

**Impact**: Type hints provide documentation but not safety. Type errors pass silently. Refactoring is dangerous because the type checker isn't verifying correctness.

**Resolution**: Add `mypy` configuration with `strict = true` (gradually). Run in CI. Fix existing type errors. Item #66 in the improvement plan.

### 🟠 TYPE-02: `parse_dt()` Accepts `Any`

**Location**: `core/api_pool.py` — `parse_dt(value: Any)`  
**Description**: A parsing function that accepts `Any` defeats the purpose of type hints. Callers can pass integers, lists, or None, and the function must handle all cases at runtime.

**Resolution**: Accept `str | datetime | None`. Validate at the call site.

### 🟡 TYPE-03: `dict[str, Any]` for Export Options

**Location**: `core/export_formats.py`, `core/configuration.py`  
**Description**: Export format options are typed as `dict[str, Any]`, meaning there is no compile-time validation of STL resolution values, STEP units, or OBJ mode. A typo like `"resoultion": "fine"` passes silently.

**Resolution**: Define per-format Pydantic models: `StlOptions(mode: Literal["binary", "ascii"], resolution: Literal["coarse", "fine"], units: Literal["inch", "mm"])`. Item #28.

---

## 4. Database

### 🟠 DB-01: Per-Call SQLite Connections

**Location**: `core/database.py` — most methods  
**Description**: Most `Database` methods call `sqlite3.connect()` on every invocation. SQLite WAL mode supports concurrent reads on a shared connection, but a new connection is opened for each query. This is slower than connection reuse and defeats some of WAL's benefits.

**Impact**: Increased latency per query. More file descriptor usage. The `QueueManager.stats()` pattern (5 separate calls → 5 separate connections) amplifies this.

**Resolution**: Use a shared read connection. Open write connections as needed for mutations. Item #59.

### 🟡 DB-02: Global Search Does Linear Scan

**Location**: `core/metrics.py` — `global_search()`  
**Description**: The command palette search loads up to 2,000 history entries into memory and performs linear string matching. For a long-running instance with tens of thousands of exports, this becomes slow and memory-intensive.

**Resolution**: Use SQLite's built-in FTS5 module for full-text search across history, labels, accounts, and profiles.

### 🟡 DB-03: `directory_usage()` Walks Entire Exports Tree

**Location**: `core/metrics.py`  
**Description**: The storage usage calculation walks the entire exports directory tree to count files and sum sizes. With a 50,000-file cap, this could take seconds on a slow SD card. The result is not cached.

**Resolution**: Cache the result with a TTL. Incrementally update a running total when exports complete. Use `os.scandir()` for more efficient walking.

---

## 5. Testing

### 🟠 TEST-01: CLI Is Almost Entirely Untested

**Location**: `tests/test_cli.py`  
**Description**: The CLI (`cli.py`) handles account management, label creation, profile management, manual exports, backups, and database operations. Test coverage for these paths is minimal or nonexistent.

**Impact**: CLI bugs are not caught before release. The CLI is the recovery path when the web UI fails — if the CLI is broken, users have no recovery.

**Resolution**: Add integration tests for all CLI commands. Test with actual config files and mock Onshape responses.

### 🟡 TEST-02: No Concurrency Tests

**Location**: `tests/` — missing  
**Description**: There are no tests for: multi-worker queue contention, API pool lease races, WebSocket event delivery during worker activity, rapid worker start/stop cycles, or event bus subscriber isolation.

**Impact**: Concurrency bugs (like the TOCTOU race) are discovered in production, not in CI.

**Resolution**: Item #65. Write pytest-asyncio tests with multiple concurrent workers, shared queue, and simulated race conditions.

### 🟡 TEST-03: No End-to-End Test

**Location**: Missing  
**Description**: There is no test that boots the full application, creates configuration via the API, runs an export, and verifies files on disk. All tests are unit or integration tests of individual components.

**Impact**: Integration failures between components are caught manually or in production.

**Resolution**: Item #70. Write a single E2E test with a fake Onshape client that exercises: init → web start → create org/credential/label/profile → manual export → verify files.

---

## 6. Frontend

### 🟠 FE-01: app.js Is a 1,380-Line Monolith

**Location**: `ui/static/app.js`  
**Description**: Three Alpine.js components (`appShell`, `dashboardPage`, `sectionPage`) plus all utility functions, template rendering logic, date manipulation, chart rendering, API calls, and manual export workflow — all in one file.

**Impact**: 
- `sectionPage` handles 14 different pages through conditional logic (page === 'logs', page === 'settings', page === 'organizations', etc.)
- Adding a new page requires modifying the monolithic `sectionPage` function
- Impossible to lazy-load page-specific code
- No module-level encapsulation

**Resolution**: Split into ES modules: `services/api.js`, `components/toast.js`, `components/modal.js`, `components/commandPalette.js`, `pages/dashboard.js`, `pages/manual-export.js`, `pages/organizations.js`, etc. Item #18.

### 🟠 FE-02: No Build Step — All CDN Dependencies

**Location**: `ui/templates/base.html`  
**Description**: Alpine.js, Chart.js, Flatpickr, Tailwind CSS, and HTMX are all loaded from CDN with no bundling, minification, or tree-shaking. Every page load fetches 5+ separate CDN resources.

**Impact**: 
- Slow initial load on Raspberry Pi local networks
- No offline capability
- Dependency on CDN availability (if CDN is down, UI is broken)
- No version pinning beyond the URL (CDN could update and break compatibility)
- HTMX is loaded but never used — dead bytes on every page

**Resolution**: Bundle with Vite or esbuild. Generate content-hashed filenames. Tree-shake unused code. Serve from the application's own static files. Item #17.

### 🟡 FE-03: `sectionPage` Renders Every Page as a Table — Even When Wrong

**Location**: `ui/static/app.js` — `sectionPage()` function  
**Description**: The generic section page renders a table for Accounts, Labels, Profiles, Queue, Scheduler, and History. But these are fundamentally different concepts:
- Queue needs a real-time timeline view
- Scheduler needs a calendar-like view
- History needs summary + detail
- Accounts/Organizations needs a card-based layout with nested credentials

**Impact**: Every page feels the same. Important domain-specific information is lost in the one-size-fits-all table.

**Resolution**: Design dedicated page components for each domain. The table is a fallback for list-like data, not the universal UI.

### 🟡 FE-04: Template Rendering in JavaScript with String Concatenation

**Location**: `app.js` — `renderCell()` method  
**Description**: Table cells are rendered by building HTML strings: `return '<span class="badge badge-ok">Success</span>'`. This is error-prone, XSS-risky despite `escapeHtml()`, and unreadable for complex markup.

**Resolution**: Use Alpine.js `x-html` with template literals, or adopt a proper templating approach. Better: render on the server side where Jinja2 is already available.

### 🟡 FE-05: No Client-Side Routing

**Location**: `web.py` — page routes  
**Description**: Every page navigation is a full server round-trip (Jinja2 template render). The SPA-like Alpine.js components re-initialize on every page load. There is no client-side router to preserve state between pages.

**Impact**: Navigating from Dashboard → Queue → History → back to Dashboard requires 4 full page loads. Each load re-fetches data that was already available. The command palette's search results are lost between navigations.

**Resolution**: Consider a lightweight client-side router (e.g., Alpine.js with `x-if` page switching) or accept server-rendered pages but add a shared state cache.

---

## 7. Security

### 🟠 SEC-01: Session Tokens Have No Expiry Enforcement

**Location**: `core/auth.py`  
**Description**: Session tokens are stored in the database but there is no background task to purge expired tokens. The "remember me" flag extends the expiry to 30 days, but there's no mechanism to forcibly expire a session (e.g., after password change).

**Impact**: Stolen session tokens remain valid for up to 30 days. An administrator cannot view or revoke active sessions.

**Resolution**: Add a session management page showing active sessions with "Revoke" buttons. Implement a background task that purges expired tokens.

### 🟡 SEC-02: No Rate Limiting on Export Endpoints

**Location**: `web.py` — rate limiter only for login and generic API  
**Description**: The rate limiter applies to login (5 req/60s) and API (120 req/60s). But the export endpoint (`POST /api/exports/run`) has no specific rate limit beyond the generic API limit.

**Impact**: A malicious or buggy client could enqueue thousands of export jobs, exhausting Onshape API rate limits and creating a massive queue backlog.

**Resolution**: Add a specific rate limit for export submission: e.g., 10 exports per minute per IP.

### 🟡 SEC-03: TOTP Secret Stored in Plaintext Config

**Location**: `core/auth.py` — `totp_enabled()`, `config.json`  
**Description**: The TOTP secret for two-factor authentication appears to be stored in `config.json` (based on `auth.totp_enabled()` reading from config). If this is the case, anyone with filesystem access can extract the TOTP secret.

**Resolution**: Store TOTP secrets in the database with encryption at rest. Never store secrets in configuration files that may be backed up or version-controlled.

---

## 8. Configuration & Deployment

### 🟡 CFG-01: Configuration Inconsistency Between Files

**Location**: `config/accounts.json`, `config/organizations.json`  
**Description**: The application reads from both `accounts.json` (legacy) and `organizations.json` (new). Some endpoints return data from one, some from the other. The migration path is unclear.

**Resolution**: Complete the migration. Standardize on `organizations.json`. Remove `accounts.json` support after a deprecation window.

### 🟡 CFG-02: No Configuration Validation on Startup

**Location**: `core/configuration.py` — `ConfigManager`  
**Description**: The application handles invalid configuration gracefully (boots with `queue_manager = None`), which is good. However, there is no validation report or user-visible warning when configuration is partially invalid.

**Impact**: A user may not realize their configuration is broken until they try to use a feature that silently failed to initialize.

**Resolution**: Show a banner on the dashboard when configuration has errors: "2 configuration issues detected. Click to review."

### 🟢 CFG-03: `worker_count` Config Is Unused

**Location**: `config/config.json` — `worker_count: 4`  
**Description**: The config file specifies `worker_count: 4`, but the application only ever starts one worker thread. This setting is aspirational with no implementation backing it.

**Resolution**: Either implement multi-worker support (Item #41) or remove the misleading config key.

---

## 9. Observability

### 🟡 OBS-01: No Structured Error Codes

**Location**: All modules  
**Description**: Errors are reported as human-readable strings. There is no error code system (e.g., `ERR_EXPORT_001`, `ERR_AUTH_003`). This makes it difficult to write documentation, create troubleshooting guides, or build automated error recovery.

**Resolution**: Define an error code enum. Every raised exception should include a unique code. The API should return error codes alongside messages.

### 🟡 OBS-02: No Health Check Depth

**Location**: `GET /health`  
**Description**: The health endpoint returns `{"status": "ok"}` without checking database connectivity, Onshape API reachability, queue health, or worker status. It is a static string that only proves the web server is running.

**Resolution**: Add a `/health/deep` endpoint that checks: database connection, config validity, worker status, queue depth, and optionally Onshape API reachability.

---

## 10. Summary

| Category | Critical | High | Medium | Low |
|---|---|---|---|---|
| Architecture | 3 | 2 | 0 | 0 |
| Code Duplication | 0 | 2 | 2 | 0 |
| Type Safety | 0 | 2 | 1 | 0 |
| Database | 0 | 1 | 2 | 0 |
| Testing | 0 | 1 | 2 | 0 |
| Frontend | 0 | 2 | 3 | 0 |
| Security | 0 | 1 | 2 | 0 |
| Config/Deploy | 0 | 0 | 2 | 1 |
| Observability | 0 | 0 | 2 | 0 |
| **Total** | **3** | **11** | **16** | **1** |

**Total items: 31**

**Highest-priority resolutions** (should be completed before any new feature work):
1. Unify ApiPool + CredentialPool (ARCH-01)
2. Fix TOCTOU race in queue claim (ARCH-04)
3. Extract route modules from web.py (ARCH-03)
4. Implement proper DI container (ARCH-02)
5. Add mypy/pyright configuration (TYPE-01)
6. Split app.js into ES modules (FE-01)

---

*End of Technical Debt Register. Next: MASTER_UI_REDESIGN_PLAN.md*
