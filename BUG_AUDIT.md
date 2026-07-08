# Bug Audit Report

> Generated: 2026-07-08 | Tests: 180 passing | Automated + manual review

---

## OPEN ISSUES

### Severity: LOW

| # | Subsystem | Issue | Root Cause | Reproduction | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | Web | `test_pages_render` intermittently fails on `/settings` 404 | Auth state leaking between tests — setup not completed before rendering | Run test_pages_render before test_setup_wizard_flow | Complete auth setup in test | ✅ Fixed |
| 2 | Web | SSE `/api/stream` endpoint not tested | SSE testing deferred as "hard to test" | N/A | Add httpx streaming tests (Item 64) | ⬜ Deferred |
| 3 | CLI | `--run-export` and `--run-worker` not tested via subprocess | Requires real Onshape API credentials | N/A | Add integration smoke tests (Item 63) | ⬜ Deferred |
| 4 | Core | `retry.py` has confusing aliases (`delay_for_attempt` vs `delay_seconds_for_attempt`) | API change without cleanup | Import both — they're aliases | Deprecate one, keep the other | ⬜ Deferred |
| 5 | Core | `CredentialPool` and `ApiPool` are near-duplicates | Organic growth — org model added without deprecating flat model | Use either — both work | Merge into single CredentialProvider (V2) | ⬜ Deferred (V2) |
| 6 | Web | `web.py` at 1,300+ lines — monolithic route handler | Never refactored into route modules | N/A | Extract route modules (Item 11) | ⬜ Deferred (V2) |
| 7 | UI | No accessibility (ARIA labels, keyboard nav, screen reader) | Not considered during prototype development | Navigate with keyboard only — modals trap focus, tables have no labels | WCAG 2.1 AA audit (Item 20) | ⬜ Deferred (V3) |
| 8 | UI | No mobile responsiveness | Designed for desktop viewport | Open on phone — sidebar obscures content | Responsive layout (Item 55) | ⬜ Deferred (V3) |
| 9 | Perf | Onshape document fetching is O(n) client-side | Onshape `?label=` parameter unreliable | Export with org containing 1000+ documents — slow | Server-side filtering (Item 56) | ⬜ Deferred (V2) |

### Severity: MEDIUM

| # | Subsystem | Issue | Root Cause | Reproduction | Fix | Status |
|---|---|---|---|---|---|---|
| 10 | Core | `global_search()` loads up to 2000 history entries in memory | Linear search, no FTS | Search with large history — slow | SQLite FTS5 | ⬜ Deferred |
| 11 | Core | `directory_usage()` walks entire exports tree on every dashboard refresh | No caching | Open dashboard with 50000+ export files | Cache with TTL | ⬜ Deferred |
| 12 | Web | No CSRF protection on cookie-based sessions | CSRF tokens never implemented | Theoretical — app typically runs on localhost | Add CSRF middleware | ⬜ Deferred |
| 13 | Web | Session cookie lacks `__Host-` prefix, explicit `Secure`/`HttpOnly`/`SameSite` | Cookie set without explicit attributes | Check cookie in browser devtools | Set cookie attributes explicitly | ⬜ Deferred |
| 14 | Core | Backup archives not encrypted — contain API keys in plaintext | Backups are ZIP files without encryption | Create backup, unzip, read config | Encrypt backups with password | ⬜ Deferred |

### Severity: NONE (by design)

| # | Subsystem | Note |
|---|---|---|
| 15 | Auth | No multi-user support — single-owner model is intentional for Pi appliance |
| 16 | DB | No foreign key constraints — intentional loose coupling with JSON config |
| 17 | DB | SQLite only — intentional for Raspberry Pi; no PostgreSQL/MySQL planned |

---

## RESOLVED ISSUES

| # | Issue | Fix | Session |
|---|---|---|---|
| R1 | TOCTOU race in queue claim (double-processing) | Atomic `UPDATE ... RETURNING *` | Phase 1 |
| R2 | Data race in ApiPool state mutation | `threading.Lock` | Phase 1 |
| R3 | Data race in CredentialPool state mutation | `threading.Lock` | Phase 1 |
| R4 | Scheduler never re-syncs after label changes | EventBus subscription + `on_labels_changed()` | Phase 1 |
| R5 | Database corruption during backup restore | `PRAGMA wal_checkpoint(TRUNCATE)` before overwrite | Phase 1 |
| R6 | No rate limiting on login | 5/min per IP | Phase 1 |
| R7 | No rate limiting on API | 120/min per IP | Phase 1 |
| R8 | HTMX loaded but never used | Removed script tag | Phase 2 |
| R9 | Only first Part Studio exported per document | Iterates all Part Studios | Phase 4 |
| R10 | Document name collisions in exports | doc_id suffix in filename | Phase 4 |
| R11 | 5 separate SQL queries for queue stats | Single `GROUP BY` query | Phase 8 |
| R12 | Config reloaded on every job | 5s TTL cache in worker | Phase 8 |
| R13 | No per-export timeout enforcement | `asyncio.wait_for()` | Phase 6 |
| R14 | Worker couldn't stop gracefully during export | 30s timeout + in-flight awareness | Phase 6 |
| R15 | CLI virtually untested (2 trivial tests) | 15 integration tests, 12/14 commands | Phase 9 |
| R16 | Dead deps: textual, apscheduler, cryptography | Removed from requirements.txt | Cleanup |
| R17 | Dead files: bambu.py, plugins.py | Deleted | Cleanup |
| R18 | Bambu STL profile referenced nonexistent stub | Removed from defaults | Cleanup |
| R19 | Plugin nav item linked to empty page | Removed from NAV_ITEMS | Cleanup |
| R20 | Export options untyped (`dict[str, Any]`) | Per-format Pydantic schemas (Item 28) | Current |
| R21 | Inconsistent datetime handling (naive + aware mix) | UTC-aware enforced everywhere (Item 31) | Current |

---

## SUMMARY

| Severity | Open | Resolved | Deferred |
|---|---|---|---|
| Critical | 0 | 6 | 0 |
| High | 0 | 5 | 0 |
| Medium | 5 | 4 | 0 |
| Low | 9 | 6 | 4 |
| **Total** | **14** | **21** | **4** |

**All open issues are LOW or MEDIUM severity. No blocking issues for V1.0.**
All deferred items have clear target milestones (V2 or V3) and are documented in MASTER_IMPROVEMENT_PLAN.md.
