# User Workflows

## First-Run Setup

1. Start app → `python app.py --mode desktop`
2. Browser opens to **Setup Wizard**
3. Create owner account (username + password, min 8 chars)
4. Set exports directory (default: `onshape_export_manager/exports`)
5. Setup complete → redirected to Dashboard

## Workflow: Add an Onshape API Account

1. Navigate to **API Keys** page
2. Click "New Organization" or use existing
3. Fill name, type, description
4. Click "Create Organization"
5. Click "+ Add API Key" under the organization
6. Enter key name, access key, secret key
7. Click "Test" to verify connectivity
8. Account appears in the accounts table with health status

## Workflow: Create a Group

1. Navigate to **Groups** page
2. Expand an account in the tree
3. Click "+ Create Group"
4. Fill in:
   - **Group Name** — friendly name (e.g., "Robotics Parts")
   - **Onshape Label ID** — 24-char hex from Onshape
   - **Export Profile** — choose from dropdown (STL, STEP, etc.)
   - **Schedule** — optional (None, 15min, 30min, hourly, daily, weekly)
5. Click "Create"
6. Group appears under the account in the tree

## Workflow: Get an Onshape Label ID

1. Open your Onshape document in a browser
2. Navigate to: `https://cad.onshape.com/api/documents/{YOUR_DOCUMENT_ID}/labels`
3. Copy the `id` field from the response
4. Paste into the "Onshape Label ID" field when creating a Group

## Workflow: Manual Export (Batch via Tree)

1. Navigate to **Export** page (or **Groups** page)
2. In the tree selector:
   - Expand an account to see its Groups
   - Check the Groups you want to export
   - Or check the account to select all its Groups
3. The "Export Selected" button shows count (e.g., "3 selected")
4. Click "Export Selected"
5. Toast notification confirms "Queued: 3 export(s) enqueued"

## Workflow: Manual Export (Single with Preview)

1. Navigate to **Export** page
2. Scroll to "Manual Export" section
3. Select a Group from the dropdown
4. Optionally override the Export Profile
5. Set a date range (Today, This Week, Custom Range)
6. Click "Preview" to see estimated documents and API calls
7. Click "Queue Export" to submit

## Workflow: Monitor Exports

1. **Dashboard** shows:
   - Export Activity chart (success vs failed, 14 days)
   - Account Health donut
   - Queue breakdown (pending, running, completed, failed)
   - Recent Exports table
2. **History** page shows all exports with filtering and sorting
3. Failed exports appear in red; click to see error details

## Workflow: Enable/Disable a Group

1. Navigate to **Groups** page
2. Expand the account containing the Group
3. Click the "Disable" button next to the Group
4. Button changes to "Enable"
5. Disabled Groups are skipped by scheduler and don't appear in export dropdowns

## Workflow: Delete a Group

1. Navigate to **Groups** page
2. Expand the account containing the Group
3. Click the "✕" button next to the Group
4. Confirmation dialog appears: "Delete group 'X'? This cannot be undone."
5. Click "Delete" to confirm, or "Cancel" to abort

## Workflow: Move a Group to Another Account

1. Navigate to **Groups** page
2. Expand the account containing the Group
3. Use the "Move to…" dropdown next to the Group
4. Select the target account
5. Group moves and appears under the new account

## Workflow: Toggle Theme

1. Click the "Toggle theme" button in the top bar
2. Switches between Dark and Light mode
3. Preference stored via API

## Workflow: Start/Stop Worker

1. Navigate to **Settings** → General tab
2. View Worker status (Running/Stopped), jobs processed, last tick
3. Click "Stop Worker" to pause processing
4. Click "Start Worker" to resume
5. Also visible on Dashboard and Export pages

## Workflow: View Logs

1. Navigate to **Settings** → Logs tab
2. Select log area from dropdown: app, errors, api, export, scheduler, queue, web, worker, events, audit, notifications
3. Last 300 lines displayed
4. Click "Refresh" to reload

## Workflow: Create a Backup

1. Navigate to **Settings** → Backups tab
2. Click "Create Backup"
3. Backup saved to `database/backups/` with timestamp
4. Includes all config files + SQLite database

## Workflow: Check Account Health

1. Navigate to **API Keys** page
2. Each credential shows health status: healthy, degraded, rate_limited, failed, disabled
3. Click "Test" to verify connectivity
4. Dashboard shows aggregate Account Health donut chart
