# Master UI Plan

## Page Inventory

### 1. Dashboard (`/`)
**Purpose:** System overview at a glance.
**Components:**
- Stat cards row (API Keys, Labels, Total Exports, In Queue, Failed)
- Export Activity chart (Chart.js line, 14-day success vs failed)
- Account Health donut (Chart.js)
- Success Rate panel (percentage + counts)
- Queue breakdown (pending, running, completed, failed, cancelled)
- Storage panel (disk usage, file count, DB schema version)
- Recent Exports table (last 5)

**States:** Loading (spinners), Empty ("No exports yet"), Error (toast)

### 2. API Keys (`/api-keys`)
**Purpose:** Manage Onshape credentials.
**Components:**
- New Organization form (name, type, description)
- Organization cards with credential tables
- Credential rows: name, environment, health, priority, usage, access key (masked), Test/Delete buttons
- "+ Add API Key" button per org
- Import from Accounts button
- Duplicate/Delete org buttons

**States:** Empty ("No organizations"), Loading, Test in progress (spinner)

### 3. Groups (`/labels`)
**Purpose:** Manage Groups in Account → Group tree hierarchy.
**Components:**
- "Export Selected" button with selection count badge
- Create Group form (name, Onshape ID, profile, schedule)
- Delete confirmation dialog
- Tree: Accounts (expandable) → Groups
- Per-group: checkbox, name, enable/disable toggle, profile badge, move dropdown, delete button
- "+ Create Group" button per account

**States:** Loading ("Loading…"), Empty ("No Accounts Configured"), Create form open/closed, Delete confirm

### 4. Export (`/export`)
**Purpose:** Manual export with tree selector + detailed form.
**Components:**
- Tree selector (Select Groups) — compact version of Groups tree
- "Export Selected" button for batch
- Manual Export form: Group dropdown, Profile override, Destination path
- Date Window: Range/Single Day toggle, presets (Today, Yesterday, This Week, etc.), Flatpickr date pickers
- Saved Templates (save/load/favorite export configurations)
- Export Preview panel: estimate cards (Documents, API Calls, Runtime, Storage), summary list, validation checks
- Queue status table (below export form)

**States:** Preview loading, Preview ready, Preview failed, Export queued toast

### 5. History (`/history`)
**Purpose:** Browse completed/failed exports.
**Components:**
- Filter input (text search)
- Data table: Started, Label, Profile, Account, Files, Duration, Result
- Sortable columns
- Download link per export

**States:** Empty ("No exports recorded"), Loading

### 6. Settings (`/settings`)
**Purpose:** System configuration.
**Tabs:**
- **General:** Appearance (Light/Dark), Worker status/control, System Health (CPU, RAM, Disk, Uptime)
- **Notifications:** Channel list, Create/Edit/Delete/Test channels
- **Backups:** Backup list, Create Backup button
- **Remote Access:** Network status, Tailscale info, proxy config
- **Logs:** Log area selector, log viewer (300 lines)
- **About:** Version, tech stack, links

**States:** Each tab loads independently, Loading per section

---

## UI Component Checklist

### Buttons
| Button | Page | Status |
|--------|------|--------|
| Export Selected | Groups, Export | ✅ |
| Create Group | Groups | ✅ |
| Delete Group | Groups | ✅ |
| Preview Export | Export | ✅ |
| Queue Export | Export | ✅ |
| Save Template | Export | ✅ |
| Favorite Template | Export | ✅ |
| Start/Stop Worker | Settings | ✅ |
| Create Backup | Settings | ✅ |
| Test Credential | API Keys | ✅ |
| Create Organization | API Keys | ✅ |
| Import from Accounts | API Keys | ✅ |
| Duplicate/Delete Org | API Keys | ✅ |
| Refresh | All pages | ✅ |
| Toggle Theme | Top bar | ✅ |

### Forms
| Form | Fields | Validation | Status |
|------|--------|------------|--------|
| Create Group | name, onshape_id, profile, schedule | Required, length, duplicate | ✅ |
| Create Organization | name, type, description | Required | ✅ |
| Add API Key | name, access_key, secret_key, env, priority | Required | ✅ |
| Manual Export | group, profile, destination, dates | Required group | ✅ |
| Create Notification | name, kind, target, severity | Required, format | ✅ |

### Interactive Elements
| Element | Page | Behavior | Status |
|---------|------|----------|--------|
| Tree expand/collapse | Groups, Export | Click account → toggle groups | ✅ |
| Tree checkboxes | Groups, Export | Check group/account → update count | ✅ |
| Date picker | Export | Flatpickr calendar | ✅ |
| Date presets | Export | Click → set date range | ✅ |
| Theme toggle | Top bar | Click → swap theme | ✅ |
| Sidebar collapse | Sidebar | Click → shrink/expand | ✅ |
| Table sorting | History | Click header → sort asc/desc | ✅ |
| Move dropdown | Groups | Select account → move group | ✅ |
| Enable/disable toggle | Groups | Click → toggle group active | ✅ |
| Delete confirmation | Groups | Click ✕ → show confirm → Delete | ✅ |
| Toast dismiss | All | Click × → dismiss | ✅ |

---

## Missing UI Features

1. **Loading skeletons** — currently shows "Loading…" text
2. **Mobile sidebar** — hamburger menu exists but needs testing
3. **Keyboard shortcuts** — ⌘K search is placeholder only
4. **Drag-and-drop** — for reordering groups (not implemented)
5. **Pagination** — history table loads all rows
6. **Bulk actions** — select multiple history rows for download/delete
7. **Undo** — no undo for delete operations
8. **Inline edit** — groups must be edited via API, no inline form
9. **Search** — global search endpoint exists but UI is placeholder
10. **Empty states** — some pages show raw "No X" text instead of designed empty states
