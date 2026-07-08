# Master UI Redesign Plan — Onshape Export Manager

> **Date**: 2026-07-08  
> **Design Team**: Senior Product Designer, Senior UX Designer, Senior Software Architect  
> **Status**: Design Phase — No implementation yet  
> **Goal**: Transform the Onshape Export Manager from a functional web dashboard into a polished commercial desktop application

---

## Design Principles

These principles guide every decision in this redesign plan. Every screen, every interaction, every label is evaluated against them:

1. **Self-Teaching** — The UI should teach itself. A first-time user should understand what to do without documentation.
2. **Intentional** — Nothing exists "because it might be useful." Every screen solves a specific problem.
3. **Discoverable** — Features are visible. Power-user features are accessible but not in the way.
4. **Minimal Clicks** — The most common action should be 1-2 clicks. No workflow should require more than 3.
5. **Coherent** — The application feels like one product, not independent pages stitched together.
6. **Desktop-First** — Designed for desktop use (Raspberry Pi touchscreen, laptop, monitor). Mobile is supported but not primary.
7. **Forgiving** — Destructive actions have undo. Mistakes are easy to recover from.
8. **Fast** — Perceived performance matters. Loading states, optimistic updates, and instant feedback.

---

## Phase 0: Information Architecture Restructure (Foundation)

**Priority**: Critical — Must be done first  
**Effort**: 16-24 hours (design + implementation)  
**Risk**: Medium — Changes navigation, which affects every page  
**Dependencies**: None (pure UI restructure)

### What Changes

The current 14-item sidebar navigation collapses to **7 primary destinations** plus a Settings gear:

| Before (14 items) | After (7 + Settings) | Rationale |
|---|---|---|
| Dashboard | **Home** | Renamed. More welcoming. |
| Organizations | *(merged)* | → |
| Accounts | **API Keys** | Unified. Flat list with optional org grouping. |
| Labels | **Labels** | Kept. Core domain concept. |
| Export Profiles | *(merged into Labels)* | Profiles are an attribute of labels. Configure inline. |
| Manual Export | **Export** | Renamed. Primary action. |
| Queue | *(merged into Export)* | Queue is the status of exports, not a separate page. |
| Scheduler | *(merged into Labels)* | Schedule is an attribute of labels. |
| History | **History** | Kept. Combined with Activity as sub-tabs. |
| Activity | *(merged into History)* | → |
| System | *(split)* | → |
| Logs | *(moved to Settings)* | → |
| Notifications | *(moved to Settings)* | → |
| Settings | **⚙ Settings** (gear icon, bottom of sidebar) | Contains: Preferences, Notifications, Logs, Backups, Remote Access, About |

### New Navigation Structure

```
┌─────────────────┐
│ 🏠 Home          │  ← Dashboard with guided onboarding
│ 🔑 API Keys      │  ← Unified accounts + organizations
│ 🏷 Labels         │  ← Labels with inline profiles + schedules
│ ⚡ Export         │  ← Manual export + queue status
│ 📋 History        │  ← Export history + activity log (tabs)
│                  │
│ ───────────────  │  ← Divider
│ ⚙ Settings        │  ← Gear icon at bottom
└─────────────────┘
```

### Design Rationale

**Why merge Organizations + Accounts?** The distinction between "an organization that contains credentials" and "a flat account" is an implementation detail. Users think in terms of "my Onshape API keys." The unified page shows all credentials in a card grid, with an optional "Group by Organization" toggle for multi-team deployments.

**Why merge Export Profiles into Labels?** A profile defines *how* a label's documents are exported. It makes no sense to configure profiles independently and then assign them to labels via a dropdown. Instead: when creating/editing a label, the user selects formats (STL, STEP, etc.) directly on the label form. The "profile" concept becomes a preset/template that can be saved and reused across labels.

**Why merge Queue into Export?** The queue is not a destination — it's the operational status of the export workflow. The Export page shows: (1) "New Export" form at the top, (2) "Active & Queued" status below. Users don't navigate to a separate page to check status.

**Why merge Scheduler into Labels?** A schedule is a property of a label: "Export this label every day at 3 PM." Configuring schedules on a separate page disconnected from the labels they affect is confusing.

**Why merge Activity into History?** Users think in terms of "what happened." Whether it's an export run or a system event, it belongs in one chronological feed. Tabs separate exports from system events.

### Empty State Strategy

Every page follows a consistent empty state pattern:

```
┌──────────────────────────────────────┐
│                                      │
│         [Illustration / Icon]        │
│                                      │
│       No API keys configured yet     │
│   Add your Onshape API keys to get   │
│            started.                  │
│                                      │
│        [➕ Add Your First Key]        │
│                                      │
│  Learn more → Setup Guide            │
└──────────────────────────────────────┘
```

---

## Phase 1: Home (Dashboard) Redesign

**Priority**: Critical  
**Effort**: 12-16 hours  
**Dependencies**: Phase 0 (navigation restructure)

### Current State Problems

- Zero-state dashboard shows six cards all reading "0" — intimidating and unhelpful
- No call-to-action for new users
- Charts show data but provide no actions
- Recent exports section is a flat list with no grouping

### Redesigned Home Page

#### State A: First Run (No exports yet)

```
┌──────────────────────────────────────────────────────────┐
│  Welcome to Onshape Export Manager                        │
│  Automate your CAD exports in 3 simple steps.             │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ ①        │ →  │ ②        │ →  │ ③        │           │
│  │ Add API  │    │ Create   │    │ Run Your │           │
│  │ Key      │    │ Label    │    │ Export   │           │
│  │          │    │          │    │          │           │
│  │ [Start]  │    │ [Start]  │    │ [Start]  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│                                                          │
│  Already set up? Import existing config →                 │
└──────────────────────────────────────────────────────────┘
```

#### State B: Active User (Has exports)

```
┌──────────────────────────────────────────────────────────┐
│  Home                                    Last 24h ↑       │
│                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 12      │ │ 3       │ │ 5       │ │ 2       │       │
│  │ Exports │ │ Labels  │ │ API Keys│ │ Failed  │       │
│  │ ↗ 4 new │ │         │ │ 1 rate- │ │ ⚠ View │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                          │
│  ┌─────────────────────────┐ ┌──────────────────────┐   │
│  │ Export Activity (7d)    │ │ Quick Export         │   │
│  │ [chart: bar + line]     │ │                      │   │
│  │                         │ │ 🏷 Robotics Team     │   │
│  │                         │ │ ⚡ STL+STEP          │   │
│  │                         │ │ 📅 This week         │   │
│  │                         │ │ [▶ Export Now]       │   │
│  └─────────────────────────┘ └──────────────────────┘   │
│                                                          │
│  Recent Exports                          [View All →]    │
│  ┌──────────────────────────────────────────────────────┐│
│  │ ✅ Robotics Team · 14m ago · 8 files · 23s          ││
│  │ ✅ Student Projects · 2h ago · 3 files · 12s        ││
│  │ ❌ Archive · 5h ago · Rate limited — retrying       ││
│  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Stat cards are clickable** — Click "Failed" → jumps to History filtered by failed exports
2. **Quick Export widget** — One-click re-export of the most recently used label/profile combination
3. **Welcome flow replaced** — The 9-step wizard is replaced by a 3-step onboarding on the Home page
4. **"Last 24h" trend indicator** — Shows directional changes, not just raw numbers

---

## Phase 2: API Keys (Unified Accounts + Organizations)

**Priority**: Critical  
**Effort**: 14-20 hours  
**Dependencies**: Phase 0 (navigation restructure), ARCH-01 (unified credential pool)

### Current State Problems

- Two separate pages (Organizations, Accounts) model the same domain
- Adding a credential requires navigating to a specific org first
- No inline testing
- No visual health indicators beyond a text badge
- Legacy accounts and new org credentials are invisible to each other

### Redesigned API Keys Page

```
┌──────────────────────────────────────────────────────────┐
│  API Keys                                  [+ Add Key]   │
│  ───────────────────────────────────────────────────────│
│  Group by: [None ▾]  Filter: [________]  Status: [All ▾]│
│                                                          │
│  ┌──────────────────────┐ ┌──────────────────────┐      │
│  │ 🏢 Engineering Team  │ │ 🏫 Student Lab       │      │
│  │ 3 keys · 2 healthy   │ │ 1 key · 1 healthy    │      │
│  │                      │ │                      │      │
│  │ ● Primary       ✅   │ │ ● Lab Pi Key    ✅   │      │
│  │   142 calls · 0 fail │ │   48 calls · 0 fail  │      │
│  │ ● Backup        ⚠️   │ │                      │      │
│  │   89 calls · rate-   │ │                      │      │
│  │   limited (12m left) │ │                      │      │
│  │ ● Archive       ⏸️   │ │                      │      │
│  │   disabled           │ │                      │      │
│  └──────────────────────┘ └──────────────────────┘      │
│                                                          │
│  ┌──────────────────────┐                               │
│  │ 📦 Ungrouped         │                               │
│  │ 1 key · 1 healthy    │                               │
│  │                      │                               │
│  │ ● Personal Key   ✅   │                               │
│  │   12 calls · 0 fail  │                               │
│  └──────────────────────┘                               │
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Card grid layout** — Organizations/keys are shown as cards with health status at a glance
2. **Group by toggle** — "None" shows a flat list; "Organization" groups into cards; "Status" groups by health
3. **Inline health** — Each key shows: calls today, failure count, rate limit status with countdown, last used
4. **Quick actions on hover** — Test, Edit, Disable, Delete (with undo)
5. **"Add Key" opens a modal** — No page navigation needed. Enter access key, secret key, optionally assign to organization, click Test, click Save.
6. **Bulk actions** — Checkbox selection → Test Selected, Move to Org, Delete Selected

---

## Phase 3: Labels Redesign

**Priority**: High  
**Effort**: 12-16 hours  
**Dependencies**: Phase 0, Phase 2 (API Keys must be unified first)

### Current State Problems

- Labels table doesn't show usage or schedule info
- Profiles and schedules are configured on separate pages
- No "Run Export" button on label rows
- No way to see how many Onshape documents match a label

### Redesigned Labels Page

```
┌──────────────────────────────────────────────────────────┐
│  Labels                                   [+ New Label]  │
│  ───────────────────────────────────────────────────────│
│  [🔍 Filter labels…]              View: [Cards ▾| Table] │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ 🏷 Robotics Team                    ● Active     │    │
│  │ ─────────────────────────────────────────────── │    │
│  │ Onshape ID: 5a7b3c...                           │    │
│  │ Formats: STL, STEP                     [Edit]   │    │
│  │ Schedule: Daily at 06:00           [Change]     │    │
│  │ API Keys: Primary, Backup                        │    │
│  │ Last export: 2 hours ago · 8 files · ✅         │    │
│  │                                                  │    │
│  │ [▶ Export Now]  [📋 History]  [⏸ Disable]      │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ 🏷 Student Projects                 ● Active     │    │
│  │ ─────────────────────────────────────────────── │    │
│  │ Onshape ID: 9f2e1d...                           │    │
│  │ Formats: STL (Binary, Fine, mm)      [Edit]     │    │
│  │ Schedule: Weekdays at 15:00        [Change]     │    │
│  │ API Keys: Lab Pi Key                             │    │
│  │ Last export: 5 hours ago · 3 files · ✅         │    │
│  │                                                  │    │
│  │ [▶ Export Now]  [📋 History]  [⏸ Disable]      │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ 🏷 Archive                          ⏸ Disabled   │    │
│  │ ─────────────────────────────────────────────── │    │
│  │ Onshape ID: 3b8a7c...                           │    │
│  │ Formats: All Formats                             │    │
│  │ Schedule: Monthly on 1st                         │    │
│  │ Last export: 30 days ago · 142 files · ✅       │    │
│  │                                                  │    │
│  │ [▶ Export Now]  [📋 History]  [● Enable]       │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Card view is the default** — Each label is a card showing all its configuration in one place
2. **Profiles are embedded** — Format selection happens inline on the label card, not on a separate page
3. **Schedule is embedded** — Schedule configuration is on the label card, not a separate Scheduler page
4. **"Export Now" is the primary action** — The most common action is one click away
5. **Format options are visible** — No need to navigate to a profile to see whether STL is binary or ASCII
6. **Table view as an alternative** — For users with many labels, a compact table view is available
7. **"New Label" opens a guided form** — Step 1: Name your label. Step 2: Paste Onshape label ID. Step 3: Choose formats. Step 4 (optional): Set schedule. Done.

### New Label Creation Flow

```
┌──────────────────────────────────────┐
│  Create Label                    [✕] │
│                                      │
│  Label Name                          │
│  [Robotics Team______________]       │
│                                      │
│  Onshape Label ID                    │
│  [5a7b3c9d1e2f________________]     │
│  ℹ️ Find this in Onshape under       │
│    Document > Labels                 │
│                                      │
│  Export Formats                      │
│  [✓] STL  [✓] STEP  [ ] OBJ         │
│  [ ] IGES [ ] Parasolid [ ] DXF     │
│  [ ] PDF                             │
│                                      │
│  ── STL Options ──                   │
│  Mode: [Binary ▾]                    │
│  Resolution: [Fine ▾]                │
│  Units: [Millimeter ▾]               │
│                                      │
│  Schedule (optional)                 │
│  [ ] Export automatically            │
│      Interval: [Daily ▾]             │
│      At: [06:00 ▾]                   │
│                                      │
│  API Keys                            │
│  [✓] Primary  [✓] Backup             │
│                                      │
│       [Cancel]    [Create Label]      │
└──────────────────────────────────────┘
```

---

## Phase 4: Export Page (Manual Export + Queue)

**Priority**: High  
**Effort**: 16-24 hours  
**Dependencies**: Phase 0, Phase 3 (labels must have embedded profiles)

### Current State Problems

- Manual Export is a standalone page with no visibility into the queue
- User must navigate to Queue to see if their export started
- Queue page shows a generic table, not a real-time operational view
- No progress indication for running exports
- "Queue Export" button terminology is user-hostile

### Redesigned Export Page

```
┌──────────────────────────────────────────────────────────┐
│  Export                                                   │
│  ───────────────────────────────────────────────────────│
│                                                          │
│  ┌─ New Export ──────────────────────────────────────┐   │
│  │                                                    │   │
│  │  Label        [Robotics Team ▾]                    │   │
│  │  Date Range   [This Week ▾]  or [Custom Range…]    │   │
│  │  Destination  [Default location____________]       │   │
│  │                                                    │   │
│  │  ┌─ Preview ──────────────────────────────────┐    │   │
│  │  │ 📄 ~5 documents  🔧 ~10 API calls           │    │   │
│  │  │ ⏱ ~2 min          💾 ~25 MB                 │    │   │
│  │  │ ✅ Label found  ✅ Profile valid             │    │   │
│  │  │ ✅ Account ready ✅ Date range valid         │    │   │
│  │  └────────────────────────────────────────────┘    │   │
│  │                                                    │   │
│  │  [Save as Template ▾]     [▶ Export Now]          │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Active & Queued ─────────────────────────────────┐   │
│  │                                                    │   │
│  │  ● Running now                                     │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Robotics Team · STL+STEP · Started 23s ago   │  │   │
│  │  │ ████████████░░░░░░ 3/5 documents             │  │   │
│  │  │ Current: Bracket Assembly → bracket.stl      │  │   │
│  │  │ [Cancel]                                     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                    │   │
│  │  ◌ Queued (2)                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Student Projects · STL · Scheduled           │  │   │
│  │  │ Waiting behind 1 job · Est. start: 2 min     │  │   │
│  │  │ [Cancel]  [Move to Top]                      │  │   │
│  │  ├──────────────────────────────────────────────┤  │   │
│  │  │ Archive · All Formats · Manual               │  │   │
│  │  │ Waiting behind 2 jobs · Est. start: 5 min    │  │   │
│  │  │ [Cancel]  [Move to Top]                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Single page for export + queue** — Top half: configure and run. Bottom half: monitor.
2. **"Export Now" instead of "Queue Export"** — User-friendly terminology
3. **Real-time progress bar** — Per-document progress with current file name
4. **Estimated wait time** — Queued jobs show their position and estimated start time
5. **Template saving is prominent** — "Save as Template" button near the Export button
6. **Move to Top / Cancel actions** — Queue management is inline, not on a separate page
7. **Running job shows live file-by-file progress** — "Bracket Assembly → bracket.stl"
8. **Preview is automatic** — No need to click "Preview" separately; it updates as fields change

---

## Phase 5: History Redesign

**Priority**: Medium-High  
**Effort**: 10-14 hours  
**Dependencies**: Phase 0, Phase 4 (queue and export flow)

### Redesigned History Page

```
┌──────────────────────────────────────────────────────────┐
│  History                        [Exports | Activity Log] │
│  ───────────────────────────────────────────────────────│
│                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 142     │ │ 97.2%   │ │ 1,230   │ │ 12s     │       │
│  │ Total   │ │ Success │ │ Files   │ │ Avg Time│       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                          │
│  Filter: [All Labels ▾] [All Results ▾] [30 days ▾]     │
│  Search: [______________________________]                │
│                                                          │
│  ┌─ June 26, 2026 ──────────────────────────────────┐    │
│  │                                                   │    │
│  │  ✅ 14:28  Robotics Team · STL+STEP               │    │
│  │           8 files · 23s · via Primary key         │    │
│  │           [Show Files] [Re-Export] [Details ▾]    │    │
│  │                                                   │    │
│  │  ✅ 11:15  Student Projects · STL                 │    │
│  │           3 files · 12s · via Lab Pi Key          │    │
│  │           [Show Files] [Re-Export] [Details ▾]    │    │
│  │                                                   │    │
│  │  ❌ 06:00  Archive · All Formats                  │    │
│  │           Rate limited on Primary key             │    │
│  │           Auto-retry in 8 minutes                 │    │
│  │           [Retry Now] [Show Logs] [Details ▾]     │    │
│  └───────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ June 25, 2026 ──────────────────────────────────┐    │
│  │  ✅ 14:30  Robotics Team · STL+STEP · 8 files    │    │
│  │  ✅ 06:00  Archive · All Formats · 142 files      │    │
│  └───────────────────────────────────────────────────┘    │
│                                                          │
│  [Load More]                                             │
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Tabs: Exports | Activity Log** — Former "Activity" page becomes the second tab
2. **Summary cards at top** — Success rate, total files, average time
3. **Grouped by date** — Human-readable date headers (Today, Yesterday, June 26, 2026)
4. **"Show Files" action** — Opens the export folder in the file system or shows a file list inline
5. **"Re-Export" action** — One-click re-run with the same parameters
6. **Expandable details** — Click "Details" to see per-file list, exact timestamps, full error messages
7. **"Load More" pagination** — Instead of a hard 500-item limit
8. **Search across history** — Filter by label name, profile, or file name

### Activity Log Tab

```
┌──────────────────────────────────────────────────────────┐
│  History                        [Exports | Activity Log] │
│  ───────────────────────────────────────────────────────│
│                                                          │
│  Filter: [All Categories ▾] [Warnings+Errors ▾]         │
│                                                          │
│  ● 14:28  Export completed: Robotics Team               │
│  ● 11:15  Export completed: Student Projects            │
│  ⚠ 06:00  Rate limit hit: Primary key                  │
│  ● 05:59  Worker started                               │
│  ● 05:45  Config updated: Labels changed               │
│  ⚠ 04:30  Login failed: bad password attempt           │
│  ● 00:00  System startup                               │
│                                                          │
│  [Load More]                                             │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 6: Settings Redesign

**Priority**: Medium  
**Effort**: 14-18 hours  
**Dependencies**: Phase 0

### Current State Problems

- "Settings" shows read-only information
- Actual settings are only editable via JSON config files
- System monitoring, logs, backups, and remote access are scattered across separate pages

### Redesigned Settings Page

```
┌──────────────────────────────────────────────────────────┐
│  Settings                                                 │
│  ───────────────────────────────────────────────────────│
│                                                          │
│  [General] [Notifications] [Backups] [Remote Access]     │
│  [Logs] [About]                                          │
│                                                          │
│  ┌─ General ─────────────────────────────────────────┐   │
│  │                                                    │   │
│  │  Theme                                             │   │
│  │  [🌙 Dark]  [☀️ Light]  [🖥 System]                 │   │
│  │                                                    │   │
│  │  Export Defaults                                   │   │
│  │  Default format: [STL ▾]                           │   │
│  │  Default resolution: [Fine ▾]                      │   │
│  │  Default units: [Millimeter ▾]                     │   │
│  │                                                    │   │
│  │  Worker                                            │   │
│  │  [✓] Auto-start worker on app launch               │   │
│  │  Poll interval: [5 ▾] seconds                      │   │
│  │  Worker threads: [1 ▾]                             │   │
│  │                                                    │   │
│  │  Retry Policy                                      │   │
│  │  Max attempts: [3 ▾]                               │   │
│  │  Base delay: [10 ▾] seconds                        │   │
│  │  Max delay: [300 ▾] seconds                        │   │
│  │                                                    │   │
│  │  Storage                                           │   │
│  │  Export location: [/home/pi/exports________]       │   │
│  │  Retention: Keep exports for [90 ▾] days           │   │
│  │                                                    │   │
│  │                         [Save Settings]             │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Key Changes

1. **Tabbed settings** — General, Notifications, Backups, Remote Access, Logs, About
2. **Editable settings** — All `config.json` values exposed as form controls with validation
3. **Save button** — Explicit save with confirmation toast
4. **Notifications tab** — The former Notifications page moves here with improved form design
5. **Backups tab** — Create, list, restore, prune backups
6. **Remote Access tab** — Tailscale, Cloudflare, HTTPS status with setup instructions
7. **Logs tab** — Log viewer with search and severity filtering
8. **About tab** — Version, database stats, system info (the read-only info from the old "Settings")

---

## Phase 7: Visual Design System Implementation

**Priority**: Medium  
**Effort**: 20-30 hours  
**Dependencies**: Phases 0-6 design decisions

### What Gets Implemented

1. **Consistent icon system** — All icons from a single SVG sprite or component set (Feather Icons)
2. **Design token consolidation** — Every color, spacing, radius, shadow defined as CSS custom properties
3. **Component library** — Reusable UI components standardized across pages:
   - `StatCard` — Summary metric with trend indicator
   - `DataCard` — Card layout for entities (labels, API keys)
   - `Modal` — Styled dialog with focus trapping
   - `Toast` — Already exists, needs refinement
   - `EmptyState` — Illustrated empty state with CTA
   - `SkeletonLoader` — Loading placeholder
   - `ProgressBar` — Determinate progress indicator
   - `Badge` — Status badge (success, warning, error, info, muted)
   - `Chip` — Filter/tag chip
   - `ConfirmDialog` — Styled confirmation (replaces native confirm())
4. **Accessibility pass** — ARIA labels, keyboard navigation, focus management, screen reader support
5. **Responsive breakpoints** — Proper layouts at 320px, 768px, 1024px, 1440px+
6. **Animation system** — Consistent transitions, page enter/exit, hover states

### Design Tokens (sample)

```css
:root {
  /* Spacing scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* Radius scale */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Shadow scale */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.12);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.15);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.2);
  --shadow-xl: 0 20px 60px rgba(0,0,0,0.3);

  /* Animation tokens */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;

  /* Z-index scale */
  --z-sidebar: 40;
  --z-topbar: 30;
  --z-modal: 70;
  --z-toast: 90;
  --z-command-palette: 80;
}
```

---

## Phase 8: Keyboard Shortcuts & Power-User Features

**Priority**: Medium  
**Effort**: 8-12 hours  
**Dependencies**: Phase 0-6 (pages must exist)

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `⌘K` | Command palette (search everything) |
| `⌘B` | Toggle sidebar |
| `⌘1`-`⌘5` | Navigate: Home, API Keys, Labels, Export, History |
| `⌘,` | Open Settings |
| `⌘N` | New (context-dependent: new label on Labels page, new key on API Keys page) |
| `⌘Enter` | Submit current form / Run export |
| `⌘F` | Focus search/filter on current page |
| `Escape` | Close modal / close command palette / deselect |
| `?` | Show keyboard shortcuts help dialog |
| `Space` | Toggle checkbox selection (when row is focused) |
| `↑↓` | Navigate items in list/table (when focused) |
| `⌘Z` | Undo last action (where supported) |

### Context Menus (Right-Click)

| Context | Menu Items |
|---|---|
| Label card | Export Now, Edit, Duplicate, Disable/Enable, Delete |
| API Key card | Test Connection, Edit, Disable, Move to Organization, Delete |
| History row | Show Files, Re-Export, Copy Error Message |
| Queue job | Cancel, Move to Top, View Details |
| Empty area | New Label, New API Key, Import Config |

---

## Phase 9: Onboarding & First-Run Experience

**Priority**: Medium-High  
**Effort**: 10-14 hours  
**Dependencies**: Phase 0-4 (new pages must exist)

### Complete Replacement of the 9-Step Wizard

The wizard is replaced with:

1. **Welcome screen** (1 step) — Create admin account (username + password)
2. **Guided setup on Home page** (post-login) — 3 cards: Add API Key, Create Label, Run Export
3. **Progressive disclosure** — Advanced features (organizations, schedules, notifications) are introduced via subtle hints and tooltips after the user has completed their first export

### First-Run Flow

```
Step 0: Open app → See welcome screen
  "Welcome to Onshape Export Manager"
  [Create admin account form]
  → Creates owner and signs in

Step 1: Home page with 3-step guide
  ┌──────────────────────────────┐
  │ ① Add your Onshape API key   │  [Start] ← Opens modal
  │ ② Create your first label    │  [Start] ← Opens modal
  │ ③ Run your first export      │  [Start] ← Navigates to Export
  └──────────────────────────────┘

Step 2: After first export → Celebration
  🎉 "Your first export is complete!"
  "8 files saved to ~/exports/Robotics_Team/2026-07-08_142831/"
  [Open Folder]  [View in History]  [Set Up Schedule →]
```

---

## Phase 10: Polish & Final Coherence Pass

**Priority**: Lower (but essential for v1.0)  
**Effort**: 12-18 hours  
**Dependencies**: All previous phases

### What Gets Polished

1. **Empty state illustrations** — Custom SVG illustrations for each page's empty state
2. **Loading skeletons** — Animated placeholder shapes matching the layout of loaded content
3. **Error states** — Consistent error cards with retry buttons and expandable details
4. **Success celebrations** — Subtle animations for completed exports, created labels, etc.
5. **Transition animations** — Page transitions, modal open/close, toast enter/exit
6. **Focus rings** — Visible focus indicators for keyboard navigation
7. **Scroll behavior** — Smooth scroll, sticky headers where appropriate
8. **Print styles** — Basic print stylesheet for history/logs
9. **Favicon** — Application icon in browser tab
10. **`<title>` tags** — Dynamic page titles: "Robotics Team · Export · Onshape Export Manager"

---

## Implementation Phases Summary

| Phase | Name | Effort | Priority | Depends On |
|---|---|---|---|---|
| 0 | Information Architecture Restructure | 16-24h | 🔴 Critical | — |
| 1 | Home (Dashboard) Redesign | 12-16h | 🔴 Critical | Phase 0 |
| 2 | API Keys (Unified) | 14-20h | 🔴 Critical | Phase 0, ARCH-01 |
| 3 | Labels Redesign | 12-16h | 🟠 High | Phase 0, Phase 2 |
| 4 | Export Page (Export + Queue) | 16-24h | 🟠 High | Phase 0, Phase 3 |
| 5 | History Redesign | 10-14h | 🟡 Med-High | Phase 0, Phase 4 |
| 6 | Settings Redesign | 14-18h | 🟡 Medium | Phase 0 |
| 7 | Visual Design System | 20-30h | 🟡 Medium | Phase 0-6 |
| 8 | Keyboard Shortcuts & Power-User | 8-12h | 🟡 Medium | Phase 0-6 |
| 9 | Onboarding & First-Run | 10-14h | 🟡 Med-High | Phase 0-4 |
| 10 | Polish & Coherence | 12-18h | 🟢 Lower | All phases |

**Total estimated effort: 144-206 hours (4-6 weeks of full-time work)**

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Backend changes (ARCH-01) delay UI work | Medium | High | Start ARCH-01 in parallel with Phase 0 |
| Design changes break existing user workflows | Low | Medium | Keep old pages accessible via URL during transition |
| Scope creep during design iteration | Medium | Medium | Strict phase boundaries; defer non-critical polish to Phase 10 |
| Mobile responsiveness adds unexpected complexity | Medium | Low | Mobile is Phase 7; desktop is the priority |

---

*End of Master UI Redesign Plan. Next: UI_GUIDELINES.md*
