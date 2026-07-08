# Feature Inventory

## Implemented Features (✅ Complete)

### Authentication & Security
- [x] Single-owner account (scrypt password hashing)
- [x] TOTP two-factor authentication
- [x] Session tokens (SHA-256 hashed, 12h/30d TTL)
- [x] Login rate limiting (5/min per IP)
- [x] API rate limiting (120/min per IP)
- [x] Setup wizard (first-run)
- [x] HttpOnly/Secure cookies

### Onshape Integration
- [x] REST API client (documents, labels, Part Studios, Assemblies)
- [x] Multi-format export (STL, STEP, PARASOLID, OBJ, IGES, DXF, PDF)
- [x] Multi-Part Studio iteration
- [x] Account health tracking (healthy/degraded/rate_limited/failed)
- [x] API usage counting
- [x] Credential testing

### Export Engine
- [x] Automatic document discovery by label
- [x] Timestamped output directories
- [x] Export history (success/failure tracking)
- [x] Retry with exponential backoff (max 4 attempts)
- [x] Configurable timeouts (request 30s, export 120s)

### Queue System
- [x] Atomic job claiming (SQLite UPDATE...RETURNING)
- [x] Job state machine (pending → running → completed/failed/cancelled)
- [x] Retry scheduling with backoff
- [x] Job chaining (up to 3 depth)
- [x] Batch cancel/retry
- [x] Queue stats (GROUP BY query)

### Worker
- [x] Multi-threaded (configurable, default 4)
- [x] Config caching (5s TTL)
- [x] Graceful shutdown (30s timeout)
- [x] Start/stop via UI and API
- [x] Job timeout enforcement

### Scheduler
- [x] Recurring exports per Group
- [x] Intervals: 15min, 30min, hourly, daily, weekly, monthly
- [x] Labels-changed event re-sync
- [x] Timezone support

### Configuration
- [x] JSON config files (5 files)
- [x] Pydantic strict validation
- [x] Cross-reference validation (accounts, profiles)
- [x] Environment variable secrets (`env:VAR`)
- [x] Config hot-reload (mtimes polling)
- [x] Atomic file writes (tmp + rename)

### Web UI
- [x] Dashboard with charts (Chart.js: activity line, health donut)
- [x] Glassmorphism dark theme
- [x] Light/dark theme toggle
- [x] Collapsible sidebar
- [x] Tree view (Accounts → Groups)
- [x] Group CRUD (create, update, delete, move, enable/disable)
- [x] Manual export with tree selector
- [x] Manual export with detailed form (profile, dates, preview)
- [x] Export history table (sortable, filterable)
- [x] Settings tabs (6 tabs)
- [x] Toast notifications
- [x] Live updates (SSE + WebSocket)
- [x] Reactive UI (Alpine.js)

### API
- [x] 55+ REST endpoints
- [x] Pydantic request validation
- [x] Consistent error responses (401/400/404/422)
- [x] WebSocket event stream
- [x] SSE metrics stream

### Organizations & Credentials
- [x] Organization CRUD
- [x] Credential management (add, delete, test)
- [x] Organization duplication
- [x] Import from flat accounts.json
- [x] Priority-based selection

### Notifications
- [x] Multi-channel (Discord, Slack, Teams, Email, Webhook)
- [x] Severity filtering
- [x] Category-based routing
- [x] Test delivery

### System
- [x] CPU/RAM/Disk/Temperature monitoring
- [x] Remote access status (Tailscale, Cloudflare)
- [x] Backup/restore (config + DB)
- [x] Log viewer (per-area, 300 lines)
- [x] Database migrations (v1→v3)

### Terminal UI
- [x] 22 CLI commands
- [x] Interactive setup wizard
- [x] QR code generation
- [x] Live metrics display

### Testing
- [x] 183 tests (pytest)
- [x] Web API tests (33)
- [x] CLI tests (17)
- [x] Unit tests for all core modules

---

## Partially Implemented (⚠️ Needs Work)

- [~] Input sanitization — Alpine escapes HTML but no server-side sanitization
- [~] Search — global search endpoint exists, UI is placeholder
- [~] Mobile responsive — basic hamburger menu, not fully tested
- [~] Empty states — some pages lack designed empty states
- [~] Error messages — some toasts show raw "error" instead of descriptive messages — **FIXED**

---

## Not Implemented (❌ Future)

- [ ] Bambu Studio direct integration (3MF generation)
- [ ] S3/SFTP export destinations
- [ ] Multi-user support
- [ ] Export diff/comparison
- [ ] Custom export format plugins
- [ ] Webhook export triggers
- [ ] OLED/LCD display (Raspberry Pi)
- [ ] GPIO button integration
- [ ] Drag-and-drop group reordering
- [ ] Undo for destructive operations
- [ ] Pagination for history
- [ ] Keyboard shortcuts
- [ ] Dark/light theme persistence across sessions
- [ ] Production Tailwind CSS build (currently using CDN)
