# Feature Removal Proposals — Onshape Export Manager

**Status:** WAITING FOR USER APPROVAL on all items  
**Principle:** Remove anything that doesn't directly support the core mission: exporting Onshape CAD files from school accounts.

---

## Proposal #1: Remove Notifications System

**Current Feature:** Multi-channel notification delivery (Discord, Slack, Teams, Email, Webhook) with CRUD UI, per-channel severity filtering, test-delivery endpoint.

**Reason It Exists:** Built for a multi-user SaaS scenario where admins need alerts.

**Problems:**
- Single-user appliance — the admin IS the only person who would receive notifications
- 6 API endpoints, 200+ lines of UI template, entire `notifications.py` module
- NotificationService runs a background thread on every server start
- Adds complexity to setup, config, testing

**Suggested Replacement:** Remove entirely. If the admin wants to know if an export failed, they check the History page or look at the terminal.

**Benefits:** ~500 lines removed, 6 endpoints removed, 1 background thread eliminated, simpler settings page.

**Risk:** Low. A single-user local appliance doesn't need push notifications.

**Confidence:** 95%

**Recommendation:** STRONGLY RECOMMEND REMOVAL

---

## Proposal #2: Remove Plugin System

**Current Feature:** Plugin hooks architecture (`plugins.py`), UI page with 6 plugin categories, no actual plugins exist.

**Reason It Exists:** Future-proofing for extensibility.

**Problems:**
- Zero plugins have ever been created
- The plugin architecture adds indirection without value
- UI shows placeholder descriptions for plugins that don't exist
- Creates false expectation of extensibility

**Suggested Replacement:** Remove entirely. If extensibility is needed later, add it when there's a concrete use case.

**Benefits:** ~100 lines removed, 1 module eliminated, simpler architecture.

**Risk:** Low. Can be re-added if needed.

**Confidence:** 90%

**Recommendation:** RECOMMEND REMOVAL

---

## Proposal #3: Remove TOTP Two-Factor Authentication

**Current Feature:** TOTP-based 2FA with QR code provisioning, backup codes, TOTP verification on login.

**Reason It Exists:** Security best practice for web applications.

**Problems:**
- The application runs on a Raspberry Pi on a local network
- Single administrator, not exposed to the internet
- scrypt password hashing is already secure for local use
- 2FA adds friction to every login with no real security benefit in this deployment model

**Suggested Replacement:** Remove TOTP. Keep scrypt password hashing. If remote access is needed, use Tailscale or SSH tunneling — don't expose the app directly.

**Benefits:** Simpler login flow, less code, fewer things to break.

**Risk:** Low for intended deployment model.

**Confidence:** 85%

**Recommendation:** RECOMMEND REMOVAL

---

## Proposal #4: Remove Command Palette (⌘K)

**Current Feature:** Keyboard shortcut ⌘K opens a fuzzy-search palette to navigate between pages and search items.

**Reason It Exists:** Power-user feature common in IDEs and SaaS dashboards.

**Problems:**
- The app has 4 navigation items — no fuzzy search needed
- Adds JavaScript complexity (~80 lines)
- Adds a UI element that most users will never discover
- The `/` keyboard shortcut conflicts with browser search

**Suggested Replacement:** Remove. The 4-item sidebar is already fast enough.

**Benefits:** Simpler JS, fewer event listeners, less confusion.

**Risk:** None.

**Confidence:** 95%

**Recommendation:** STRONGLY RECOMMEND REMOVAL

---

## Proposal #5: Remove Live SSE Streaming

**Current Feature:** Server-Sent Events stream for real-time dashboard updates and WebSocket for live activity feed.

**Reason It Exists:** Real-time updates feel modern and responsive.

**Problems:**
- Single user doesn't need sub-second updates
- SSE connection holds a server thread
- WebSocket adds protocol complexity
- 6-second polling already exists as fallback
- Dashboard is being simplified anyway

**Suggested Replacement:** Use polling only (already implemented as fallback). 6-second interval is sufficient for a single-user appliance.

**Benefits:** Simpler server, fewer connections, one less protocol to maintain.

**Risk:** Low. Polling is already working.

**Confidence:** 80%

**Recommendation:** RECOMMEND REMOVAL

---

## Proposal #6: Remove Config File Watcher (Hot Reload)

**Current Feature:** Background thread watches config files for changes and reloads configuration without restart.

**Reason It Exists:** Convenience for development and server deployments.

**Problems:**
- Single-user appliance — the admin can restart after config changes
- Adds a background thread and filesystem watcher
- Hot-reload can cause inconsistent state if config is partially written
- Rarely needed in production

**Suggested Replacement:** Remove. Config changes require a restart (`systemctl restart onshape-export-manager`).

**Benefits:** One less background thread, simpler state management.

**Risk:** Low. Config changes are infrequent.

**Confidence:** 85%

**Recommendation:** RECOMMEND REMOVAL

---

## Proposal #7: Remove Chart.js Dependency

**Current Feature:** Line chart (export activity) and doughnut chart (account health) on the Dashboard, rendered with Chart.js 4.4.

**Reason It Exists:** Visual dashboards look professional.

**Problems:**
- Single user doesn't need data visualization
- Charts show mostly zero/empty data
- Chart.js adds ~200KB to page load (CDN)
- Chart rendering code is ~100 lines of JS
- With Dashboard simplification, charts have no home

**Suggested Replacement:** Remove Chart.js. Replace with simple text badges showing key numbers (queue depth, last export, disk usage) on the Export page header.

**Benefits:** Faster page load, simpler JS, one less CDN dependency.

**Risk:** None — charts show no meaningful data.

**Confidence:** 90%

**Recommendation:** RECOMMEND REMOVAL

---

## Proposal #8: Remove Export Templates Feature

**Current Feature:** Save/load/favorite export templates with localStorage persistence, 3 default templates, template chips in UI.

**Reason It Exists:** Power users might want to save common export configurations.

**Problems:**
- Adds ~150 lines of JS for template management
- Default templates reference profiles that may not exist
- "undefined · undefined" bug was caused by template code
- Most users export ad-hoc, not from saved templates
- localStorage can be cleared accidentally

**Suggested Replacement:** Simply remember the last-used label, profile, and date selection in localStorage without the full template management UI.

**Benefits:** Simpler UI, fewer bugs, less JS.

**Risk:** Low — power users can adapt.

**Confidence:** 75%

**Recommendation:** RECOMMEND SIMPLIFICATION

---

## Proposal #9: Rename "Organizations" → "Schools"

**Current Feature:** The term "Organizations" is used throughout the codebase, UI, API, and config files.

**Reason It Exists:** Generic term chosen during initial development.

**Problems:**
- Target users are SCHOOLS, not generic organizations
- "Organization" has no specific meaning in this context
- "School" is immediately understood by the target audience
- Config files, API endpoints, and database columns all use the wrong term

**Suggested Replacement:** Rename everywhere.

**Benefits:** Clearer product, better mental model for users.

**Risk:** Medium — requires migration of config files and database.

**Confidence:** 95%

**Recommendation:** STRONGLY RECOMMEND

---

## Proposal #10: Merge Dashboard into Export Page

**Current Feature:** Separate Dashboard page (/) with stats cards, charts, recent exports, and health indicators.

**Reason It Exists:** Standard web app pattern — dashboard as landing page.

**Problems:**
- The admin doesn't come to the app to "see a dashboard"
- They come to EXPORT files
- Dashboard adds an extra click before the real work begins
- Cards show data that's already visible on other pages
- Charts show no meaningful data for a single user

**Suggested Replacement:** Make Export (/) the home page. Add compact status badges to the Export page header showing: queue depth, disk usage, last export time, healthy schools count.

**Benefits:** One less page, faster workflow, the admin starts exactly where they need to be.

**Risk:** Low — all dashboard data is available elsewhere.

**Confidence:** 90%

**Recommendation:** STRONGLY RECOMMEND

---

## Proposal #11: Consolidate 5 Config Files into 3

**Current Feature:** Separate JSON files: `config.json`, `accounts.json`, `labels.json`, `export_profiles.json`, `organizations.json`.

**Problems:**
- 5 files to manage, back up, and validate
- Cross-references between files are fragile
- `accounts.json` and `organizations.json` overlap in purpose
- Labels reference accounts that live in organizations
- Adding a school requires editing 3 files

**Suggested Replacement:** Consolidate to 3 files:
1. `config.json` — app settings (worker, paths, timeouts)
2. `schools.json` — schools with embedded credentials and groups
3. `profiles.json` — export profiles

**Benefits:** Fewer files, simpler cross-references, easier backup.

**Risk:** Medium — requires config migration.

**Confidence:** 85%

**Recommendation:** RECOMMEND

---

## Proposal #12: Remove Event/Audit System

**Current Feature:** EventBus with pub/sub, AuditService, TelemetryStore, EventType enum, event persistence to SQLite, WebSocket streaming, activity feed UI page.

**Problems:**
- Over-engineered for a single-user appliance
- Events table grows unboundedly
- Activity feed page shows system events no one needs to see
- Audit for compliance is irrelevant — there's one user
- ~500 lines across multiple modules

**Suggested Replacement:** Log to file only. Keep structured logging for debugging. Remove event table, event bus, audit service, telemetry store, activity feed UI.

**Benefits:** ~500 lines removed, simpler architecture, no unbounded table growth.

**Risk:** Low — logs serve the same debugging purpose.

**Confidence:** 80%

**Recommendation:** RECOMMEND SIMPLIFICATION

---

## Summary

| # | Proposal | Impact | Confidence | Recommendation |
|---|----------|--------|------------|---------------|
| 1 | Remove Notifications | ~500 lines | 95% | STRONGLY RECOMMEND |
| 2 | Remove Plugins | ~100 lines | 90% | RECOMMEND |
| 3 | Remove TOTP 2FA | ~150 lines | 85% | RECOMMEND |
| 4 | Remove Command Palette | ~80 lines JS | 95% | STRONGLY RECOMMEND |
| 5 | Remove SSE Streaming | ~100 lines | 80% | RECOMMEND |
| 6 | Remove Config Watcher | ~50 lines | 85% | RECOMMEND |
| 7 | Remove Chart.js | ~100 lines JS | 90% | RECOMMEND |
| 8 | Simplify Templates | ~150 lines JS | 75% | RECOMMEND |
| 9 | Rename Orgs→Schools | Terminology | 95% | STRONGLY RECOMMEND |
| 10 | Dashboard→Export home | UX change | 90% | STRONGLY RECOMMEND |
| 11 | Consolidate configs | Architecture | 85% | RECOMMEND |
| 12 | Simplify Events/Audit | ~500 lines | 80% | RECOMMEND |

**Total potential removal: ~1,730 lines of code, 8+ API endpoints, 3 background threads.**

**All proposals require USER APPROVAL before implementation.**
