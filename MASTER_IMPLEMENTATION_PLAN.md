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

## Phase 3: UI Polish (IN PROGRESS)
- [x] Tree selector on Groups page
- [x] Tree selector on Export page (batch selection)
- [x] Group management UI (create, delete, move, enable/disable)
- [x] Preview null-access fix (optional chaining)
- [ ] Accessibility audit
- [ ] Mobile-responsive sidebar
- [ ] Loading skeletons
- [ ] Empty state improvements
- [ ] Error state consistency
- [ ] Toast notification consistency

## Phase 4: Reliability (PLANNED)
- [ ] Input sanitization (XSS prevention server-side)
- [ ] Group name special character handling
- [ ] Worker health monitoring alerts
- [ ] Database connection resilience
- [ ] Config validation on load (more cross-reference checks)
- [ ] Export retry policy tuning
- [ ] API rate limit adaptive backoff

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
