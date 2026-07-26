# Bug Audit — Onshape Export Manager

> Generated: 2026-07-26 | Auditor: QA Lead  
> 178 tests pass · 1 warning (Starlette deprecation)

---

## BUG-001 · CRITICAL — Broken `favoriteTemplates`/`recentTemplates` Getters

- **Location**: `onshape_export_manager/ui/static/app.js:918-923`
- **Severity**: Critical — crashes any page that references these getters
- **Description**: The getters `favoriteTemplates` and `recentTemplates` reference `this.manualTemplates` and `this.manualRecentTemplates`, which were removed during template management simplification (SIMPLIFICATION_PLAN.md item 5). These getters will throw `TypeError: Cannot read properties of undefined`.
- **Steps to Reproduce**: Open the Export page — any template reference in HTML triggers these getters.
- **Root Cause**: Incomplete cleanup — the state arrays were deleted but their getter consumers were not.
- **Fix**: Delete both getters (lines 918-923). They are dead code.
- **Status**: 🔴 Not fixed

---

## BUG-002 · HIGH — Broken `setTheme` Method (Copy-Paste Error)

- **Location**: `onshape_export_manager/ui/static/app.js:951-954`
- **Severity**: High — method does not do what its name says
- **Description**: The `setTheme(mode)` method in `sectionPage` contains the body of `sortBy()` instead of theme-switching logic:
  ```js
  setTheme(mode) {
    if (this.sortKey === key) this.sortDir = this.sortDir === "asc" ? "desc" : "asc";
    else {
      this.sortKey = key;
      this.sortDir = "asc";
    }
  }
  ```
  `key` is undefined here. This is a copy-paste error.
- **Steps to Reproduce**: Call `setTheme("dark")` from any section page — it will silently do nothing (or crash if `key` is not defined).
- **Root Cause**: Copy-paste from `sortBy()` method during refactoring.
- **Fix**: Replace with actual theme logic:
  ```js
  setTheme(mode) {
    const dark = mode === "dark";
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("oem-theme", dark ? "dark" : "light"); } catch (e) {}
    if (window.oem) { window.oem.isDark = dark; }
  }
  ```
- **Status**: 🔴 Not fixed

---

## BUG-003 · MEDIUM — Dead Palette CSS Not Removed

- **Location**: `onshape_export_manager/ui/static/styles.css:723-739`
- **Severity**: Medium — dead code, no runtime impact but increases CSS payload
- **Description**: The palette CSS classes (`.palette-overlay`, `.palette`, `.palette-input`, `.palette-results`, `.palette-group-title`, `.palette-item`, etc.) are still present despite the command palette being removed from HTML and JS.
- **Fix**: Delete lines 723-739 from styles.css.
- **Status**: 🔴 Not fixed (previously attempted, incorrect match string)

---

## BUG-004 · LOW — Dead CSS Classes (search-trigger, live-indicator)

- **Location**: `onshape_export_manager/ui/static/styles.css:222-251`
- **Severity**: Low — dead CSS, no runtime impact
- **Description**: `.search-trigger`, `.search-trigger-text`, `.search-trigger kbd`, `.live-indicator`, `.live-indicator .dot`, `.live-indicator.live` are all dead CSS. The HTML elements that used them were removed from `base.html`.
- **Fix**: Remove lines 222-251 from styles.css.
- **Status**: 🟡 Not fixed (low priority)

---

## BUG-005 · LOW — `--text-muted` Reference in Deleted Code

- **Location**: `onshape_export_manager/ui/static/app.js` (in removed `renderCharts`)
- **Severity**: Low — code already removed (was `getPropertyValue("--text-muted")`)
- **Description**: The `renderCharts` function (now deleted) referenced `--text-muted`. This was fixed by removing the entire `dashboardPage` function. No remaining references.
- **Status**: ✅ Fixed

---

## BUG-006 · LOW — `templateId()` Utility Function Orphaned

- **Location**: `onshape_export_manager/ui/static/app.js:95-98`
- **Severity**: Low — dead code, no callers
- **Description**: `templateId()` function was only called by now-deleted template management code.
- **Status**: ✅ Fixed (removed in simplification pass)

---

## BUG-007 · LOW — Duplicate `setTheme` in sectionPage

- **Location**: See BUG-002
- **Severity**: Low — the real `setTheme` exists on `appShell`; this broken copy on `sectionPage` is dead code.
- **Description**: The `appShell.setTheme()` method works correctly. The broken `sectionPage.setTheme()` overrides nothing usefully.
- **Status**: 🔴 Not fixed

---

## Summary

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| BUG-001 | 🔴 Critical | Broken template getters | Not fixed |
| BUG-002 | 🟠 High | Broken setTheme copy-paste | Not fixed |
| BUG-003 | 🟡 Medium | Dead palette CSS | Not fixed |
| BUG-004 | 🟢 Low | Dead search/live CSS | Not fixed |
| BUG-005 | 🟢 Low | --text-muted in deleted code | Fixed |
| BUG-006 | 🟢 Low | Orphaned templateId() | Fixed |
| BUG-007 | 🟢 Low | Duplicate broken setTheme | Not fixed |
