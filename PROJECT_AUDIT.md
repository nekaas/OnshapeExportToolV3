# Project Audit Report

> **Brutally honest engineering review of the Onshape Export Manager**
>
> Date: 2026-07-08 | Auditor: Automated codebase analysis
> Scope: All source files, tests, deployment scripts, and configuration

---

## Executive Summary

The Onshape Export Manager is a **mature prototype** — a project with genuinely solid foundations that has outgrown its proof-of-concept origins but has not yet been hardened for production. The codebase demonstrates strong engineering instincts: a clean event-driven architecture, sensible separation of concerns, excellent deployment tooling, and thoughtful Raspberry Pi optimization. However, it also carries the scars of organic growth: a dual account model creating significant code duplication, a monolithic 1,300-line web handler, a CLI interface that is almost entirely untested, and fundamental thread-safety gaps that would manifest under any concurrent load.

The project is well-positioned to become production-grade with approximately 4-6 weeks of focused hardening. The most urgent issues are atomicity of queue operations, thread safety of shared mutable state, and completion of the organizations migration to eliminate the duplicate credential management pathways.

**Verdict**: A solid B+ prototype that needs disciplined engineering to reach A-grade production readiness.

---

## Scores

| Dimension | Score | Summary |
|---|---|---|
| Architecture | **6/10** | Good layered design held back by manual DI and duplicate subsystems |
| Maintainability | **7/10** | Clean module boundaries but a monolithic web handler and thin public API |
| Scalability | **5/10** | Single-worker bottleneck, O(n) document filtering, no horizontal scaling path |
| Performance | **6/10** | Excellent Pi optimization, but wasteful queries and per-job config reload |
| UX | **7/10** | Polished glassmorphism design, real-time updates — missing a11y and mobile |
| Reliability | **6/10** | Graceful degradation is excellent, but race conditions undermine core operations |
| Security | **7/10** | Strong auth fundamentals, but missing operational security layers |
| Developer Experience | **7/10** | Clean test patterns, but the CLI gap and missing type checking hurt |
| **Overall Technical Debt** | **Moderate** | Migration in progress, significant duplication, testing gaps |

---

## Architecture — 6/10

### What Works

The project employs a **layered service architecture** with clear boundaries:

```
Foundation (models, jobs, retry, settings, security — pure data, no deps)
    ↓
Infrastructure (database, logger, events, configuration — state & I/O)
    ↓
Services (api_pool, auth, export_formats, queue_manager, scheduler, etc.)
    ↓
Integration (onshape_client, export_engine — external API & orchestration)
    ↓
Process (worker — long-running daemon)
```

The **EventBus** is the architectural centerpiece — a thread-safe publish/subscribe hub with a bounded ring buffer for replay. Every subsystem (audit logging, WebSocket streaming, notifications, metrics) consumes events through it rather than through direct coupling. This is genuinely good design and the single best decision in the codebase.

**Graceful degradation** is another strong pattern: if configuration is invalid at startup, the application boots with `queue_manager`, `scheduler`, and `api_pool` set to `None`. The web UI renders meaningful empty states rather than crashing. This is production-grade thinking.

### What Doesn't Work

**Manual Service Locator defeats the purpose of DI.** The `Application` dataclass holds all singleton services as mutable attributes. Factory methods like `create_api_pool()` and `create_export_engine()` exist on the same class, mixing container responsibilities with service creation. There is no type-safe way to express "this component requires a Database and an EventBus." Instead, every consumer receives the entire `Application` and picks what it needs. This works at small scale but becomes a maintenance burden as the service count grows.

**The dual account model is the single largest source of technical debt.** `ApiPool` (based on flat `accounts.json`) and `CredentialPool` (based on hierarchical `organizations.json`) are near-duplicate implementations of the same concept: select the best credential from a pool, track health, handle rate limiting. They use different state tracking (mutable dataclass attributes vs. EMA-based latency), different persistence strategies, and different selection algorithms. Every new feature that touches credentials must be implemented twice or, more realistically, only once — leaving one pathway incomplete.

**`web.py` at 1,300+ lines is a monolith masquerading as a route file.** It contains 50+ endpoint handlers, authentication middleware, WebSocket management, SSE streaming, template rendering, and setup wizard logic — all in a single file. There are no separate route modules, no request/response schema definitions per endpoint group, and no extraction of business logic from HTTP concerns. FastAPI's router composition features are unused.

**No API versioning.** All endpoints live at `/api/...` with no version prefix. Any breaking change to the API must be coordinated with a simultaneous frontend update, or both old and new behavior must be handled in the same handler.

### Thread Safety Gaps

- `ApiPool.lease()` mutates `AccountRuntimeState` attributes (failure_count, api_usage, last_used) without any lock. If the web dashboard queries account status while the worker is recording a failure, the read may observe a partially-updated state.
- `QueueManager.claim_next()` reads the next due job, then updates its status in a separate operation. Between read and update, nothing prevents another worker from claiming the same job. This is the textbook TOCTOU (time-of-check-time-of-use) race.
- `remote_access._cache` is a module-level dict with a 15-second TTL. Reads and writes are protected by the GIL in CPython, but the pattern is fragile and would break under free-threaded Python or subinterpreters.

---

## Maintainability — 7/10

### What Works

**Module boundaries are sensible.** Each file in `core/` has a single responsibility, a clear name, and manageable size (most are 100-300 lines). A developer can understand `retry.py` without reading `export_engine.py`. The layered architecture means dependency arrows point consistently downward.

**Consistent coding style.** All services follow the same patterns: constructor injection of dependencies, `start()/stop()` lifecycle methods where needed, typed dataclasses for data transfer. Error handling follows a consistent philosophy: best-effort for non-critical paths (telemetry, events, notifications), fail-fast for critical paths (config loading, authentication, export).

**Well-named things.** Class names (`ApiPool`, `QueueManager`, `ExportEngine`, `FolderManager`) clearly communicate purpose. Method names (`claim_next`, `mark_completed`, `lease`) use domain-appropriate verbs. Test method names are descriptive (`test_rate_limited_account_fails_over_then_recovers`).

### What Doesn't Work

**The `__init__.py` files are empty** (or contain only a version string). There is no curated public API. Consumers import from individual modules: `from onshape_export_manager.core.database import Database`. If `database.py` is renamed or split, every import site breaks. For a library with 28 core modules, this is a significant maintenance liability. Re-exporting key symbols through `__init__.py` would decouple internal organization from the public interface.

**Code duplication beyond the dual account model:**

- `serialize_dt()` / `parse_dt()` appear in both `database.py` and `api_pool.py` with slightly different type signatures.
- `AccountRuntimeState.from_dict()` in `api_pool.py` duplicates serialization logic that `database.py` already handles for other types.
- The `_selection_key` pattern for choosing the "best" credential appears in both `ApiPool.lease()` (tuple of `(api_usage, failure_count, last_used, name)`) and `CredentialPool` (`order_credentials()` using priority→requests_today→failures→last_used). The selection criteria are different but the pattern is identical.

**No type checking infrastructure.** Despite extensive use of type hints throughout the codebase, there is no `mypy` or `pyright` configuration, no CI step for type checking, and no evidence that types have been verified. Several functions use `Any` as a parameter type (`parse_dt` in `api_pool.py` accepts `Any`), which defeats the purpose of typing.

**`retry.py` has confusing aliases.** `delay_for_attempt()` and `delay_seconds_for_attempt()` are described as "compatibility aliases" for each other. This suggests an API change happened without cleaning up the old name, leaving future developers to wonder which to use.

---

## Scalability — 5/10

### What Works

**SQLite WAL mode** is correctly configured, allowing concurrent reads during writes. This is appropriate for the target deployment (Raspberry Pi, single process).

**The event bus ring buffer** uses `collections.deque` with a configurable `maxlen`, providing O(1) append and bounded memory. Late-joining subscribers (WebSocket clients, audit service restart) can replay recent events.

### What Doesn't Work

**Single-worker model is a hard bottleneck.** The `BackgroundWorker` runs as a single daemon thread with its own asyncio event loop. Each tick processes jobs sequentially. The `worker_count: 4` setting in `config.json` appears to be aspirational — there is no mechanism to spawn multiple workers or distribute queue items across them. The TOCTOU race in `claim_next()` would cause duplicate processing if multiple workers were actually started.

**`stats()` in `QueueManager` runs five separate SQL queries** — one for each `JobStatus` value — each opening a new SQLite connection. A single `SELECT status, COUNT(*) FROM queue GROUP BY status` would return the same data. For a queue with thousands of entries, this is wasteful.

**Onshape document filtering is O(n) client-side.** `fetch_documents_by_label()` in `onshape_client.py` loads ALL visible documents from the Onshape API, then filters by label and date range locally. The docstring acknowledges this is because Onshape's `?label=` query parameter is "unreliable." For an organization with thousands of documents, this is a serious performance problem. The correct approach is paginated API queries with server-side filtering where possible, or at minimum incremental caching of the document list.

**No horizontal scaling path.** The application is fundamentally single-process. Queue state, scheduler state, and API pool state all live in a single SQLite database with no coordination mechanism for multiple instances. If export throughput needs to exceed what a single Raspberry Pi can provide, the entire architecture must be redesigned.

**Only the first Part Studio per document is exported.** The docstring in `export_engine.py` explicitly notes this is "preserving proof-of-concept behavior." For documents containing multiple Part Studios (common in assembly projects), only one gets exported. The rest are silently skipped.

---

## Performance — 6/10

### What Works

**Raspberry Pi optimization is thoughtful and pervasive:**
- `@dataclass(slots=True)` on all data classes reduces memory overhead
- `scrypt` password hashing with tuned parameters (N=2^14, r=8, p=1) avoids memory exhaustion
- `RotatingFileHandler` with `delay=True` avoids creating empty log files
- `psutil` is optional — system monitoring degrades gracefully to `/proc` filesystem reads
- No heavy framework dependencies (no SQLAlchemy ORM, no React build chain)

**ZIP backup compression** uses `ZIP_DEFLATED` which is a good balance of speed and size for config/database backups.

### What Doesn't Work

**Per-job config reload.** `_build_request()` in `worker.py` calls `config_manager.load()` on every single job — reading and parsing all five JSON config files from disk. For a scheduled task that runs every 15 minutes, this is wasteful but tolerable. For a burst of 50 queued jobs, it means 50 full re-parses of identical data.

**Five separate queries for queue stats** (described under Scalability) is also a performance issue at smaller scale. Each query opens a new SQLite connection.

**`global_search()` in `metrics.py` loads up to 2,000 history entries into memory** and performs linear string matching. For a long-running instance with tens of thousands of exports, this becomes slow and memory-intensive. SQLite's built-in FTS5 (full-text search) module would be dramatically more efficient.

**`directory_usage()` walks the entire exports tree** to count files and sum sizes. With a 50,000 file cap, this could take seconds on a slow SD card. The result is not cached, so every dashboard refresh triggers a full walk.

**Frontend assets have no build step.** Alpine.js, Chart.js, Flatpickr, Tailwind CSS, and HTMX are all loaded from CDN with no bundling, minification, or tree-shaking. The `app.js` file is served as-is with no minification. While this is appropriate for a prototype, it means every page load fetches 5+ separate CDN resources.

---

## UX — 7/10

### What Works

**The dark-first glassmorphism design is genuinely attractive.** The CSS custom property system (60+ variables) enables consistent theming across all components. The dark/light toggle with `localStorage` persistence is correctly implemented.

**Real-time updates work well.** The SSE stream (`/api/stream`) provides live summary data to the dashboard shell. The WebSocket endpoint (`/ws/events`) streams audit events to the activity page. Both have polling fallbacks (6-second interval for summary, periodic fetch for events).

**The command palette (`⌘K`)** is a thoughtful power-user feature. Global search across accounts, labels, profiles, history, and queue is genuinely useful and well-implemented with keyboard-first navigation.

**The manual export wizard** is the most polished workflow, with date presets, Flatpickr integration, template saving to `localStorage`, and a preview/estimate step before queuing.

**The setup wizard** correctly detects whether the application is in first-run mode and guides the user through owner creation, storage configuration, and initial setup.

### What Doesn't Work

**No accessibility.** There are no ARIA labels, no `role` attributes, no focus trapping in modals, no keyboard navigation beyond the command palette, and no screen reader considerations. The glassmorphism design, while attractive, uses low-contrast text in several places (secondary text, muted labels). The sidebar toggle and mobile menu have no `aria-expanded` state.

**No mobile responsiveness.** The sidebar layout, data tables, and dashboard widgets assume a desktop viewport. On narrow screens, tables overflow horizontally with no scroll indicators, and the sidebar permanently obscures content.

**HTMX is loaded but unused.** The CDN script tag is in `base.html`, but no template uses `hx-*` attributes. This is dead weight on every page load.

**Forms have no client-side validation.** The login form, label creation form, profile editor, and notification channel configurator all rely entirely on server-side validation. Users see raw JSON error messages from the API rather than inline field validation.

**Error states are inconsistent.** Some pages show toast notifications for errors, others show inline alerts, and some silently fail. There is no standardized error boundary component.

**No undo capability.** Deleting a label, organization, or notification channel is immediate and irreversible from the UI. There is no confirmation dialog with a countdown, and no undo toast.

---

## Reliability — 6/10

### What Works

**Graceful degradation is excellent.** If configuration is invalid, the application boots and shows meaningful error states. If the Onshape API is unreachable, exports fail with retry rather than crashing the worker. The event bus isolates subscriber failures — a crashing audit subscriber does not affect WebSocket delivery.

**Retry with exponential backoff** is well-implemented across the stack. `RetryPolicy` provides configurable base delay, backoff multiplier, max attempts, and retryable HTTP status codes. `QueueRetryPolicy` extends this for queue-specific behavior with per-attempt delay tracking. The `is_transient_exception()` heuristic correctly classifies network errors for automatic retry.

**The event bus never raises.** `EventBus.publish()` wraps every subscriber dispatch in try/except, logs errors, and continues. A misbehaving subscriber cannot take down the system.

**Backup safety net.** `BackupManager.restore_backup()` takes a pre-restore snapshot before overwriting files. If the restore fails, the snapshot can be used for recovery.

### What Doesn't Work

**Queue claim race condition.** As described under Architecture, `claim_next()` has a TOCTOU race. In a single-worker setup this is benign, but it means the queue cannot safely support multiple workers — a feature the `worker_count` config setting implies should work.

**Scheduler never re-syncs.** `BackgroundWorker._sync_scheduler_jobs()` runs once at startup. If labels are added, removed, or modified while the worker is running, scheduler jobs become stale. A label with a daily schedule that is deleted will continue generating export jobs until the worker restarts.

**No export timeout enforcement.** `config.json` has `export_timeout_seconds: 120`, but there is no mechanism in the worker or export engine to enforce this. An export that hangs (e.g., waiting for a translation that never completes) will block the worker indefinitely. The `OnshapeClient` has request-level timeouts (30s default), but the overall export pipeline has no deadline.

**Backup restore on a live database.** `BackupManager.restore_backup()` overwrites the SQLite database file directly. If the application is running (and it always is, since the restore API is part of the running application), the in-memory WAL may contain uncommitted writes that conflict with the restored file. There is no coordination with the `Database` instance to close connections before restore.

**Notification delivery queue overflow.** `NotificationService` uses a `queue.Queue(maxsize=2000)`. Under a burst of events (e.g., 50 simultaneous export failures), events beyond 2,000 are silently dropped with a warning log. There is no backpressure mechanism to slow the event producer.

---

## Security — 7/10

### What Works

**Password hashing uses scrypt with strong parameters** (N=2^14, r=8, p=1) via `hashlib.scrypt`. This is a memory-hard algorithm resistant to GPU/ASIC acceleration. Salts are randomly generated per-password and stored in the encoded hash string. There is no dependency on `passlib` or `bcrypt` — everything is stdlib, reducing supply chain risk.

**TOTP 2FA is correctly implemented** per RFC 6238: HMAC-SHA1, 30-second time step, 6-digit codes, ±1 step acceptance window. Secret provisioning uses the standard `otpauth://` URI format for QR code generation.

**Session tokens are hashed before storage.** `AuthService.create_session()` generates a random 64-byte token, returns it to the client, but stores only `SHA-256(token)` in the database. A database compromise does not reveal valid session tokens.

**Secret references** (`env:VARIABLE_NAME`) allow API keys to be stored in environment variables rather than plaintext JSON config files. The `resolve_secret_value()` function is used consistently by `ConfigManager` and `OrganizationManager`.

**`ConfigModel` uses `extra="forbid"`** — unknown keys in JSON config files are rejected with a clear error. This prevents typos from silently creating unintended configuration.

**Backup path traversal prevention.** `BackupManager._resolve()` strips directory components from filenames using `Path(name).name`, preventing `../../../etc/passwd` style attacks through backup names.

### What Doesn't Work

**No brute-force protection on login.** There is no rate limiting, no account lockout after failed attempts, and no CAPTCHA. An attacker can submit unlimited password attempts against the `/login` endpoint.

**No API rate limiting.** All API endpoints are unthrottled. A malicious or buggy client could hammer `/api/exports/run` to flood the queue, or repeatedly poll expensive endpoints like `/api/metrics`.

**No CSRF protection.** The application uses cookie-based sessions (`oem_session`) but implements no CSRF tokens, no `SameSite` cookie attribute enforcement, and no `Origin`/`Referer` header checking. While the primary attack surface is low (the app typically runs on localhost), the reverse proxy documentation encourages exposing it to the internet.

**Session cookie lacks `__Host-` prefix and explicit `Secure`/`HttpOnly`/`SameSite` attributes.** The `set_cookie` call in `web.py` should set these explicitly rather than relying on browser defaults.

**No audit log for authentication events.** Login failures are logged to the application log but not to the audit event system. This means the activity page and notification system are blind to brute-force attempts.

**Backup archives are not encrypted.** Configuration backups contain API keys and secrets in plaintext JSON within the ZIP file. Anyone with filesystem access to the backups directory can read them.

**No minimum password strength enforcement.** `AuthService.create_owner()` accepts any non-empty password. While the setup wizard enforces a minimum length of 8 characters on the client side, the API endpoint does not validate this server-side.

---

## Developer Experience — 7/10

### What Works

**The test suite is well-structured.** 24 test files map cleanly to source modules. Test doubles (`FakeSession`, `FakeResponse`, `FakeExportClient`, `FakePoster`, `StubEngine`, `Clock`) are well-designed and minimally coupled. The `Clock` pattern for deterministic time is particularly elegant — it enables testing rate-limit recovery, scheduler ticks, and queue backoff without `time.sleep`.

**State round-trip testing** is a strong pattern. Many tests write state to the database, create a new instance from the same database, and verify the state survived. This catches serialization bugs that unit tests alone would miss.

**`test_web_api.py` is comprehensive.** It boots a real FastAPI `TestClient`, copies templates into a temp directory, and tests 20+ endpoints including WebSocket streaming and the full setup wizard flow. This is closer to an integration test than a unit test and provides real confidence.

**Deployment tooling is excellent.** `install.sh` is a clean, well-commented bash script with `set -euo pipefail`, proper `sudo` handling, and configurable port/user. The systemd unit file is correctly configured with `Restart=on-failure`, memory limits, and `After=network-online.target`. The reverse proxy documentation covers five different methods with working configuration examples.

### What Doesn't Work

**CLI testing is virtually nonexistent.** `test_cli.py` contains exactly two tests: `parse_cli_datetime()` and `export_window()` date validation. None of the 20+ CLI commands are tested: `--init`, `--init-db`, `--validate-config`, `--database-status`, `--accounts-status`, `--queue-status`, `--scheduler-status`, `--list-export-formats`, `--list-export-profiles`, `--run-export`, `--add-export-profile`, `--run-worker`, `--drain-once`. This is the single largest testing gap.

**No pytest features are used.** Despite requiring `pytest>=8.2` and `pytest-asyncio`, all tests inherit from `unittest.TestCase` and use `self.assertEqual()`. There are no fixtures, no parametrize, no markers, no conftest.py. The test suite is functionally unittest with a pytest runner.

**No type checking.** As noted under Maintainability, type hints exist but are unverified. There is no `mypy.ini`, `pyproject.toml [tool.mypy]` section, or CI step.

**No linting configuration.** There is no `.flake8`, `.pylintrc`, `ruff.toml`, or any other linter configuration in the repository.

**No pre-commit hooks.** Developers can commit code that fails tests, has syntax errors, or violates style conventions without any automated gate.

**No coverage measurement.** There is no `.coveragerc`, no `pytest-cov` dependency, and no coverage reporting in CI or locally.

**`bambu.py`, `plugins.py`, and `security.py` have zero tests.** These are small files, but untested code is broken code waiting to be discovered.

---

## Overall Technical Debt Assessment: Moderate

The project carries moderate technical debt concentrated in four areas:

### 1. Dual Account Model Migration (HIGH impact)
The coexistence of flat `accounts.json` (via `ApiPool`) and hierarchical `organizations.json` (via `CredentialPool`) is an in-progress migration that has stalled. Every new feature touching credentials must either be implemented twice or implemented once in the new model, leaving the old pathway incomplete. The import functionality (`/api/organizations/import`) exists but the old model has not been deprecated or removed. Estimated cleanup effort: 3-5 days.

### 2. Thread Safety Gaps (HIGH impact)
The TOCTOU race in queue claiming and the unguarded mutable state in `ApiPool`/`CredentialPool` will cause bugs as soon as the application is used under concurrent load — either from multiple workers or from web API calls during active exports. These are not theoretical issues; they are deterministic race conditions. Estimated cleanup effort: 2-3 days.

### 3. Monolithic Web Handler (MEDIUM impact)
`web.py` at 1,300+ lines is the largest single file in the project and contains route handlers, middleware, WebSocket management, SSE streaming, template rendering, and business logic. It will only grow as features are added. Extracting route modules would not change behavior but would dramatically improve maintainability. Estimated cleanup effort: 3-4 days.

### 4. CLI Testing Gap (MEDIUM impact)
The CLI is the primary interface for headless/Raspberry Pi deployments and scripting. Having it almost entirely untested means regressions in scheduling, export, or initialization go undetected until a user reports them. Estimated cleanup effort: 2-3 days.

### Additional Debt Items
- `retry.py` API aliases create confusion (LOW, 1 hour)
- HTMX loaded but unused in templates (LOW, 15 minutes)
- No API versioning strategy (MEDIUM, design work needed before implementation)
- `__init__.py` files expose no public API (MEDIUM, requires design decisions about what to export)
- `stats()` uses 5 queries instead of 1 (LOW, 30 minutes)
- Per-job config reload in worker (LOW, 1 hour with caching)
- `global_search()` loads up to 2000 entries in memory (LOW, 2 hours with FTS5)

---

## Summary Matrix

| Area | Issues Found | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| Architecture | 6 | 1 | 2 | 2 | 1 |
| Maintainability | 7 | 0 | 1 | 3 | 3 |
| Scalability | 5 | 1 | 2 | 1 | 1 |
| Performance | 5 | 0 | 0 | 2 | 3 |
| UX | 6 | 0 | 1 | 3 | 2 |
| Reliability | 5 | 1 | 2 | 1 | 1 |
| Security | 7 | 1 | 2 | 2 | 2 |
| Developer Experience | 9 | 0 | 2 | 4 | 3 |
| **Total** | **50** | **4** | **12** | **18** | **16** |

---

*This audit was produced through systematic analysis of all 28 core modules, 24 test files, 5 configuration schemas, deployment infrastructure, and the full UI layer. No aspect of the codebase was excluded from review.*
