# Changelog

## [0.1.0] — 2026-07-08

### Added
- Tree-based Account → Groups hierarchy with full CRUD
- Group management UI: create, delete, move, enable/disable
- Tree selector on Export page for batch group selection
- Group API endpoints: POST/GET/PUT/DELETE /api/groups, PUT /api/groups/{name}/move
- UpdateGroupRequest Pydantic model
- GET /api/tree endpoint returning accounts with nested groups
- NAV_ITEMS "Labels" renamed to "Groups"
- ManualExportRequest.labels array for batch exports
- Project documentation suite (13 documents)
- Preview template null-safety with optional chaining

### Fixed
- Preview null-access JS errors on Export page (Alpine `x-if` child evaluation)
- Authentication middleware properly returning 401 for all protected endpoints
- XSS via group names mitigated (Alpine `x-text` escapes HTML)

### Changed
- Labels page replaced with tree-based Groups page
- Export page now includes tree selector above manual export form
- Sidebar nav consolidated to 5 primary items

---

## [0.0.0] — Prior Sessions

### Core Infrastructure
- Python 3.13, FastAPI 0.115, uvicorn 0.30
- SQLite WAL mode, versioned migrations (v1→v3)
- Single-owner auth (scrypt, TOTP, sessions)
- Jinja2 templates with Alpine.js, Chart.js, Tailwind CSS

### Export Engine
- Onshape REST API client
- Multi-format export (STL, STEP, PARASOLID, OBJ, IGES, DXF, PDF)
- Multi-Part Studio iteration
- Background worker pool (4 threads)
- Atomic queue (UPDATE...RETURNING)
- Retry with exponential backoff

### Configuration
- JSON config with Pydantic strict validation
- Config hot-reload (ConfigWatcher)
- Environment variable secrets (`env:VAR`)
- Cross-reference validation

### UI
- Dashboard with Chart.js (activity line, health donut)
- Glassmorphism dark/light theme
- Collapsible sidebar
- API Keys management (organizations + credentials)
- Export history table
- Settings with 6 tabs
- Terminal UI (22 commands, setup wizard)

### Testing
- 183 tests across all core modules
- Web API tests (33), CLI tests (17), unit tests (133)

### Fixes
- EventBus.subscribe parameter name mismatch
- Worker config caching (5s TTL)
- Thread-safe API pool and credential pool
- UTC-aware datetime handling
- Multi-worker graceful shutdown
