# UX Audit — Onshape Export Manager

> **Date**: 2026-07-08  
> **Auditor**: Senior Product Design Team (Product Designer, UX Designer, Software Architect, QA Lead)  
> **Scope**: Every screen, every workflow, every interaction  
> **Methodology**: First-time-user walkthrough, workflow tracing, heuristic evaluation against Nielsen's 10 usability heuristics, comparison against desktop-app benchmarks (Docker Desktop, GitHub Desktop, Obsidian, VS Code, JetBrains IDEs)

---

## Severity Scale

| Level | Icon | Meaning |
|---|---|---|
| **Critical** | 🔴 | Blocks core workflow; user cannot complete primary task without confusion or workaround |
| **High** | 🟠 | Causes significant friction, confusion, or error; degrades the experience substantially |
| **Medium** | 🟡 | Noticeable issue; adds unnecessary clicks, creates inconsistency, or violates conventions |
| **Low** | 🟢 | Cosmetic or minor; polish-level improvement |
| **Observation** | 🔵 | Not a defect per se, but a design decision worth reconsidering |

---

## 1. Global Navigation & Information Architecture

### 🔴 NAV-01: 14 navigation items is overwhelming for a focused tool

The sidebar contains 14 distinct pages: Dashboard, Organizations, Accounts, Labels, Export Profiles, Manual Export, Queue, Scheduler, History, System, Activity, Logs, Notifications, Settings.

**Problem**: For an application whose primary job is "export CAD files from Onshape," 14 top-level navigation destinations creates cognitive overload. A first-time user cannot distinguish between Queue/Scheduler/History, between Activity/Logs, or between Organizations/Accounts.

**Benchmark comparison**: Docker Desktop has 5 tabs. GitHub Desktop has 3 views. Obsidian's core has 4 icons. VS Code's activity bar has 5-6 icons.

**Recommendation**: Collapse to 6-7 primary destinations. Group related concepts.

### 🔴 NAV-02: Organizations and Accounts are separate pages that model the same domain entity

"Organizations" and "Accounts" appear as separate sidebar items. In the implementation, Organizations are the new model (hierarchical grouping of credentials) and Accounts are the legacy flat model. But to a user, both represent "Onshape API keys I can use to export."

**Problem**: A user opening the app for the first time does not know whether to go to Organizations or Accounts. They see both, try both, and find overlapping information. If they create an Organization and then go to Accounts, they may add a credential that doesn't belong to any org.

**Recommendation**: Unify into a single "Accounts" page (or "API Keys") with an optional grouping/organization view. The flat-vs-hierarchical distinction is an implementation detail that should not leak into the UI.

### 🟠 NAV-03: Activity and History are confusingly similar

"Activity" shows an event feed (system startup, config changes, login attempts). "History" shows export history. The icons are nearly identical (both use `history`). The conceptual separation between "what the system did" and "what exports ran" is not immediately obvious.

**Problem**: Users go to "Activity" looking for their last export, or go to "History" looking for system events. Neither page links to the other.

**Recommendation**: Merge into one page with tabs ("Exports" and "System Events"), or rename "Activity" to "Audit Log." Remove the word "Activity" — it's ambiguous.

### 🟠 NAV-04: System, Logs, and Settings overlap significantly

"System" shows CPU/RAM/disk/uptime, worker status, remote access URLs, and backups. "Logs" shows log file contents. "Settings" shows a read-only display of database stats and version info.

**Problem**: All three are "administration" pages. A user trying to troubleshoot an issue doesn't know which to open. The information is scattered across three pages when it could be consolidated.

**Recommendation**: Consolidate into one "Administration" page with sub-tabs: Overview (system health), Logs, Backups, Remote Access. Move actionable settings into a distinct Settings panel accessible from a gear icon.

### 🟡 NAV-05: Plugins page shows static cards, not real plugins

The Plugins page (rendered via `pluginHooks` in app.js) shows six hardcoded cards describing plugin hook types. No actual plugins are installed or loadable.

**Problem**: This is aspirational content presented as a feature. A user clicking "Plugins" expecting to install integrations finds a museum of what might someday exist. This erodes trust.

**Recommendation**: Remove the Plugins page until the plugin loader is implemented. Replace with a "Coming Soon" badge or move to Settings.

### 🔵 NAV-06: Sidebar uses icons+labels but collapse hides labels

The sidebar supports collapsing (⌘B), which hides labels and shows only icons. This is good for power users. However, the collapsed state does not show tooltips on hover, so a new user who accidentally collapses the sidebar cannot discover what the icons mean.

**Recommendation**: Add hover tooltips in collapsed mode (standard behavior in VS Code, JetBrains, Obsidian).

---

## 2. Dashboard

### 🟠 DASH-01: Dashboard shows everything but teaches nothing

The dashboard has stat cards (6), two charts (activity line chart, account health doughnut), a success rate gauge, queue breakdown, storage info, and recent exports. It shows data but provides no guidance.

**Problem**: When a first-time user opens the dashboard, all numbers show zero. There is no call-to-action, no "Get Started" button, no explanation of what to do next. The empty dashboard is a dead end.

**Benchmark comparison**: Docker Desktop's empty state shows "No containers running" with a "Run a container" button. GitHub Desktop's empty state shows "Let's get started" with a clone/create/open flow.

**Recommendation**: Empty dashboard should show a guided getting-started flow: "1. Add an API key → 2. Create a label → 3. Run your first export." Replace zero-stat cards with step-by-step onboarding.

### 🟡 DASH-02: Stat cards show raw numbers without context

Cards show "Accounts: 3" and "Labels: 5" but don't indicate whether 3 is good, bad, or what the user should do with that information. The "Failed" card turns red when >0 but provides no path to investigate.

**Problem**: Stat cards answer "what" but not "so what." A user seeing "Failed: 2" wants to click it and see which exports failed and why. Currently, the cards are not clickable.

**Recommendation**: Make stat cards clickable — clicking "Failed" should navigate to History filtered by failed exports. Add trend indicators (↑↓) comparing to previous period.

### 🟡 DASH-03: Charts show 14 days of activity without date range control

The activity chart is fixed at 14 days. There is no way to change the range, zoom, or compare periods.

**Recommendation**: Add period selector (7d / 14d / 30d / 90d). Make chart points clickable to drill into specific days.

### 🟢 DASH-04: "Recent Exports" section is a table-in-a-card but styled as a timeline

The timeline design is attractive, but each row's metadata (profile, account, files, duration) is concatenated into a single string separated by "·" characters, making it hard to scan.

**Recommendation**: Use a more structured layout for metadata. Add a "View all" link that is more prominent.

---

## 3. Login / Authentication

### 🟠 AUTH-01: Login page doubles as setup page, creating confusion

The login page shows different content depending on whether an owner exists: first run shows account creation, subsequent visits show sign-in. The URL is always `/login`.

**Problem**: The dual-purpose page is elegant code reuse but confusing UX. A returning user seeing "Sign in" doesn't know they visited `/login`. A new user seeing "Create the owner account" doesn't know this is a one-time setup.

**Recommendation**: Separate the first-run experience into a dedicated `/setup` route with branding that says "Welcome — let's set up your appliance." The login page should only ever show sign-in.

### 🟡 AUTH-02: No "forgot password" or recovery mechanism

There is a single owner account with no password reset flow. If the owner forgets their password, there is no recovery path documented on the login page or in the UI.

**Recommendation**: Document the CLI recovery command (`python -m onshape_export_manager.cli --reset-owner`) on the login page. Better: provide a "Reset password" link that explains the procedure.

### 🟢 AUTH-03: "Remember me" is a checkbox with no explanation of what happens

The "Remember me for 30 days" label is clear, but there's no indication of what happens without it (session cookie? browser session?).

**Recommendation**: Add a subtle hint: "Keeps you signed in for 30 days. Without this, you'll be signed out when you close the browser."

---

## 4. Setup Wizard

### 🔴 WIZ-01: Nine-step wizard is too many steps

The wizard has 9 steps: Administrator, Storage, Organization, API Credentials, Labels, Export Profile, Test, Remote Access, Finish. Four of these (Labels, Export Profile, Test, Remote Access) are optional or advanced.

**Problem**: A new user who just wants to export a file must click through 9 steps. The wizard does not indicate which steps are skippable until the user reaches them. The progress indicator shows all 9 dots, making the task feel daunting before it begins.

**Benchmark comparison**: Docker Desktop's first-run is 2 steps (install, optional survey). GitHub Desktop's is 3 steps (sign in, configure Git, optional usage data). Obsidian's is 1 step (pick a vault location).

**Recommendation**: Reduce to 4 required steps: (1) Create admin account, (2) Add an API key, (3) Create a label, (4) Done. Move storage configuration, organization creation, and advanced settings to post-onboarding hints. Add a "Skip for now" button prominently on every step.

### 🟠 WIZ-02: The "Organization" step is confusing before the user has any exports

Step 3 asks the user to create an Organization (school, company, department, etc.) before they have added any API credentials. The concept of an "Organization" as a container for credentials is abstract and unexplained.

**Problem**: Users think in terms of "I have an Onshape account with an API key." The hierarchy of Organization → Credential is an implementation detail. For a single user with one API key, creating an Organization feels like bureaucracy.

**Recommendation**: Start with a flat "Add API Key" step. Introduce organizations later as an optional organizational feature for multi-team deployments.

### 🟡 WIZ-03: The "Test" step is buried at step 7

The user enters API credentials at step 4 but cannot verify they work until step 7. If the credentials are wrong, they must navigate back 3 steps.

**Recommendation**: Add a "Test Connection" button directly on the API Credentials step. Show success/failure inline before proceeding.

### 🟡 WIZ-04: The "Remote Access" step shows raw JSON with no explanation

Step 8 shows Tailscale status, Cloudflare tunnel status, local URLs, and HTTPS configuration. There is no explanation of what any of this means or why the user should care during setup.

**Recommendation**: Move remote access configuration to a post-setup Settings page. If the user is running in desktop mode, this step is completely irrelevant.

### 🟢 WIZ-05: The wizard lives on a separate page with no back-link to the app

The wizard page has its own HTML template, CSS, and JS logic. It does not share the sidebar or topbar. Once the user completes the wizard, they are redirected to the dashboard. There is no way to re-run the wizard without deleting the database.

**Recommendation**: A "Re-run Setup" button in Settings would help users who made mistakes or want to add more configuration.

---

## 5. Accounts / Organizations Pages

### 🔴 ACC-01: Two pages model the same concept from two different eras

"Organizations" shows hierarchical groups with nested credentials. "Accounts" shows a flat list of API keys with runtime state (usage, failures, rate limits). The Accounts page uses the legacy `ApiPool`, while Organizations uses the newer `CredentialPool`.

**Problem**: A user who adds a credential via Organizations does not see it on the Accounts page. A user who looks at Accounts sees a flat list with no organizational grouping. The implementation schism is fully exposed to the user as two separate pages with overlapping but incompatible data.

**Recommendation**: Merge into a single page. Show all credentials in a unified view with optional grouping by organization. The flat legacy view should be deprecated and migrated.

### 🟠 ACC-02: No way to test an API key from the Accounts/Organizations page

The test endpoint exists (`POST /api/organizations/{org_id}/credentials/{id}/test`) and is used in the wizard, but there is no "Test" button on the Organizations or Accounts management pages.

**Problem**: After initial setup, if a user adds a new API key, they cannot verify it works without navigating away to a different workflow.

**Recommendation**: Add a "Test Connection" button to each credential row. Show latency and status inline.

### 🟡 ACC-03: Credential creation form uses a `<details>` / `<summary>` expandable section

On the Organizations page, the "Add credential" form is hidden behind a `<details>` element. This is accessible but unusual for a data-entry form.

**Problem**: The expandable section collapses after adding a credential, hiding the form. Users who want to add multiple credentials must re-expand it each time.

**Recommendation**: Use a persistent inline form or a modal dialog. Do not auto-collapse after submission.

### 🟡 ACC-04: No bulk actions for credentials

Users cannot select multiple credentials to delete, test, or move them between organizations. Every action is one-at-a-time.

**Recommendation**: Add checkbox selection and bulk action toolbar (Delete, Move to Organization, Test All).

### 🟢 ACC-05: "Import from accounts" button is unclear

The Organizations page has an "Import from accounts" button that migrates flat accounts into organizations. The button label doesn't explain what it does or that it's a migration action.

**Recommendation**: Add a description: "Migrate your legacy accounts into the organization model." Show a preview of what will be imported before executing.

---

## 6. Labels Page

### 🟡 LAB-01: Labels page shows configuration data but not label usage

The labels table shows: Label name, Profile, Onshape ID, Assigned Accounts, Enabled. It does not show: when the label was last exported, how many documents match this label on Onshape, or how many exports have been run with this label.

**Problem**: A user managing labels wants to know which labels are actively used, which have documents waiting, and which are stale. The current table answers none of these questions.

**Recommendation**: Add columns for "Last Export," "Document Count" (if discoverable), and "Export Count." Add a "Run Export" action button directly on each label row.

### 🟡 LAB-02: No way to create or edit labels except through a separate form

The labels page uses the generic `sectionPage` component which renders a table with filtering. But creating a label requires a separate form (not visible on the page by default). The only way to create a label is via the wizard or the API.

**Problem**: The "Create" action is missing from the Labels page toolbar. Users must use the CLI or wizard to create labels.

**Recommendation**: Add a "+ New Label" button that opens an inline form or modal.

### 🟢 LAB-03: Label table columns don't match the label model

The label model in `labels.json` includes: `friendly_name`, `onshape_label_id`, `assigned_accounts`, `export_location`, `export_profile`, `scheduler`, `enabled`. The table shows only 5 of 7 fields. Export location and scheduler configuration are hidden.

**Recommendation**: Show all relevant fields, or make the hidden ones accessible via an expandable detail row.

---

## 7. Export Profiles Page

### 🟡 PROF-01: Profiles page is read-only with no creation UI

Like labels, the export profiles page shows a table (Profile, Formats, Bambu, Enabled) but provides no way to create or edit profiles from the UI. The nine default profiles (STL, STEP, OBJ, IGES, Parasolid, DXF, PDF, STL+STEP, All Formats) are pre-configured.

**Problem**: If a user needs a custom profile (e.g., "STL binary, fine resolution, millimeters"), they cannot create it from the UI. They must edit `export_profiles.json` manually.

**Recommendation**: Add profile CRUD to the UI with a format picker, resolution options, and unit selection.

### 🟢 PROF-02: "Bambu" column is confusing without context

The table shows a "Bambu" column (Yes/No) without explaining what Bambu Studio integration means or why a user would enable it.

**Recommendation**: Add a tooltip: "Auto-arrange and slice exports in Bambu Studio after download." Consider renaming to "Post-Process."

---

## 8. Manual Export Page

### 🟠 MAN-01: The manual export workflow is the most polished page but still has friction

The manual export page is by far the best-designed page: it has a date range picker, presets, templates, a preview pane, and validation. But it reveals deeper issues:

**Problem 1 — The page requires the user to already understand labels and profiles**: The Label dropdown shows all labels created in the system. A new user with zero labels sees an empty dropdown and a dead page. There's no "Create your first label" prompt.

**Problem 2 — The preview makes estimates based on historical data, not live Onshape data**: The preview intentionally avoids API calls. This means the first export always shows "Unknown" estimates, which undermines trust in the preview feature.

**Problem 3 — Date presets are overloaded with 7 options**: Today, Yesterday, This Week, Last Week, This Month, Last Month, Custom Range. For a tool that primarily exports "whatever changed recently," several of these presets are unlikely to be used (Last Month, Custom Range).

**Recommendation**: Simplify presets to Today, This Week, Custom. Add "Export All" (no date filter) as the default. Show a prominent "Create your first label" CTA when labels are empty. After the first export, use real document counts from the Onshape API for preview estimates.

### 🟡 MAN-02: Template system is powerful but hidden

The template system (saving date/label/profile combinations as named templates, favoriting them, recent template list) adds significant value for repeat workflows. But the UI elements are small and below the fold.

**Problem**: Most users will not discover templates because they're in the lower portion of the left panel, represented by small chips and a dropdown.

**Recommendation**: Make templates a first-class feature. Show "Recent exports" as one-click re-run buttons at the top of the page. Use larger, more visible template cards.

### 🟡 MAN-03: "Queue Export" button label is ambiguous

The primary action button says "Queue Export" — a technically accurate but user-unfriendly term. A new user doesn't know what "queue" means in this context.

**Recommendation**: Rename to "Export Now" or "Start Export." The queue is an implementation detail.

### 🟢 MAN-04: The CLI command preview is a nice touch but out of place

The page includes an `manualCommand` getter that generates the equivalent CLI command. This is developer documentation mixed into the user interface.

**Recommendation**: Move the CLI equivalent to a tooltip or a collapsible "Advanced" section at the bottom of the page.

---

## 9. Queue Page

### 🟠 QUE-01: Queue uses the generic table template, losing important context

The queue page renders a table with columns: Label, Profile, Status, Retries, Next Run, Last Error, Actions. This is the same generic table used by Accounts, Labels, Profiles, Scheduler, and History.

**Problem**: The queue is a real-time operational view. It needs to show: how many jobs are ahead of this one, estimated wait time, progress indicators for running jobs, and visual distinction between job types (manual vs. scheduled). The generic table provides none of this.

**Recommendation**: Design the queue as a dedicated view with: (1) a summary bar showing total/active/waiting/failed, (2) a visual timeline or Gantt-like view of running jobs, (3) per-job progress bars, (4) real-time status updates without page refresh.

### 🟡 QUE-02: Queue actions are cryptic buttons

The Actions column shows "Cancel" or "Retry" as small text buttons. There is no confirmation for "Cancel" (it uses `confirm()`), no undo after cancellation, and no way to view the job's full error details inline.

**Recommendation**: Use icon buttons with tooltips. Replace `confirm()` with a custom confirmation dialog. Add an expandable detail row showing full error messages.

### 🟢 QUE-03: No visual distinction between manual and scheduled jobs

Both job types look identical in the queue table. A user cannot tell at a glance which jobs they triggered manually and which are automatic.

**Recommendation**: Add a "Source" column or icon (manual = person icon, scheduled = clock icon).

---

## 10. Scheduler Page

### 🟠 SCH-01: Scheduler and Labels have overlapping configuration

A label's schedule is configured in `labels.json` (the `scheduler` field on each label). The Scheduler page shows jobs that were created from those label schedules. But there's no visible link between a scheduler job and the label it comes from.

**Problem**: A user looking at a scheduler job wants to know: "Which label is this for? What profile does it use? What time is it scheduled?" They see a job name that may or may not match the label name.

**Recommendation**: Embed schedule configuration directly into the Labels page. Show each label's schedule status inline. Remove the standalone Scheduler page or make it a filtered view of Labels.

### 🟡 SCH-02: Scheduler intervals are limited

Supported intervals: 15min, 30min, hourly, daily, weekly, monthly. There is no custom cron expression, no "weekdays only," no "first Monday of the month."

**Problem**: For school/educational use cases, "weekdays at 3 PM" is a common need. The current intervals cannot express this.

**Recommendation**: Add custom cron expression support for power users. Add common presets: "Every weekday," "Weekends," "First of month."

### 🟢 SCH-03: No "Run Now" button on scheduler jobs

A user who wants to trigger a scheduled job immediately (outside its normal schedule) must go to Manual Export, find the same label, configure the same profile, and queue it manually.

**Recommendation**: Add a "Run Now" button on each scheduler job that enqueues an immediate export with the same parameters.

---

## 11. History Page

### 🟡 HIST-01: History page is purely a log with no analytical value

The history table shows: Started, Label, Profile, Account, Files, Duration, Result. It's a flat list with filtering. There is no aggregation, no trend analysis, no comparison, and no way to re-export from a historical entry.

**Problem**: A user looking at history wants to answer questions like: "Which labels export the most files?" "Which account is fastest?" "What's my success rate this month?" The flat table answers none of these.

**Recommendation**: Add summary cards above the table (success rate, total exports, total files, average duration). Add grouping options (by label, by profile, by day). Add a "Re-export" action on successful entries.

### 🟡 HIST-02: No way to view exported files from history

When an export succeeds, files are written to disk in a timestamped folder. The history entry records `exported_files` (count and paths), but the UI does not show or link to these files.

**Problem**: A user who wants to find a file that was exported last week must manually navigate their filesystem. The application knows where the files are but doesn't expose them.

**Recommendation**: Add a "Show Files" action that opens the export folder in the system file manager, or a file browser modal within the app.

### 🟢 HIST-03: "Limit=500" is hardcoded in the page config

The history endpoint is called with `limit=500`. There is no pagination, no "Load More," and no way to see older entries beyond the 500 cutoff.

**Recommendation**: Implement cursor-based pagination with a "Load More" button.

---

## 12. System Page

### 🔴 SYS-01: System page is a grab-bag of unrelated information

The System page contains: CPU, RAM, temperature, disk usage, uptime, job counts, worker controls, backup controls, remote access URLs (Tailscale, Cloudflare, HTTPS, reverse proxies), and database file size. It has no clear information hierarchy or purpose.

**Problem**: This page tries to be everything: a system monitor, a worker control panel, a backup manager, and a network config viewer. None of these functions are done well because they're competing for space.

**Recommendation**: Split into focused pages:
- **System Health** — CPU, RAM, disk, temperature, uptime (monitoring dashboard)
- **Worker** — Worker status, controls, recent job history (operational view)
- **Backups** — List, create, restore, prune (data management)
- **Remote Access** — URLs, tunnel status, HTTPS config (networking)

### 🟠 SYS-02: Worker start/stop buttons have no status transition feedback

Clicking "Start Worker" or "Stop Worker" sends a POST request and updates the display. There is no loading state, no transition animation, and no confirmation that the action took effect.

**Problem**: A user clicking "Stop Worker" sees no immediate change. They may click again, sending duplicate requests. The worker status may take seconds to actually change.

**Recommendation**: Show a loading spinner on the button during the API call. Disable the button until the response returns. Show a status transition animation (running → stopping → stopped).

### 🟡 SYS-03: Backup "Create" button has no options

The backup creation button creates a backup with a single click — no options for including/excluding logs, no naming, no scheduling. The only option (`include_logs`) is available via the API but not exposed in the UI.

**Recommendation**: Add a backup options dialog: name, include logs (checkbox), schedule (for future auto-backup).

---

## 13. Activity Page

### 🟠 ACT-01: Activity page is an event firehose

The activity page shows a real-time feed of ALL system events via WebSocket. Every login attempt, config change, backup creation, export start/finish, and system notification appears in a single scrolling list.

**Problem**: The unfiltered feed is overwhelming. A security-relevant event (failed login) scrolls past at the same speed as a routine event (export completed). There is no way to filter by importance at a glance.

**Recommendation**: Add severity-based visual hierarchy. Critical/error events should be visually distinct (red background, pinned to top). Add default filters: "Errors & Warnings" should be the default view, with "All Events" as an option.

### 🟡 ACT-02: Category and severity dropdowns are easy to miss

The filter controls (category dropdown, severity dropdown) are small `<select>` elements in the toolbar. They don't stand out visually.

**Recommendation**: Use chip/tag filters like GitHub's issue filters. Show active filter count as a badge.

---

## 14. Logs Page

### 🟠 LOG-01: 11 log areas is too much choice

The logs page offers 11 tabs: app, errors, api, export, scheduler, queue, web, worker, events, audit, notifications.

**Problem**: A user troubleshooting an issue doesn't know which log to look at. The "errors" log aggregates warnings and errors from all areas, making it the most useful — but it's the second tab, not the first.

**Recommendation**: Make "Errors" the default tab. Group remaining logs into categories: "Application" (app, web, api), "Export Pipeline" (export, worker, queue, scheduler), "System" (events, audit, notifications). Add a search bar that searches across all logs simultaneously.

### 🟡 LOG-02: Log viewer has no search, filter, or auto-scroll toggle

The log viewer is a `<pre>` block with syntax-colored lines. There is no search within the current log, no filter by severity, and no pause/play for live logs.

**Recommendation**: Add a search input that highlights matching lines. Add severity filter chips. Add an "Auto-scroll" toggle for live log tailing.

### 🟢 LOG-03: Logs load 300 lines with no pagination

The API returns 300 lines per request with no way to load older entries.

**Recommendation**: Add "Load older entries" button or infinite scroll.

---

## 15. Notifications Page

### 🟠 NOT-01: Notification configuration uses a complex inline form

The notifications page has an inline form for creating/editing channels with fields for: name, kind (dropdown), target URL, minimum severity, enabled toggle, and options object. The form layout changes based on the selected kind (email shows SMTP fields, webhook shows URL only) — but this behavior is handled by a generic JSON blob in `options`.

**Problem**: Email configuration requires `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `from_address`, `to_addresses` — all stuffed into a single `options` object with no structured form fields. Users must know the exact JSON keys.

**Recommendation**: Show kind-specific form fields. For email, show labeled fields for SMTP host, port, username, password, from address, to addresses. For webhooks, show URL field. For Discord/Slack/Teams, show webhook URL with platform-specific help text.

### 🟡 NOT-02: Test notification button provides limited feedback

Clicking "Test" shows a toast: "Sending test…" then either "Test delivered" or "Test failed" with a detail string. The detail string is raw (e.g., "HTTP 404" or "Connection refused") with no troubleshooting guidance.

**Recommendation**: Show richer feedback: "Could not reach Discord webhook. Check that the webhook URL is correct and the channel still exists. Error: HTTP 404."

### 🟢 NOT-03: No notification preview

There is no way to preview what a notification will look like before sending. For Discord/Slack/Teams, the message format (embeds, adaptive cards) is different for each platform.

**Recommendation**: Add a "Preview" button that shows a mock notification in the target platform's format.

---

## 16. Settings Page

### 🔴 SET-01: Settings page shows read-only information, not actual settings

The Settings page displays four groups: Application (version, generated time), Database (schema version, row counts), Storage (exports size, file count), Exports (success rate, average duration, total files). None of these are editable.

**Problem**: A user clicking "Settings" expects to change settings: server port, worker count, retry policy, theme, notification preferences. Instead, they see a read-only report. The name "Settings" creates false expectations.

**Recommendation**: Rename to "About" or "System Info." Create an actual Settings page for configurable options: server configuration, worker configuration, retry policy, UI preferences, export defaults.

### 🟡 SET-02: Actual settings require editing JSON config files

The application's real configuration lives in `config.json`, `accounts.json`, `labels.json`, `export_profiles.json`, and `organizations.json`. None of these are editable from the web UI (except labels and profiles via dedicated endpoints).

**Problem**: Changing the worker poll interval, log level, or retry policy requires SSH access and manual JSON editing. This is not acceptable for a "desktop application."

**Recommendation**: Expose all user-facing configuration in the Settings UI with proper form controls, validation, and save functionality.

---

## 17. Cross-Cutting UX Issues

### 🔴 CC-01: No undo for destructive actions

Deleting a label, organization, credential, or notification channel is immediate and irreversible. There is no confirmation dialog with a countdown timer, no undo toast, and no soft-delete pattern.

**Problem**: A misclick destroys configuration data with no recovery path except restoring from a backup — which itself is a multi-step process requiring CLI access.

**Recommendation**: Implement a toast-based undo system: after deletion, show "Label 'X' deleted. Undo?" for 10 seconds. Use soft-delete in the backend to support this.

### 🔴 CC-02: No client-side form validation

All forms (login, label creation, credential addition, notification channel configuration) rely entirely on server-side validation. Users submit forms, wait for a round-trip, and see raw JSON error messages in toast notifications.

**Problem**: A user who submits a form with missing required fields waits 200-500ms for a server response that could have been caught instantly. The error messages are technical (e.g., "export profile 'nonexistent' does not exist") rather than helpful.

**Recommendation**: Add inline validation on blur for all form fields. Show error messages next to the field, not in a toast. Reserve toasts for success confirmations.

### 🔴 CC-03: No mobile responsiveness

The application assumes a desktop viewport. On screens narrower than 820px, the sidebar is hidden by default (hamburger menu). However, tables overflow with no horizontal scroll indicators, form grids don't collapse properly, and the dashboard stat grid breaks at intermediate widths.

**Problem**: The application is designed to run on a Raspberry Pi, which is often accessed from a phone or tablet on the local network. The current mobile experience is broken.

**Recommendation**: Full responsive redesign: hamburger menu, single-column layouts, horizontal-scroll tables with sticky first column, touch-friendly tap targets (minimum 44px).

### 🔴 CC-04: No accessibility (WCAG 2.1 AA)

Zero ARIA labels, no `role` attributes, no focus trapping in modals, no `aria-live` regions for dynamic content, no skip-to-content link, insufficient color contrast on muted text in dark mode.

**Problem**: The application is inaccessible to users with screen readers, keyboard-only users, and users with visual impairments. This is a legal requirement in many jurisdictions for educational software.

**Recommendation**: Comprehensive accessibility audit and remediation. Add ARIA labels to all interactive elements, implement keyboard navigation for all workflows, ensure color contrast ratios ≥4.5:1 for text and ≥3:1 for large text.

### 🟠 CC-05: No consistent empty state design

Empty states vary across pages: Dashboard shows zero-stat cards, Queue shows "The export queue is empty," History shows "No export history yet," Accounts shows "No accounts configured yet." Some empty states have CTAs, others don't.

**Problem**: Empty states are the first thing a new user sees. Inconsistent empty states make the application feel unfinished.

**Recommendation**: Design a consistent empty state pattern: illustration, descriptive text, and a prominent CTA button that leads to the next logical step.

### 🟠 CC-06: No loading state consistency

Some pages show a loading state (dashboard has `loading` flag), others don't. There are no skeleton loaders, no progress indicators for data fetches, and no timeout handling for slow requests.

**Problem**: Users see blank pages or stale data while waiting for API responses, with no indication that anything is happening.

**Recommendation**: Implement skeleton loaders for all data-dependent views. Add a global loading indicator in the topbar. Show timeout errors with retry buttons.

### 🟠 CC-07: Confirmation dialogs use native `confirm()` and `prompt()`

Cancelling a queue job triggers `confirm("Cancel this queued job?")`. Saving a template triggers `prompt("Template name", ...)`.

**Problem**: Native browser dialogs are unstyled, cannot be themed, block the entire tab, and look completely out of place in a premium desktop application. They break the glassmorphism aesthetic entirely.

**Recommendation**: Replace all `confirm()` and `prompt()` calls with custom modal components styled to match the design system.

### 🟡 CC-08: No right-click context menus

Nowhere in the application can a user right-click to access actions. Tables, list items, and cards have no contextual menus.

**Problem**: Power users expect right-click → Delete, right-click → Duplicate, right-click → Export. Every action requires navigating to a button somewhere on the page.

**Recommendation**: Add context menus for all interactive elements: right-click a label row → Run Export, Edit, Duplicate, Delete. Right-click a queue job → Cancel, Retry, View Details.

### 🟡 CC-09: No keyboard shortcuts beyond ⌘K and ⌘B

The only keyboard shortcuts are ⌘K (command palette), ⌘B (toggle sidebar), and `/` (also opens command palette). There are no shortcuts for navigation (⌘1-9 for sidebar items), no shortcuts for common actions (⌘N for new label, ⌘Enter to submit), and no Escape key handling beyond the command palette.

**Recommendation**: Implement a comprehensive keyboard shortcut system:
- ⌘1-9: Navigate to sidebar items
- ⌘N: New (context-dependent: new label, new profile, etc.)
- ⌘Enter: Submit current form
- Escape: Close modal/dialog, then close sidebar on mobile
- ⌘F: Focus search/filter on current page
- Space: Toggle checkbox selection in tables
- Show available shortcuts via `?` key

### 🟡 CC-10: No drag-and-drop

The application has no drag-and-drop interactions anywhere. Label priority ordering, profile ordering, and dashboard widget layout are all candidates for drag-and-drop but use static ordering.

**Recommendation**: Add drag-and-drop for: dashboard widget reordering (promised in roadmap #50), label priority ordering, profile ordering, notification channel priority.

### 🟡 CC-11: Toast notifications are ephemeral and not storable

Toasts auto-dismiss after 4.5 seconds. There is no notification center or history to review past toasts. If a user misses a toast (e.g., "Export failed: rate limited"), they have no way to see what happened except by navigating to the relevant page.

**Recommendation**: Add a notification bell icon in the topbar that shows recent toasts/events. Allow users to click a toast to navigate to the relevant page before it dismisses.

### 🟢 CC-12: HTMX is loaded but unused

`base.html` includes an HTMX CDN script, but no template uses `hx-*` attributes. This is dead weight — approximately 20KB of JavaScript loaded on every page.

**Recommendation**: Remove the HTMX script tag until HTMX is actually used in templates.

### 🟢 CC-13: Flatpickr theme conflicts with dark/light mode

Flatpickr is styled via CSS overrides in `styles.css`, but the flatpickr calendar does not fully respect the application's theme variables. Some internal elements use hardcoded colors.

**Recommendation**: Fully theme Flatpickr to use CSS custom properties, or replace with a native-inspired date picker.

### 🟢 CC-14: No offline capability

The application requires a constant connection to the backend. If the server becomes unreachable (e.g., Raspberry Pi goes offline), the UI shows a disconnected state with no cached data and no offline actions.

**Recommendation**: Implement a service worker for offline shell. Cache the last-known dashboard state. Show a meaningful offline message with reconnection attempts.

---

## 18. Visual Design & Coherence

### 🟠 VIS-01: Glassmorphism is attractive but has legibility issues

The glass effect (backdrop-filter blur, semi-transparent backgrounds) creates depth but reduces text contrast against busy backgrounds. On the dashboard, stat cards overlaid on the gradient background can be hard to read when the background gradient shifts.

**Problem**: The `--text-muted` color (`#9aa0b9` on dark) has a contrast ratio of approximately 3.8:1 against the surface background when accounting for the blurred background showing through. This fails WCAG AA for normal text.

**Recommendation**: Increase muted text opacity. Consider reducing the glass blur intensity or adding a more opaque fallback for browsers that don't support backdrop-filter.

### 🟡 VIS-02: Three different icon systems in one application

The application uses: (1) Inline SVGs in `app.js` (the `ICONS` object with Feather-style paths), (2) SVG file includes in Jinja2 templates (`icons/home.svg`, etc.), (3) Emoji/Unicode characters in some places (✓ checkmark in wizard steps).

**Problem**: The inline SVGs in `app.js` are not visually consistent with the file-based SVGs. Some icons (home, building, key, tag, layers) exist only as files; others (search, sun, moon, bolt) exist only in the JS object. There is no single source of truth for icons.

**Recommendation**: Consolidate all icons into a single system — either all inline SVGs or all file-based includes. Ensure consistent stroke width (1.8px), 24×24 viewBox, and `currentColor` for theming.

### 🟡 VIS-03: Color usage is inconsistent across pages

The brand color (`--brand: #818cf8`) is used for: active nav links, primary buttons, chart accents, icon backgrounds, the command palette highlight, and focus rings. But some elements use different blues: brand-soft backgrounds, gradient overlays on stat cards, and the gauge bar use slightly different opacity values.

**Recommendation**: Define a strict color token system: `--color-primary`, `--color-primary-hover`, `--color-primary-subtle`, `--color-primary-text`. Never use raw hex values in component styles.

### 🟢 VIS-04: Typography is generally good but font loading causes FOUT

Inter and JetBrains Mono are loaded from Google Fonts via `<link>` tags. If the CDN is slow, text renders in the fallback system font before swapping to Inter, causing a flash of unstyled text (FOUT).

**Recommendation**: Add `font-display: swap` to the font loading strategy. Consider self-hosting fonts to eliminate the CDN dependency.

### 🟢 VIS-05: The version pill in the sidebar is easy to miss

The version number is shown as a small monospace pill at the bottom of the sidebar. It's useful for debugging but invisible to most users.

**Recommendation**: Keep the version pill but also show it in Settings/About. Consider showing update availability.

---

## 19. Workflow Analysis: End-to-End User Journeys

### Journey 1: First-Time User — "I want to export my Onshape parts as STLs"

**Current path**: Open app → See login/setup page → Create admin account (step 1/9) → Set storage path (2/9) → Create organization (3/9) → Add API key (4/9) → Create label (5/9) → Create profile (6/9) → Test connection (7/9) → View remote access (8/9) → Finish (9/9) → Dashboard (all zeros) → Click "Manual Export" in sidebar → Select label from dropdown → Pick date preset → Click Preview → Click Queue Export → (No immediate feedback) → Navigate to Queue → Wait → Check History → Find files in filesystem.

**Pain points**: 9-step wizard, zero-state dashboard, 4 separate page navigations to complete one export, no file browser to see results.

**Ideal path**: Open app → "Welcome! Let's export your first file" → Enter Onshape API key → The app discovers your labels → Pick a label → "Export as STL?" → Click Export → Progress bar fills → "Done! Files saved to ~/exports/today/. Open folder?" → 4 steps total.

### Journey 2: Returning User — "I need to export this week's updated parts"

**Current path**: Open app → Dashboard → Click "Manual Export" → Select label → Pick "This Week" preset → Click Preview → Click Queue Export → Navigate to Queue to confirm → Wait → Navigate to History to verify → Find files.

**Pain points**: Still 5+ clicks for a repeat action. No "Re-run last export" button. No template auto-apply.

**Ideal path**: Open app → Dashboard shows "3 labels have updates this week" → Click "Export All Updated" → Confirm → Done. Or: Open app → Click "Re-run Last Export" → Done (1 click).

### Journey 3: Administrator — "I need to add a new team member's API key"

**Current path**: Open app → Navigate to Organizations → Find the right org → Expand "Add credential" → Fill form → Submit → No test button → Navigate to Accounts to verify it appears → (It doesn't, because Organizations ≠ Accounts) → Confusion.

**Pain points**: Organizational model confusion, no inline testing, dual pages with inconsistent data.

**Ideal path**: Open app → Settings/Accounts → "Add API Key" → Enter keys → "Test" → Green check → Assign to label → Done (all on one page).

---

## 20. Summary of Findings

| Severity | Count | Key Themes |
|---|---|---|
| 🔴 Critical | 7 | Navigation overload, dual account model, missing undo, no form validation, no accessibility, settings is read-only, wizard too long |
| 🟠 High | 13 | Dashboard teaches nothing, queue loses context, system page is a grab-bag, no loading states, no context menus, browser dialogs |
| 🟡 Medium | 18 | Label/profile management gaps, scheduler inflexibility, history is flat, log page complexity, notification form usability |
| 🟢 Low | 15 | Visual polish, typography, dead dependencies, icon consistency |
| 🔵 Observation | 2 | Sidebar tooltips in collapsed mode, HTMX pre-loading |

**Total: 55 issues identified.**

---

## 21. Top 10 Actions (Priority-Ordered)

1. **Merge Organizations + Accounts into a single "API Keys" page** — eliminates the #1 source of user confusion
2. **Reduce navigation from 14 items to 6-7** — makes the app scannable and learnable
3. **Add undo to all destructive actions** — prevents data loss from misclicks
4. **Add client-side form validation to all forms** — eliminates round-trip errors
5. **Redesign the setup wizard to 4 steps** — reduces first-run friction by 55%
6. **Make the empty dashboard a guided onboarding experience** — turns a dead end into a path forward
7. **Add accessibility (ARIA labels, keyboard nav, focus trapping)** — makes the app usable by everyone
8. **Separate Settings into "Settings" (editable) and "About" (read-only)** — meets user expectations
9. **Add context menus and keyboard shortcuts** — enables power-user efficiency
10. **Implement consistent loading, empty, and error states** — makes the app feel polished

---

*End of UX Audit. Next: MASTER_UI_REDESIGN_PLAN.md*
