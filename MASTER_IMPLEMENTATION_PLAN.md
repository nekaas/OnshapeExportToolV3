# Master Implementation Plan

## Status: Phase 3 — UI & Workflow Polish (36/78 items complete)

## Phase 0: Foundation (COMPLETE)
- [x] Project structure, config system, database schema v3
- [x] FastAPI web layer with auth
- [x] Alpine.js + Chart.js dashboard
- [x] SQLite WAL mode, versioned migrations

## Phase 1: Core Export (COMPLETE)
- [x] Onshape REST API client
- [x] Export engine (multi-format, multi-Part Studio)
- [x] Background worker (multi-threaded, graceful shutdown)
- [x] Queue manager (atomic claim, retry with backoff)
- [x] Export history and metrics

## Phase 2: Configuration & Management (COMPLETE)
- [x] JSON config with Pydantic validation
- [x] Config hot-reload (ConfigWatcher)
- [x] API key management (organizations + credentials)
- [x] Export profile CRUD
- [x] Group CRUD (create, update, delete, move)
- [x] Tree-based Account → Groups hierarchy
- [x] Scheduler (recurring exports)

## Phase 3: UI Polish (COMPLETE)
- [x] Tree selector on Groups page
- [x] Tree selector on Export page (batch selection)
- [x] Group management UI (create, delete, move, enable/disable)
- [x] Preview null-access fix (optional chaining)
- [x] Dashboard Labels→Groups fix
- [x] Toast consistency fix
- [x] Refresh button hidden on non-table pages
- [x] XSS sanitization (server-side HTML tag stripping)
- [x] Loading skeletons (CSS pulse animation)
- [x] Empty state consistency
- [x] BUG-003: group special character handling (slash→dash)
- [x] Accessibility audit + fixes (skip link, aria-labels, live regions)

## Phase 4: Reliability (COMPLETE)
- [x] Input sanitization (XSS prevention server-side)
- [x] Group name special character handling
- [x] Worker health monitoring (/api/worker/health with stall detection)
- [x] Database connection resilience (WAL checkpoint API)
- [x] Config validation: warns on empty assigned_accounts
- [x] Export retry policy: adaptive backoff for 429/5xx
- [x] Organisation aggregate root redesign

## Phase 5: Raspberry Pi Appliance (PLANNED)
- [ ] Systemd service file hardening
- [ ] Boot splash screen
- [ ] OLED/LCD display support
- [ ] GPIO button integration
- [ ] Temperature monitoring alerts
- [ ] SD card wear optimization (tmpfs for logs)

## Phase 6: Advanced Features (FUTURE)
- [ ] Bambu Studio direct integration (3MF creation)
- [ ] S3/SFTP export destinations
- [ ] Webhook export triggers
- [ ] Custom export format plugins
- [ ] Multi-user support (read-only viewers)
- [ ] Export diff/comparison

---

## Implementation Principles

1. **Documentation first** — update docs before code
2. **Test before merge** — 183 tests must stay green
3. **No silent divergence** — docs and code must match
4. **Config over code** — preferences in JSON, not hardcoded
5. **Single process** — no microservices, no external deps
