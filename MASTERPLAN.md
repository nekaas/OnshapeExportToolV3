# Onshape Export Manager — Master Plan

**Version:** 0.3.0-target  
**Date:** 2026-07-26  
**Status:** Planning Phase

---

## Phase 0: Foundation Repair (Days 1-3)

### Architecture Cleanup
| # | Task | Priority | Status |
|---|------|----------|--------|
| 0.1 | Rename "Organizations" to "Schools" throughout codebase | P0 | ⬜ |
| 0.2 | Rename "Groups" to "Classes" or keep as "Groups" under Schools | P0 | ⬜ |
| 0.3 | Remove LEGACY_PAGES and dead routes from web.py | P0 | ⬜ |
| 0.4 | Standardize export directory: `exports/{school}/{group}/{date}/` | P0 | ✅ |
| 0.5 | Remove all dead code: `LEGACY_PAGES`, stubs, unused imports | P0 | ✅ |
| 0.6 | Consolidate duplicate `utc_now`, `human_bytes` into `core/utils.py` | P1 | ⬜ |
| 0.7 | Remove empty `__init__.py` files in unused packages | P2 | ⬜ |

### Database
| # | Task | Priority | Status |
|---|------|----------|--------|
| 0.8 | Add `schools` table (migrate from organizations.json) | P0 | ⬜ |
| 0.9 | Add `school_id` FK to export_history, export_queue, scheduler_jobs | P0 | ⬜ |
| 0.10 | Add migration v4 for schools table | P0 | ⬜ |
| 0.11 | Add database indexes for common queries (school_id, label_name, created_at) | P1 | ⬜ |
| 0.12 | Add WAL checkpoint on shutdown | P1 | ⬜ |
| 0.13 | Add database integrity check on startup | P1 | ⬜ |

### API Cleanup
| # | Task | Priority | Status |
|---|------|----------|--------|
| 0.14 | Remove `/api/labels` POST (deprecated, use `/api/groups`) | P0 | ⬜ |
| 0.15 | Remove `/api/accounts` GET (use `/api/tree`) | P0 | ⬜ |
| 0.16 | Remove `/api/formats` GET (unused by frontend) | P1 | ⬜ |
| 0.17 | Remove `/api/queue/batch` POST (test-only) | P1 | ⬜ |
| 0.18 | Remove `/api/telemetry/*` endpoints (unused) | P1 | ⬜ |
| 0.19 | Add `/api/schools` CRUD | P0 | ⬜ |
| 0.20 | Add `/api/schools/{id}/groups` for group management | P0 | ⬜ |
| 0.21 | Add `/api/schools/{id}/credentials` for credential management | P0 | ⬜ |
| 0.22 | Standardize all error responses to `{"error": str, "detail": str, "code": str}` | P1 | ⬜ |
| 0.23 | Add request ID middleware for tracing | P2 | ⬜ |

---

## Phase 1: Core Reliability (Days 4-7)

### Export Engine
| # | Task | Priority | Status |
|---|------|----------|--------|
| 1.1 | Add retry with exponential backoff in export engine | P0 | ⬜ |
| 1.2 | Add export progress tracking (docs processed / total) | P0 | ⬜ |
| 1.3 | Add partial export resume on failure | P1 | ⬜ |
| 1.4 | Add export cancellation mid-flight | P1 | ⬜ |
| 1.5 | Add per-format timeout (30s STL, 60s STEP, 30s 3MF) | P0 | ⬜ |
| 1.6 | Fix flaky test_export_engine test | P0 | ⬜ |
| 1.7 | Add streaming download for large STL files | P2 | ⬜ |

### Worker
| # | Task | Priority | Status |
|---|------|----------|--------|
| 1.8 | Add worker health check endpoint with details | P1 | ⬜ |
| 1.9 | Add worker graceful shutdown (30s drain) | P0 | ⬜ |
| 1.10 | Add worker auto-restart on crash | P1 | ⬜ |
| 1.11 | Add queue depth monitoring and alerts | P2 | ⬜ |
| 1.12 | Add worker concurrency from config (not hardcoded) | P1 | ⬜ |

### Queue Manager
| # | Task | Priority | Status |
|---|------|----------|--------|
| 1.13 | Add queue priority (manual exports before scheduled) | P2 | ⬜ |
| 1.14 | Add queue deduplication (don't enqueue same label+profile twice) | P1 | ⬜ |
| 1.15 | Add queue max size enforcement (prevent memory issues) | P1 | ⬜ |
| 1.16 | Add per-school queue isolation | P2 | ⬜ |

---

## Phase 2: Frontend Rebuild (Days 8-12)

### Manual Export Page
| # | Task | Priority | Status |
|---|------|----------|--------|
| 2.1 | Redesign school/group tree with search + multi-select | P0 | ⬜ |
| 2.2 | Add keyboard navigation (↑↓ Space Enter) | P1 | ⬜ |
| 2.3 | Add "Select All" / "Deselect All" per school | P0 | ⬜ |
| 2.4 | Add recent selections persistence | P1 | ⬜ |
| 2.5 | Add export template save/load/delete | P0 | ⬜ |
| 2.6 | Add real-time preview with document count | P0 | ⬜ |
| 2.7 | Add progress bar during export | P1 | ⬜ |
| 2.8 | Add batch export confirmation dialog | P1 | ⬜ |
| 2.9 | Add "Export All Schools" quick action | P2 | ⬜ |

### Settings Page
| # | Task | Priority | Status |
|---|------|----------|--------|
| 2.10 | Add Export Root configuration | P0 | ⬜ |
| 2.11 | Add Worker configuration (concurrency, interval) | P0 | ⬜ |
| 2.12 | Add Notification channels CRUD | P0 | ⬜ |
| 2.13 | Add Backup management (create, list, restore) | P1 | ⬜ |
| 2.14 | Add Log viewer with search/filter | P1 | ⬜ |
| 2.15 | Add Theme toggle (light/dark/system) | P0 | ⬜ |
| 2.16 | Add Timezone setting | P1 | ⬜ |
| 2.17 | Add Automatic cleanup configuration | P0 | ⬜ |

### Schools (Organizations) Page
| # | Task | Priority | Status |
|---|------|----------|--------|
| 2.18 | Redesign as School cards with expandable sections | P0 | ⬜ |
| 2.19 | Add inline credential test button | P0 | ⬜ |
| 2.20 | Add credential health indicator (green/yellow/red) | P0 | ⬜ |
| 2.21 | Add group management within school card | P0 | ⬜ |
| 2.22 | Add school import/export | P2 | ⬜ |
| 2.23 | Add school statistics (exports, failures, last export) | P1 | ⬜ |

### General UI
| # | Task | Priority | Status |
|---|------|----------|--------|
| 2.24 | Remove all remaining placeholder text | P0 | ⬜ |
| 2.25 | Add loading skeletons for all data views | P1 | ⬜ |
| 2.26 | Add error boundaries for all components | P0 | ⬜ |
| 2.27 | Add empty states with CTAs for all views | P0 | ⬜ |
| 2.28 | Add toast notifications for all mutations | P0 | ⬜ |
| 2.29 | Add confirmation dialogs for destructive actions | P0 | ⬜ |
| 2.30 | Add keyboard shortcuts (⌘K palette, ⌘Enter export) | P2 | ⬜ |

---

## Phase 3: Export Formats & Profiles (Days 13-15)

### Format Expansion
| # | Task | Priority | Status |
|---|------|----------|--------|
| 3.1 | Add PARASOLID format back with quality presets | P0 | ⬜ |
| 3.2 | Add GLTF format for web/AR viewing | P1 | ⬜ |
| 3.3 | Add DXF format for 2D drawings | P1 | ⬜ |
| 3.4 | Add PDF format for drawing exports | P2 | ⬜ |
| 3.5 | Add OBJ format with MTL material support | P1 | ⬜ |
| 3.6 | Add "Native Backup" format (Onshape native format) | P2 | ⬜ |
| 3.7 | Keep STL, STEP, 3MF as primary formats | P0 | ✅ |

### Profile Presets
| # | Task | Priority | Status |
|---|------|----------|--------|
| 3.8 | Create STEP — Maximum Quality preset | P0 | ⬜ |
| 3.9 | Create STEP — Balanced preset | P0 | ⬜ |
| 3.10 | Create STEP — Small Files preset | P1 | ⬜ |
| 3.11 | Create STL — High Resolution preset | P0 | ⬜ |
| 3.12 | Create STL — 3D Printing preset | P0 | ⬜ |
| 3.13 | Create STL — Low Poly preset | P1 | ⬜ |
| 3.14 | Create Parasolid preset | P0 | ⬜ |
| 3.15 | Create GLTF preset | P1 | ⬜ |
| 3.16 | Add profile description field explaining use case | P1 | ⬜ |
| 3.17 | Add profile duplicate functionality | P0 | ⬜ |
| 3.18 | Add profile preview (estimated size, format count) | P1 | ⬜ |

---

## Phase 4: Production Hardening (Days 16-18)

### Error Handling
| # | Task | Priority | Status |
|---|------|----------|--------|
| 4.1 | Add user-friendly error messages (not stack traces) | P0 | ⬜ |
| 4.2 | Add retry suggestions in error messages | P1 | ⬜ |
| 4.3 | Add API error codes for programmatic handling | P1 | ⬜ |
| 4.4 | Add network error recovery in frontend | P0 | ⬜ |
| 4.5 | Add offline detection and graceful degradation | P2 | ⬜ |

### Logging
| # | Task | Priority | Status |
|---|------|----------|--------|
| 4.6 | Add structured JSON logging | P0 | ⬜ |
| 4.7 | Add log rotation by size (10MB) | P0 | ⬜ |
| 4.8 | Add log export to file | P1 | ⬜ |
| 4.9 | Add per-school export logs | P2 | ⬜ |
| 4.10 | Add performance metrics logging (export duration, API latency) | P1 | ⬜ |

### Security
| # | Task | Priority | Status |
|---|------|----------|--------|
| 4.11 | Add CSRF protection for mutations | P0 | ⬜ |
| 4.12 | Add session timeout (configurable) | P1 | ⬜ |
| 4.13 | Add rate limiting per endpoint | P0 | ⬜ |
| 4.14 | Sanitize file paths to prevent traversal | P0 | ⬜ |
| 4.15 | Add audit log for all mutations | P1 | ⬜ |

### Testing
| # | Task | Priority | Status |
|---|------|----------|--------|
| 4.16 | Fix flaky test_export_engine test | P0 | ⬜ |
| 4.17 | Add integration tests for full export pipeline | P1 | ⬜ |
| 4.18 | Add UI component tests | P2 | ⬜ |
| 4.19 | Add API contract tests | P1 | ⬜ |
| 4.20 | Add performance benchmark tests | P2 | ⬜ |
| 4.21 | Add database migration tests (forward + rollback) | P1 | ⬜ |

---

## Phase 5: Polish & Documentation (Days 19-21)

### Documentation
| # | Task | Priority | Status |
|---|------|----------|--------|
| 5.1 | Write ARCHITECTURE.md | P0 | ⬜ |
| 5.2 | Write API.md with all endpoints | P0 | ⬜ |
| 5.3 | Write DATABASE.md with schema | P0 | ⬜ |
| 5.4 | Write WORKFLOW.md with user guides | P0 | ⬜ |
| 5.5 | Write DEPLOY.md for Raspberry Pi | P0 | ⬜ |
| 5.6 | Write TESTING.md with test strategy | P1 | ⬜ |
| 5.7 | Write KNOWN_LIMITATIONS.md | P1 | ⬜ |
| 5.8 | Update README.md with current state | P0 | ⬜ |

### Deployment
| # | Task | Priority | Status |
|---|------|----------|--------|
| 5.9 | Create systemd service file | P0 | ⬜ |
| 5.10 | Create Dockerfile for container deployment | P1 | ⬜ |
| 5.11 | Add startup health check script | P1 | ⬜ |
| 5.12 | Add backup/restore script | P1 | ⬜ |
| 5.13 | Add update/migration script | P1 | ⬜ |

### Final Audit
| # | Task | Priority | Status |
|---|------|----------|--------|
| 5.14 | Full UI audit — every button, every page | P0 | ⬜ |
| 5.15 | Full API audit — every endpoint | P0 | ⬜ |
| 5.16 | Full database audit — schema, indexes, constraints | P0 | ⬜ |
| 5.17 | Performance audit — large dataset simulation | P1 | ⬜ |
| 5.18 | Security audit — OWASP top 10 | P1 | ⬜ |
| 5.19 | Accessibility audit — WCAG 2.1 AA | P2 | ⬜ |
| 5.20 | 24-hour stability test on Raspberry Pi | P1 | ⬜ |

---

## Priority Legend
- **P0** — Must complete before v0.3.0 release
- **P1** — Should complete for production readiness
- **P2** — Nice to have, can be post-v0.3.0

## Total Tasks: 107
- Phase 0: 13 tasks
- Phase 1: 16 tasks
- Phase 2: 30 tasks
- Phase 3: 18 tasks
- Phase 4: 21 tasks
- Phase 5: 20 tasks
