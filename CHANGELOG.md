# Changelog

All notable changes to Onshape Export Manager.

## [0.1.0] — 2026-07-08

### Added
- Multi-account Onshape API pool with rate-limit-aware failover
- Label-driven document discovery and export
- 8 default export profiles (STL, STEP, OBJ, IGES, Parasolid, Mesh Bundle, CAD Bundle, Multi Format)
- Manual export via CLI and web UI with date range filtering
- Cron-style scheduler (15min, 30min, hourly, daily, weekly, monthly)
- Job queue with exponential backoff retry and atomic claims
- Export history with filtering by label, status, and date
- Multi-channel notifications (Discord, Slack, Teams, Email, Webhook)
- FastAPI web dashboard with real-time monitoring
- CLI with 14 commands for headless operation
- Background worker daemon with config caching and timeout enforcement
- Single-owner authentication (scrypt + TOTP 2FA)
- Pydantic-validated JSON configuration with `env:` secret references
- SQLite database with WAL mode and versioned migrations
- Rotating per-area log files with structured JSON option
- ZIP backup/restore with safety snapshot and integrity verification
- System monitoring (CPU, RAM, disk, temperature, Pi detection)
- Event bus with pub/sub for audit logging and notifications
- API rate limiting (login + API endpoints)
- Export archive download from web UI
- Docker containerization (amd64) with docker-compose

### Changed
- Export engine now exports all Part Studios per document (was first only)
- Document filenames include short doc-ID suffix to prevent collisions
- Queue stats use single GROUP BY query (was 5 separate queries)
- Worker uses config caching with 5s TTL (was per-job reload)
- Worker stop timeout increased to 30s with in-flight job awareness
- Queue claims are atomic via `UPDATE ... RETURNING *` (was TOCTOU race)
- Scheduler re-syncs on label changes via EventBus subscription
- ApiPool and CredentialPool are thread-safe (added threading.Lock)

### Removed
- Bambu Studio integration (non-functional stub — planned as V2 plugin)
- Plugin system (protocol with no implementation — planned as V2 extension point)
- `textual` dependency (never imported)
- `apscheduler` dependency (custom scheduler used instead)
- `cryptography` dependency (all crypto is stdlib)
- HTMX CDN script (loaded but never used)
- Bambu STL default export profile
- Bambu config section from default config.json
- Plugins nav item from dashboard sidebar

### Fixed
- TOCTOU race in queue claim (could double-process jobs under concurrency)
- Data race in ApiPool/CredentialPool state mutation (web thread vs worker thread)
- Scheduler not re-syncing after label changes (stale jobs from deleted labels)
- Database corruption risk during backup restore (no WAL checkpoint before overwrite)
- No rate limiting on login or API endpoints
- Only first Part Studio per document exported
- Document name collisions when two docs share a name in the same label
- 5 separate SQL queries for queue stats

[0.1.0]: https://github.com/your-org/onshape-export-manager/releases/tag/v0.1.0
