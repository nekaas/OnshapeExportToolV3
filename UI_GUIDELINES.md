# UI Guidelines — Onshape Export Manager

> **Version**: 2.0 (Redesign)  
> **Date**: 2026-07-08  
> **Status**: Design System Specification — Implementation pending  

---

## Design Philosophy

The Onshape Export Manager is a **desktop application** that happens to run in a browser. It should feel like Docker Desktop, GitHub Desktop, or Obsidian — not like a CRUD web app. Every design decision flows from these principles:

1. **Self-Teaching** — First-time users understand the UI without documentation
2. **Intentional** — Nothing exists "just in case." Every element solves a specific problem
3. **Discoverable** — Features are visible; power-user features are accessible but unobtrusive
4. **Minimal Clicks** — Common actions: 1-2 clicks. No workflow: >3 clicks
5. **Coherent** — Feels like one product, not independent pages stitched together
6. **Forgiving** — Destructive actions have undo. Mistakes are easy to recover from

---

## 1. Typography

### Font Stack

| Role | Font | Weight | Usage |
|---|---|---|---|
| UI Text | Inter | 400, 500, 600, 700, 800 | All UI text, labels, buttons, navigation |
| Code / Data | JetBrains Mono | 400, 500 | API keys, Onshape IDs, log output, CLI commands, version numbers |

### Type Scale

| Token | Size | Line Height | Usage |
|---|---|---|---|
| `text-xs` | 0.7rem (11px) | 1.4 | Version pill, keyboard shortcuts in UI, chart labels |
| `text-sm` | 0.8rem (13px) | 1.5 | Secondary text, metadata, form labels, table cells |
| `text-base` | 0.9rem (14px) | 1.5 | Body text, navigation items, card content |
| `text-lg` | 1.05rem (17px) | 1.4 | Card titles, section headers |
| `text-xl` | 1.2rem (19px) | 1.3 | Page headings |
| `text-2xl` | 2rem (32px) | 1.2 | Stat card values, gauge numbers |
| `text-3xl` | 2.5rem (40px) | 1.1 | Hero numbers (success rate, total exports) |

### Font Weights

| Weight | Token | Usage |
|---|---|---|
| 400 | Regular | Body text, form labels, metadata |
| 500 | Medium | Navigation items, button text, table headers |
| 600 | Semibold | Card titles, emphasized values, links |
| 700 | Bold | Page headings, stat values, badge text |
| 800 | Extrabold | Brand title, hero numbers, gauge values |

---

## 2. Colors

### Dark Theme (Default)

| Token | Hex | Usage |
|---|---|---|
| `--bg-primary` | `#0a0b14` | Page background (deepest) |
| `--bg-secondary` | `#141627` | Elevated surfaces, cards |
| `--surface` | `rgba(22, 24, 38, 0.72)` | Glass surfaces, sidebar, topbar |
| `--surface-raised` | `rgba(36, 39, 58, 0.85)` | Modals, command palette, dropdowns |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | Card borders, dividers |
| `--border-default` | `rgba(255, 255, 255, 0.14)` | Input borders, active borders |
| `--text-primary` | `#e7e9f3` | Primary text, headings |
| `--text-secondary` | `#9aa0b9` | Secondary text, descriptions |
| `--text-tertiary` | `#6b7192` | Muted text, placeholders, disabled |

### Light Theme

| Token | Hex | Usage |
|---|---|---|
| `--bg-primary` | `#f5f6fb` | Page background |
| `--bg-secondary` | `#eef1fb` | Elevated surfaces |
| `--surface` | `rgba(255, 255, 255, 0.78)` | Glass surfaces |
| `--surface-raised` | `rgba(255, 255, 255, 0.95)` | Modals, dropdowns |
| `--border-subtle` | `rgba(15, 23, 42, 0.08)` | Card borders |
| `--border-default` | `rgba(15, 23, 42, 0.14)` | Input borders |
| `--text-primary` | `#1a1c2c` | Primary text |
| `--text-secondary` | `#5b617a` | Secondary text |
| `--text-tertiary` | `#8b90a8` | Muted text |

### Semantic Colors

| Token | Dark | Light | Usage |
|---|---|---|---|
| `--color-brand` | `#818cf8` | `#4f46e5` | Primary actions, active states, links |
| `--color-brand-hover` | `#6366f1` | `#4338ca` | Button hover, link hover |
| `--color-brand-subtle` | `rgba(99,102,241,0.16)` | `rgba(79,70,229,0.1)` | Selected backgrounds, icon containers |
| `--color-success` | `#34d399` | `#059669` | Success states, healthy accounts, completed exports |
| `--color-success-subtle` | `rgba(52,211,153,0.15)` | `rgba(5,150,105,0.12)` | Success backgrounds |
| `--color-warning` | `#fbbf24` | `#d97706` | Warnings, degraded accounts, rate limited |
| `--color-warning-subtle` | `rgba(251,191,36,0.15)` | `rgba(217,119,6,0.12)` | Warning backgrounds |
| `--color-danger` | `#f87171` | `#dc2626` | Errors, failed exports, critical alerts |
| `--color-danger-subtle` | `rgba(248,113,113,0.15)` | `rgba(220,38,38,0.1)` | Error backgrounds |
| `--color-info` | `#60a5fa` | `#2563eb` | Informational badges |

### Contrast Requirements (WCAG AA)

- **Normal text** (14px+): ≥4.5:1 contrast ratio against background
- **Large text** (18px+ or 14px+ bold): ≥3:1
- **UI components**: ≥3:1 against adjacent colors
- **Focus indicators**: ≥3:1 against both the element and the background

---

## 3. Spacing System

Based on a 4px grid. All spacing values are multiples of 4.

| Token | Value | Usage |
|---|---|---|
| `--space-0` | 0 | No space |
| `--space-1` | 4px | Tight inline spacing (icon + text, badge padding) |
| `--space-2` | 8px | Gap between related items (nav items, chips, form row gap) |
| `--space-3` | 12px | Standard gap (card padding internal, sidebar padding) |
| `--space-4` | 16px | Component gap (card grid gap, section gap, sidebar nav gap) |
| `--space-5` | 20px | Section padding, card padding |
| `--space-6` | 24px | Page padding (content area), large section gap |
| `--space-8` | 32px | Major section divider |
| `--space-10` | 40px | Page-level spacing |
| `--space-12` | 48px | Hero section spacing |

### Layout Widths

| Token | Value | Usage |
|---|---|---|
| `--sidebar-w` | 256px | Expanded sidebar width |
| `--sidebar-w-collapsed` | 76px | Collapsed sidebar width |
| `--topbar-h` | 64px | Top bar height |
| `--content-max-w` | 1280px | Maximum content width (centered) |
| `--modal-sm` | 400px | Small modal (confirmations, alerts) |
| `--modal-md` | 560px | Medium modal (forms, details) |
| `--modal-lg` | 720px | Large modal (wizards, settings) |

---

## 4. Border Radius

Consistent corner rounding across the application.

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 8px | Inputs, chips, small cards, badge backgrounds |
| `--radius-md` | 12px | Buttons, stat cards, form fields, table rows |
| `--radius-lg` | 16px | Cards, panels, sidebar, modals |
| `--radius-xl` | 24px | Large containers, hero cards |
| `--radius-full` | 9999px | Pills, badges, toggle switches, segmented controls |

---

## 5. Shadows & Elevation

### Shadow Scale

| Token | Value | Elevation | Usage |
|---|---|---|---|
| `--shadow-none` | `none` | 0 | Flat elements, table cells |
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.12)` | 1 | Cards resting on surface |
| `--shadow-md` | `0 4px 16px rgba(0,0,0,0.15)` | 2 | Hovered cards, dropdowns |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.2)` | 3 | Modals, command palette |
| `--shadow-xl` | `0 20px 60px rgba(0,0,0,0.35)` | 4 | Highest elevation (rare) |

### Glass Effect

Used on sidebar, topbar, and cards for the premium glassmorphism aesthetic.

```css
.glass {
  background: var(--surface);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--border-subtle);
}
```

**Accessibility note**: Glass surfaces must maintain sufficient text contrast. If `backdrop-filter` is not supported (older browsers), fall back to `var(--surface-raised)` with no transparency.

---

## 6. Component Library

### 6.1 Buttons

Three variants, three sizes.

| Variant | Usage |
|---|---|
| **Primary** | Main action on page (Export Now, Save, Create) |
| **Secondary** | Alternative action (Cancel, Preview, Refresh) |
| **Ghost** | Low-emphasis action (Edit, Show Files, toolbar icons) |

| Size | Height | Padding | Font | Usage |
|---|---|---|---|---|
| **Small** | 32px | 8px 12px | `text-xs` | Table actions, chip-like buttons |
| **Medium** | 40px | 10px 16px | `text-sm` | Standard buttons |
| **Large** | 48px | 14px 24px | `text-base` | Primary CTAs, hero buttons |

```css
.btn-primary {
  background: linear-gradient(135deg, var(--color-brand), var(--color-brand-hover));
  color: #fff;
  border: none;
  font-weight: 600;
}
.btn-primary:hover { filter: brightness(1.08); }
.btn-primary:active { filter: brightness(0.95); }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-secondary {
  background: var(--surface-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  font-weight: 500;
}
.btn-secondary:hover { border-color: var(--border-default); background: var(--surface); }

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
  font-weight: 500;
}
.btn-ghost:hover { color: var(--text-primary); background: var(--surface); }
```

### 6.2 Form Fields

```css
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
}
.field-input {
  height: 40px;
  padding: 0 12px;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  transition: border-color 150ms ease;
}
.field-input:focus {
  border-color: var(--color-brand);
  outline: none;
  box-shadow: 0 0 0 3px var(--color-brand-subtle);
}
.field-input.has-error {
  border-color: var(--color-danger);
}
.field-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}
.field-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
```

### 6.3 Cards

```css
.card {
  background: var(--surface);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}
.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
  margin: 0;
}
.card-subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: 2px;
}
```

### 6.4 Tables

```css
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.data-table th {
  text-align: left;
  padding: 10px 14px;
  color: var(--text-tertiary);
  font-weight: 600;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-subtle);
  user-select: none;
}
.data-table th.sortable { cursor: pointer; }
.data-table th.sortable:hover { color: var(--text-secondary); }
.data-table th.sorted { color: var(--color-brand); }
.data-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
}
.data-table tbody tr:hover { background: var(--surface); }
.data-table tbody tr.selected { background: var(--color-brand-subtle); }
```

### 6.5 Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.badge-success { background: var(--color-success-subtle); color: var(--color-success); }
.badge-warning { background: var(--color-warning-subtle); color: var(--color-warning); }
.badge-danger  { background: var(--color-danger-subtle);  color: var(--color-danger); }
.badge-info    { background: var(--color-brand-subtle);    color: var(--color-brand); }
.badge-muted   { background: var(--surface);              color: var(--text-tertiary); }
```

### 6.6 Toasts

```css
.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-lg);
  max-width: 380px;
  animation: toast-enter 300ms var(--ease-out);
}
.toast-success { border-left: 3px solid var(--color-success); }
.toast-error   { border-left: 3px solid var(--color-danger); }
.toast-info    { border-left: 3px solid var(--color-brand); }
.toast-warning { border-left: 3px solid var(--color-warning); }
.toast-undo {
  display: flex;
  gap: 12px;
  align-items: center;
}
.toast-undo button {
  background: var(--color-brand-subtle);
  color: var(--color-brand);
  border: none;
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-weight: 600;
  cursor: pointer;
}
```

### 6.7 Modals

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal);
  display: grid;
  place-items: center;
  animation: fade-in 200ms ease;
}
.modal {
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  animation: modal-enter 300ms var(--ease-out);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
}
.modal-body {
  padding: var(--space-6);
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
  border-top: 1px solid var(--border-subtle);
}
```

### 6.8 Empty States

```css
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}
.empty-state-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-xl);
  background: var(--color-brand-subtle);
  color: var(--color-brand);
  display: grid;
  place-items: center;
  margin-bottom: var(--space-5);
}
.empty-state-title {
  font-size: var(--text-lg);
  font-weight: 700;
  margin-bottom: var(--space-2);
}
.empty-state-description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 360px;
  margin-bottom: var(--space-6);
}
```

### 6.9 Loading States (Skeletons)

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    var(--surface-raised) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}
.skeleton-text  { height: 14px; width: 80%; margin-bottom: 8px; }
.skeleton-title { height: 20px; width: 60%; margin-bottom: 12px; }
.skeleton-card  { height: 120px; width: 100%; border-radius: var(--radius-lg); }
.skeleton-avatar { width: 40px; height: 40px; border-radius: var(--radius-full); }

@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

### 6.10 Progress Bars

```css
.progress {
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--surface);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-brand), var(--color-brand-hover));
  transition: width 300ms var(--ease-out);
}
.progress-fill.indeterminate {
  width: 30%;
  animation: progress-indeterminate 1.5s infinite;
}
@keyframes progress-indeterminate {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
```

---

## 7. Iconography

### System

All icons use **Feather Icons** (https://feathericons.com/) as the standard set.

- **Stroke width**: 1.8px
- **ViewBox**: 0 0 24 24
- **Color**: `currentColor` (inherits from parent text color)
- **Sizing**: 16px for inline, 20px for navigation, 24px for standalone

### Icon Usage Map

| Icon | Usage |
|---|---|
| `home` | Home/Dashboard navigation |
| `key` | API Keys navigation |
| `tag` | Labels navigation |
| `upload-cloud` or `download` | Export navigation |
| `clock` | History navigation, scheduler, timestamps |
| `settings` | Settings gear icon |
| `plus` | Create actions (Add Key, New Label) |
| `search` | Search/filter |
| `check-circle` | Success status |
| `alert-triangle` | Warning status |
| `x-circle` | Error/failure status |
| `pause-circle` | Disabled/paused status |
| `refresh-cw` | Refresh, retry |
| `trash-2` | Delete |
| `copy` | Copy to clipboard |
| `external-link` | Open external link |
| `folder` | Show files, open folder |
| `play` | Start worker, run export |
| `square` | Stop worker |
| `more-horizontal` | Overflow menu |
| `chevron-down` | Expand/collapse |
| `sun` / `moon` | Theme toggle |
| `bell` | Notifications |
| `activity` | System health, activity log |
| `terminal` | Logs, CLI commands |
| `hard-drive` | Storage, backups |
| `wifi` | Remote access, connectivity |

---

## 8. Animation & Motion

### Principles

- **Fast**: Animations should be 150-400ms. Never longer than 500ms.
- **Purposeful**: Motion should indicate spatial relationships or draw attention to changes.
- **Respectful**: Honor `prefers-reduced-motion: reduce`. Disable all non-essential animations.

### Animation Tokens

```css
:root {
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);      /* Enter animations */
  --ease-in: cubic-bezier(0.4, 0, 1, 1);            /* Exit animations */
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);    /* Continuous animations */
  --duration-fast: 150ms;   /* Micro-interactions: hover, focus */
  --duration-normal: 250ms; /* Standard transitions: toggle, expand */
  --duration-slow: 400ms;   /* Page transitions, modal open/close */
}
```

### Animation Catalog

| Animation | Duration | Easing | Usage |
|---|---|---|---|
| Page enter | 400ms | `ease-out` | Fade + 10px slide up when navigating to a page |
| Modal open | 300ms | `ease-out` | Scale from 95% to 100% + fade in overlay |
| Modal close | 200ms | `ease-in` | Scale to 95% + fade out overlay |
| Toast enter | 300ms | `ease-out` | Slide in from right + fade in |
| Toast exit | 200ms | `ease-in` | Slide out to right + fade out |
| Sidebar toggle | 280ms | `ease-out` | Width transition |
| Hover state | 150ms | `ease-out` | Background/border color change |
| Focus ring | 150ms | `ease-out` | Box-shadow transition |
| Progress fill | 300ms | `ease-out` | Width transition on determinate progress |
| Chart update | 0ms | — | Charts should update instantly (no animation) for performance |
| Skeleton shimmer | 1500ms | `ease-in-out` | Continuous looping gradient |

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 9. Accessibility

### Keyboard Navigation

All interactive elements must be reachable and operable via keyboard:

- **Tab**: Move focus forward through interactive elements
- **Shift+Tab**: Move focus backward
- **Enter/Space**: Activate focused button/link
- **Escape**: Close modal, close command palette, cancel action
- **Arrow keys**: Navigate within lists, tables, dropdowns, and the command palette
- **⌘K**: Open command palette
- **⌘B**: Toggle sidebar
- **?**: Show keyboard shortcuts help

### Focus Management

- **Focus indicators**: Visible 3px ring using `--color-brand` on all focusable elements
- **Focus trapping**: Modals and the command palette trap focus within themselves
- **Focus restoration**: When a modal closes, focus returns to the element that opened it
- **Skip link**: First focusable element on each page: "Skip to main content"

### ARIA Requirements

| Element | Required ARIA |
|---|---|
| Sidebar `<nav>` | `role="navigation"`, `aria-label="Main navigation"` |
| Active nav link | `aria-current="page"` |
| Sidebar toggle button | `aria-expanded="true/false"`, `aria-label="Toggle sidebar"` |
| Theme toggle button | `aria-label="Toggle dark/light theme"`, `aria-pressed="true/false"` |
| Modal overlay | `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"` |
| Command palette | `role="combobox"`, `aria-expanded="true/false"`, `aria-label="Search"` |
| Toast container | `role="status"`, `aria-live="polite"`, `aria-atomic="false"` |
| Live indicator | `role="status"`, `aria-live="polite"`, `aria-label="Connection status: Live/Offline"` |
| Badge | `role="status"` if conveying state |
| Data table | `role="table"`, `aria-label="[Name] table"` |
| Sortable column | `aria-sort="ascending/descending/none"` |
| Progress bar | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| Loading state | `aria-busy="true"`, `aria-label="Loading..."` |
| Error message | `role="alert"` |

### Screen Reader Announcements

- **Page navigation**: Announce page title after navigation completes
- **Async updates**: Use `aria-live="polite"` regions for SSE/socket-driven updates
- **Export status changes**: Announce "Export completed successfully" or "Export failed"
- **Toast appearance**: Announce toast content (via `role="status"`)
- **Confirmation**: Announce after create/update/delete actions

### Color & Contrast

- All text must meet WCAG AA contrast ratios (see Colors section)
- Never convey information through color alone — always include an icon or text label
- The glassmorphism effect must not reduce contrast below accessible levels
- Test with a contrast checker (e.g., WebAIM Contrast Checker) during development

---

## 10. Responsive Behavior

### Breakpoints

| Breakpoint | Width | Target |
|---|---|---|
| **Mobile** | < 768px | Phone portrait/landscape |
| **Tablet** | 768px - 1024px | iPad, small laptop |
| **Desktop** | 1024px - 1440px | Standard monitor, laptop |
| **Large Desktop** | > 1440px | External monitor, 4K display |

### Layout Changes by Breakpoint

**Mobile (< 768px)**:
- Sidebar: hidden by default, revealed via hamburger menu overlay
- Topbar: simplified (hamburger + page title + theme toggle)
- Stat cards: 2 columns
- Content: single column, full width
- Tables: horizontal scroll with sticky first column
- Modals: full-screen
- Toast: bottom-center, full width

**Tablet (768px - 1024px)**:
- Sidebar: collapsed by default (icons only)
- Stat cards: 3 columns
- Content: can use 2-column grids
- Modals: centered, max 80vw

**Desktop (1024px+)**:
- Full layout as designed
- Expanded sidebar with icons + labels
- Multi-column grids

### Touch Targets

All interactive elements must have a minimum touch target of **44×44px** (WCAG 2.5.5). This applies to:
- Buttons
- Navigation links
- Table row actions
- Checkboxes and toggles
- Chip/tag dismiss buttons

---

## 11. Content Guidelines

### Terminology

| Use | Avoid | Rationale |
|---|---|---|
| "Export" | "Queue Export" | The user's goal is to export, not to interact with a queue |
| "API Key" | "Account", "Credential" | More familiar term for the target audience |
| "Label" | "Tag" | Consistent with Onshape's own terminology |
| "Home" | "Dashboard" | More welcoming, less corporate |
| "Start Export" / "Export Now" | "Run", "Execute" | Action-oriented, user-friendly |
| "Scheduled" | "Cron job" | Avoid implementation jargon |

### Tone

- **Direct and helpful** — Not marketing copy
- **Active voice** — "Add your API key" not "API keys can be added"
- **No jokes or personality** — This is professional tooling
- **Assume technical audience** — Users know what STL, STEP, API keys are
- **Explain unfamiliar concepts** — Briefly explain Onshape-specific concepts (label IDs)

### Error Messages

Good error messages follow this pattern:
1. What happened (in plain language)
2. Why it happened
3. What to do about it

```
❌ Bad:  "HTTP 429"
✅ Good: "Onshape rate limit reached on 'Primary' key.
         This account can make more requests in 12 minutes.
         [Switch to Backup key] [Wait and retry]"
```

---

## 12. File Organization (Frontend)

```
ui/
├── static/
│   ├── css/
│   │   ├── tokens.css        # Design tokens (colors, spacing, typography)
│   │   ├── base.css          # Reset, body, typography, glass effect
│   │   ├── layout.css        # Sidebar, topbar, main area, responsive
│   │   ├── components.css    # Buttons, forms, cards, tables, badges, modals
│   │   └── pages/
│   │       ├── home.css
│   │       ├── api-keys.css
│   │       ├── labels.css
│   │       ├── export.css
│   │       ├── history.css
│   │       └── settings.css
│   ├── js/
│   │   ├── app.js            # Alpine.js init, global state
│   │   ├── services/
│   │   │   ├── api.js        # fetchJSON, API helpers
│   │   │   └── events.js     # SSE, WebSocket connection
│   │   ├── components/
│   │   │   ├── toast.js
│   │   │   ├── modal.js
│   │   │   ├── command-palette.js
│   │   │   ├── confirm-dialog.js
│   │   │   └── data-table.js
│   │   └── pages/
│   │       ├── home.js
│   │       ├── api-keys.js
│   │       ├── labels.js
│   │       ├── export.js
│   │       ├── history.js
│   │       └── settings.js
│   └── icons/
│       └── sprite.svg        # Single SVG sprite for all icons
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── api-keys.html
│   ├── labels.html
│   ├── export.html
│   ├── history.html
│   ├── settings.html
│   ├── login.html
│   └── partials/
│       ├── sidebar.html
│       ├── topbar.html
│       └── toast-container.html
```

---

*End of UI Guidelines. This document serves as the single source of truth for all design decisions in the Onshape Export Manager.*
