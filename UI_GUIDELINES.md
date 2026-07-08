# UI Guidelines

## Design System

### Theme
- **Dark-first** glassmorphism aesthetic
- CSS custom properties on `:root` for all colors
- Light theme via class toggle on `<html>`

### Color Palette
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `--bg` | `#0a0b14` | `#f8f9fc` | Page background |
| `--surface` | `rgba(22,24,38,0.72)` | `rgba(255,255,255,0.85)` | Card backgrounds (glass) |
| `--text` | `#e7e9f3` | `#1a1c2e` | Primary text |
| `--text-muted` | `#9aa0b9` | `#6b7280` | Secondary text |
| `--brand` | `#818cf8` | `#6366f1` | Primary actions, links |
| `--success` | `#34d399` | `#10b981` | Healthy, completed |
| `--warning` | `#fbbf24` | `#f59e0b` | Degraded, pending |
| `--red` | `#ef4444` | `#dc2626` | Failed, error, danger |

### Typography
- System font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Monospace: `"JetBrains Mono", "Fira Code", monospace`
- Heading scale: `1.25rem` → `1.1rem` → `1rem`
- Body: `0.88rem`
- Labels/captions: `0.72rem`

### Spacing
- Base unit: 4px (Tailwind default)
- Card padding: 16–24px
- Page gap: 16px
- Section gap: 18px

### Border Radius
- Cards: `--radius` (16px)
- Buttons/inputs: `--radius-sm` (10px)
- Modals: 20px

### Shadows & Glass
- `.glass` class: `backdrop-filter: blur(12px)` + semi-transparent background
- Border: `1px solid var(--border)` (8% white / 10% black)
- Hover: border brightens to `var(--border-strong)` (14% / 18%)

---

## Component Patterns

### Cards
```html
<div class="card glass">
  <div class="card-head">
    <h2 class="card-title">Title</h2>
    <p class="card-sub">Subtitle</p>
  </div>
  <!-- card body -->
</div>
```

### Buttons
| Class | Usage |
|-------|-------|
| `.btn.btn-primary` | Primary action (brand color) |
| `.btn.btn-ghost` | Secondary action |
| `.btn.btn-sm` | Compact button |
| `.btn.btn-primary.btn-sm` | Compact primary |

```html
<button class="btn btn-primary">
  <span x-html="icons.bolt"></span>
  <span>Action</span>
</button>
```

### Badges
```html
<span class="badge badge-ok">Healthy</span>
<span class="badge badge-muted">Disabled</span>
```
Classes: `badge-ok` (green), `badge-muted` (gray), `badge-warn` (yellow), `badge-danger` (red)

### Forms
```html
<label class="field">
  <span>Label</span>
  <input x-model="form.field" placeholder="..." />
</label>
```

Grid layout for forms:
```html
<div class="form-grid">
  <label class="field">...</label>
  <label class="field">...</label>
</div>
```

### Data Tables
```html
<div class="table-wrap">
  <table class="data-table">
    <thead><tr><th>Col</th></tr></thead>
    <tbody><tr><td>Data</td></tr></tbody>
  </table>
</div>
```

### Toasts
```js
window.oem.toast("Title", "Message", "success");   // green
window.oem.toast("Title", "Message", "error");     // red
window.oem.toast("Title", "Message", "info");      // blue
```

### Tree View (Groups page)
- Account header: clickable, caret rotates 90° on expand
- Group row: checkbox, name, enable/disable toggle, profile badge, move dropdown, delete button
- Create button at bottom of each account's group list
- Delete confirmation dialog with red border

---

## Frontend Architecture

### Technology
- **Alpine.js 3.13** — reactive data, `x-data`, `x-if`, `x-for`, `x-text`, `x-model`
- **Chart.js 4.4** — dashboard charts (activity line, health donut)
- **Flatpickr 4.6** — date pickers on Export page
- **Tailwind CSS** (CDN, dev only — should be compiled for production)

### Component Registry
```js
document.addEventListener("alpine:init", () => {
  window.Alpine.data("appShell", appShell);       // sidebar, nav, toasts
  window.Alpine.data("dashboardPage", dashboardPage); // home
  window.Alpine.data("sectionPage", sectionPage);  // all other pages
  window.Alpine.data("treeSelector", treeSelector); // groups tree
});
```

### Page Routing
- Single-page app: Jinja2 renders `section.html` with Alpine.js switching views
- `page` variable from server determines which template section renders
- `PAGE_CONFIG` object maps page slugs to API endpoints and table columns

### API Pattern
```js
// GET
fetchJSON("/api/endpoint").then(data => { ... })

// POST
fetch("/api/endpoint", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ... })
}).then(r => r.json()).then(d => { ... })
```

---

## Page Layout

```
┌──────────────────────────────────────────────────┐
│ Top Bar: hamburger │ page title │ search │ live │ theme │
├──────────┬───────────────────────────────────────┤
│ Sidebar  │                                       │
│          │         Main Content Area              │
│ • Home   │                                       │
│ • Keys   │    Cards / Tables / Forms / Trees      │
│ • Groups │                                       │
│ • Export │                                       │
│ • History│                                       │
│          │                                       │
│ Settings │                                       │
│ Sign out │                                       │
│ v0.1.0   │                                       │
└──────────┴───────────────────────────────────────┘
```

### Sidebar
- Collapsible (76px → 256px)
- Active page highlighted
- Fixed position, scrolls independently
- Settings and Sign out at bottom

### Top Bar
- Sticky
- Hamburger for mobile sidebar toggle
- ⌘K search button (placeholder)
- Live updates indicator
- Theme toggle

---

## States

Every interactive element must handle these states:
1. **Loading** — spinner, skeleton, or "Loading…" text
2. **Empty** — "No X yet" with helpful action button
3. **Error** — toast notification + inline error message
4. **Success** — toast notification + visual confirmation
5. **Disabled** — grayed out with `disabled` attribute

---

## Accessibility
- All form inputs have associated labels
- Buttons have visible text (not icon-only)
- Color is never the sole indicator of state (badges + text)
- Keyboard navigation: Tab through form fields, Enter to submit
- `prefers-reduced-motion` respected for animations
