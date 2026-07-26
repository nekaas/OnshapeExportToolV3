# Product Audit — Onshape Export Manager v0.6

**Auditor:** Senior Product Architect  
**Date:** 2026-07-26 (updated)  
**Status:** Simplifications 85% complete. Remaining: UX-001 (duplicate group selectors), UX-003 (hardcoded profiles), make Export the home page.

---

## Simplification Status

| Proposal | Status |
|----------|--------|
| Remove TOTP 2FA | ✅ |
| Remove command palette (⌘K) | ✅ |
| Remove SSE streaming → polling | ✅ |
| Remove Chart.js → status bar | ✅ |
| Remove template management → localStorage | ✅ |
| Remove WebSocket activity feed | ✅ |
| Remove config file watcher | ✅ |
| Simplify event/audit (keep SQLite) | ✅ |
| Email + audio notification stubs | ✅ |
| Rename Organizations → Schools (UI) | ✅ |
| Remove plugins system | 🔴 Pending |
| Make Export the home page | 🔴 Pending |
| Consolidate duplicate group selectors | 🔴 Pending |

---

## Executive Summary

This application has **scope creep**. It contains features appropriate for a SaaS platform but inappropriate for a single-user Raspberry Pi appliance. Approximately **40% of current features** add complexity without adding value for the target user.

The core value proposition — "export Onshape CAD files from multiple school accounts" — is solid. But the application has accumulated features (notifications, plugins, command palette, TOTP 2FA, live dashboards, system monitoring widgets, hot-reload config) that belong in a different product.

### Key Findings

| Area | Verdict |
|------|---------|
| Core export workflow | ✅ Essential, needs simplification |
| Dashboard | ⚠️ Useful but overbuilt for single-user |
| Settings tabs | ❌ 4 of 6 tabs have no real functionality |
| Notifications | ❌ Remove — single-user appliance |
| Plugins | ❌ Remove — never used |
| Config files | ❌ 5 JSON files, consolidate to 3 |
| Terminology | ❌ "Organizations" → "Schools" |
| Command palette | ❌ Remove — 4 nav items don't need search |
| TOTP 2FA | ❌ Overkill for local appliance |
| Live SSE streaming | ⚠️ Simplify to polling only |

### Recommended Page Count: 4 (from current 5+6 settings tabs)

1. **Export** (Home page — what the admin does 90% of the time)
2. **Schools** (manage credentials + groups)
3. **History** (past exports, filterable)
4. **Settings** (3 tabs: General, Cleanup, About)

---

## Detailed Page-by-Page Analysis

### Dashboard (/)
- **Purpose:** Overview of system state
- **Who uses it:** Admin glances at it on login
- **Problems:** Charts render with fake/zero data, success rate shows 20% from 4 failed test exports, account health shows 3 healthy from stale data. The charts library (Chart.js) is loaded but shows no meaningful data for a single user.
- **Recommendation:** REMOVE as standalone page. Move key stats (queue depth, last export time, disk usage) into the Export page header as compact badges.

### Organizations (/organizations)
- **Purpose:** Manage schools, credentials, and groups
- **Problems:** "Organizations" is confusing. Form has duplicate implementations (treeSelector vs sectionPage stubs). Inline forms are complex.
- **Recommendation:** RENAME to "Schools". Simplify to card-based layout. MERGE groups directly into the school cards (already done in current UI).

### Export (/export)  
- **Purpose:** THE core workflow
- **Problems:** Too many sub-sections (tree selector, manual export form, date window, templates, preview panel, queue panel). Two separate "Export Selected" buttons. Templates are confusing. Preview shows estimates not real data.
- **Recommendation:** MAKE THIS THE HOME PAGE. Simplify to: School tree → tick groups → pick profile → pick date → preview → export. Remove templates feature (low usage, adds complexity). Remove date presets (just use a date picker).

### History (/history)
- **Purpose:** View past exports
- **Problems:** Filterable table works fine. Shows 5 test exports mixed with real ones.
- **Recommendation:** KEEP. Add "Clear test data" button.

### Settings (/settings) — 6 tabs
| Tab | Status | Recommendation |
|-----|--------|---------------|
| General | Worker controls + theme + cleanup | KEEP, merge cleanup here |
| Notifications | Discord/Slack/Teams/webhook CRUD | REMOVE — single-user appliance doesn't need push notifications |
| Backups | Create/list backups | MOVE to General tab as a button |
| Remote Access | Tailscale/Cloudflare status | KEEP as read-only info in General |
| Logs | Log viewer | REPLACE with "Download logs" button |
| About | Version + DB stats | KEEP, simplified |

---

## Feature Audit Summary

| Feature | Verdict | Reason |
|---------|---------|--------|
| Notifications (Discord/Slack/Teams/webhook) | ❌ REMOVE | Single-user appliance. Admin is the only user. |
| Plugins system | ❌ REMOVE | Never implemented, never used, zero plugins exist |
| TOTP 2FA | ❌ REMOVE | Overkill. scrypt password is sufficient for local device |
| Command palette (⌘K) | ❌ REMOVE | 4 nav items don't need fuzzy search |
| Live SSE streaming | ⚠️ SIMPLIFY | Replace with 6s polling only |
| Config file watcher (hot reload) | ❌ REMOVE | Single-user, restart to apply config |
| Bambu Studio integration | ⚠️ SIMPLIFY | Niche. Keep as optional CLI flag, remove from UI |
| Export templates | ❌ REMOVE | Low usage. Just remember last-used settings in localStorage |
| Date presets (Today, This Week, etc.) | ⚠️ SIMPLIFY | Keep "Today" and "Custom Range" only |
| Chart.js dependency | ❌ REMOVE | No meaningful data to chart for single user |
| System monitoring (CPU/RAM/disk) | ⚠️ SIMPLIFY | Show in Settings only, not dashboard |
| Event/audit system | ❌ REMOVE | Over-engineered for single-user. Log to file. |
| Scheduler | ✅ KEEP | Essential for automation |
