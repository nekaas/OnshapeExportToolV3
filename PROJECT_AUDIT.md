# Project Audit

**Date:** 2026-07-08
**Tests:** 183 passing, 0 failing
**Version:** 0.1.0

## Overall Assessment

The project is in a solid mid-development state. Core export functionality works end-to-end. The web UI is functional across all pages. Documentation was recently overhauled to match implementation. Remaining work focuses on polish, edge cases, and advanced features.

## What Works Well

1. **Export pipeline** — label → document discovery → format translation → file output is reliable
2. **Queue system** — atomic claiming prevents duplicate processing
3. **Multi-worker** — thread pool handles concurrent exports
4. **Config system** — JSON with Pydantic validation, hot-reload, env var secrets
5. **Tree UI** — Account → Group hierarchy with full CRUD
6. **Dashboard** — charts, health indicators, at-a-glance status
7. **Test suite** — 183 tests covering all core modules

## What Needs Attention

### High Priority
1. **Server-side input sanitization** — XSS in group names (mitigated by Alpine but not prevented)
2. **Special character handling** — Groups with `<`, `>`, `/` can't be deleted via UI
3. **Error message quality** — Some toasts show generic "error" instead of descriptive messages
4. **422 error on export page** — Some API call returns 422 during page load

### Medium Priority
5. **Tailwind CDN** — Should be compiled for production
6. **Loading states** — "Loading…" text instead of skeletons
7. **Empty states** — Inconsistent across pages
8. **Mobile responsiveness** — Hamburger menu exists but not fully tested
9. **Search UI** — Endpoint exists but UI is non-functional placeholder

### Low Priority
10. **Pagination** — History table loads all rows
11. **Undo** — No undo for delete operations
12. **Drag-and-drop** — Group reordering not implemented
13. **Keyboard shortcuts** — ⌘K is placeholder

## Architecture Health

| Concern | Status |
|---------|--------|
| Module coupling | Moderate — Application container is central hub |
| Thread safety | Good — locks on ApiPool, CredentialPool, EventBus |
| Error handling | Good — try/catch in worker, consistent API error format |
| Logging | Good — structured JSON + text, per-area log files |
| Test coverage | Good — 183 tests, core paths covered |
| Config validation | Good — Pydantic strict, cross-reference checks |
| Migration strategy | Good — versioned SQL migrations |

## Technical Debt

1. **sectionPage monolith** — One Alpine component handles all non-dashboard pages (~1000 lines)
2. **fetchJSON inconsistency** — Some code uses `fetchJSON()`, some uses raw `fetch()`
3. **app.js size** — ~1700 lines, should be split into modules
4. **Template duplication** — Some HTML patterns repeated across templates
5. **No TypeScript** — Alpine.js components are plain JS without type checking
6. **No frontend build step** — Tailwind CDN, no minification, no bundling
