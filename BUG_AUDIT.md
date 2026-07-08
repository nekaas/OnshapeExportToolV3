# Bug Audit

**Date:** 2026-07-08

## Open Bugs

### BUG-001: Preview null-access JS errors (FIXED)
**Severity:** Critical
**Fixed:** 2026-07-08
**Description:** Alpine.js evaluated `x-text` expressions inside `x-if` blocks during initialization, causing `Cannot read properties of null` errors on Export page.
**Fix:** Replaced `x-if` guard divs with optional chaining (`preview?.label?.name || '—'`).

### BUG-002: XSS via group name (MITIGATED)
**Severity:** Medium
**Description:** Group names accept `<script>` tags. Stored in labels.json and rendered in UI. Alpine's `x-text` escapes HTML (safe), but server-side sanitization is missing.
**Fix needed:** Add HTML entity encoding in `_create_label` and `_update_label` helper functions, or add `@field_validator` on `friendly_name` in Pydantic models.

### BUG-003: Delete fails for groups with special characters (OPEN)
**Severity:** Low
**Description:** Groups with `<`, `>`, `/`, or `'` in their name cannot be deleted via UI. The DELETE request returns 404 because `encodeURIComponent` doesn't produce a path the server can match.
**Fix needed:** Either sanitize group names to prevent these characters, or improve server-side path parameter decoding.

### BUG-004: Toast messages show generic "error" (OPEN)
**Severity:** Low
**Description:** When form validation fails or API returns error, some toasts display "Error" / "error" instead of descriptive messages. Suspect toast function signature mismatch.
**Fix needed:** Audit all `window.oem.toast()` calls for consistent parameter order (title, message, kind).

### BUG-005: 422 error during Export page load (OPEN)
**Severity:** Low
**Description:** The Export page triggers a 422 (Unprocessable Content) response during initial load. Likely a preview endpoint called with empty/default parameters.
**Fix needed:** Prevent automatic preview fetch on page load, or handle empty state before calling preview endpoint.

### BUG-006: Refresh button appears on non-table pages (OPEN)
**Severity:** Cosmetic
**Description:** A "Refresh" button appears on pages that don't have data tables (Groups page). It's from the sectionPage template and appears even when `hasTable` is false.
**Fix needed:** Gate the Refresh button behind the `hasTable` condition or move it to page-specific templates.

## Closed Bugs

### BUG-007: EventBus.subscribe parameter name mismatch (FIXED)
**Date:** Prior session
**Description:** `EventBus.subscribe(event_type=...)` used wrong parameter name `event_type` instead of `types=[...]`, preventing worker from receiving events.

### BUG-008: test_pages_render intermittent failure (FIXED)
**Date:** Prior session
**Description:** Auth state leaked between tests causing `test_pages_render` to fail intermittently.

### BUG-009: test_batch_queue leaves stale jobs (KNOWN)
**Date:** Prior session
**Description:** Batch queue test creates jobs for labels "A"/"B" that don't exist in real config. Worker correctly fails them. Expected behavior, not a bug.
