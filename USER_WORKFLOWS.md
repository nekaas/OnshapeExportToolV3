# User Workflows — Onshape Export Manager

> **Date**: 2026-07-08  
> **Status**: Workflow documentation for all user personas  
> **Note**: Workflows described here reflect the **redesigned** application (post-UI Redesign Plan). Current-state workflows differ.

---

## Personas

| Persona | Description | Primary Goals |
|---|---|---|
| **Lab Technician** | Runs a makerspace or 3D printing lab | Export STLs daily, monitor printer-ready files |
| **Engineering Manager** | Oversees a team using Onshape | Keep STEP exports current, manage multiple API keys |
| **Teacher / Educator** | Uses Onshape in a classroom | Batch export student projects, archive semesters |
| **IT Administrator** | Manages the Raspberry Pi appliance | Maintain uptime, configure backups, manage remote access |
| **Hobbyist** | Solo user with a printer farm | Quick STL exports, run on a Pi, keep it simple |

---

## Workflow 1: First-Time Setup (All Personas)

**Goal**: Go from zero to first export in under 5 minutes.

### Step-by-Step

```
1. OPEN APPLICATION
   → Navigate to http://raspberrypi:8080 (or localhost:8080 in desktop mode)
   → See: Welcome screen with "Create Administrator Account"

2. CREATE ADMIN
   → Enter username and password (min 8 chars)
   → Click "Create account & continue"
   → Signed in automatically

3. LANDING ON HOME
   → See: 3-step guided onboarding
   → Card 1: "Add your Onshape API key" [Start]
   → Card 2: "Create your first label" [Start]
   → Card 3: "Run your first export" [Start]

4. ADD API KEY
   → Click [Start] on Card 1 → Modal opens
   → Enter: Key name ("My Onshape Key")
   → Enter: Access key (from Onshape Developer Portal)
   → Enter: Secret key
   → Click [Test Connection]
   → See: ✅ "Connected · 245ms"
   → Click [Save]
   → Modal closes. Card 1 shows ✅

5. CREATE LABEL
   → Click [Start] on Card 2 → Modal opens
   → Enter: Label name ("My First Label")
   → Enter: Onshape label ID (24-char ID from Onshape)
   → Choose formats: [✓] STL [✓] STEP
   → STL options: Binary, Fine, Millimeter
   → (Skip schedule for now)
   → Click [Create Label]
   → Modal closes. Card 2 shows ✅

6. FIRST EXPORT
   → Click [Start] on Card 3 → Navigates to Export page
   → Label pre-selected: "My First Label"
   → Date range: "All Time" (default)
   → Preview auto-loads: "~3 documents · ~2 min"
   → Click [Export Now]
   → Progress bar appears
   → ✅ "Export complete! 6 files saved"
   → [Open Folder] button appears

7. CELEBRATION
   → Home page now shows real stats
   → "You've exported 6 files across 3 documents"
   → "Set up a daily schedule?" hint appears
```

**Total clicks (from app open): ~12 clicks**
**Target time: 3-5 minutes**

---

## Workflow 2: Daily Export (Lab Technician)

**Frequency**: Daily  
**Goal**: Export all updated parts for today's prints.

### Path A: Quick Export (2 clicks)

```
1. HOME PAGE
   → "Quick Export" widget shows last used label+profile
   → Shows: 🏷 Robotics Team · ⚡ STL · 📅 Today
   → Click [Export Now]
   → Progress bar. Done.

Total: 2 clicks
```

### Path B: Scheduled (0 clicks)

```
1. SET UP ONCE:
   → Labels → Robotics Team → Schedule
   → Set: "Daily at 06:00"
   → Done.

2. EVERY DAY:
   → Exports run automatically at 6 AM
   → Notification (if configured): "Robotics Team exported: 8 files"
   → Check History if needed

Total: 0 clicks (after setup)
```

### Path C: Different Label (4 clicks)

```
1. EXPORT PAGE (⌘3)
   → Select label: "Student Projects"
   → Date: "Today"
   → Preview updates automatically
   → Click [Export Now]

Total: 4 clicks
```

---

## Workflow 3: Adding a New API Key (Engineering Manager)

**Goal**: Add a backup API key so exports don't fail when primary key hits rate limits.

```
1. NAVIGATE TO API KEYS (⌘2)
   → See: Card grid showing existing keys and their orgs

2. CLICK [+ Add Key]
   → Modal opens

3. ENTER KEY DETAILS
   → Name: "Backup Key"
   → Access key: (paste from Onshape)
   → Secret key: (paste from Onshape)
   → Organization: "Engineering Team" (existing org)
   → Click [Test Connection]
   → ✅ "Connected · 180ms"

4. ASSIGN TO LABELS
   → "Assign to existing labels?" prompt
   → [✓] Robotics Team
   → [✓] Production Parts
   → Click [Save & Assign]

5. VERIFY
   → API Keys page shows new key in "Engineering Team" card
   → Status: ✅ Healthy
   → Labels page shows "Backup Key" in Robotics Team's key list

Total clicks: ~8 clicks
```

---

## Workflow 4: Setting Up a Weekly Schedule (Teacher)

**Goal**: Auto-export student project files every Friday at 3 PM.

```
1. NAVIGATE TO LABELS (⌘3)
   → Find or create "Student Submissions" label

2. EDIT LABEL
   → Click [Edit] on the label card
   → Scroll to "Schedule" section

3. CONFIGURE SCHEDULE
   → Toggle: "Export automatically" → ON
   → Frequency: "Weekly"
   → Day: "Friday"
   → Time: "15:00"
   → Click [Save]

4. VERIFY
   → Label card now shows:
     "Schedule: Weekly on Friday at 15:00"
     "Next run: Friday, July 10, 2026 at 3:00 PM"

Total clicks: ~6 clicks
```

### What Happens on Friday at 3 PM:

```
1. SCHEDULER TRIGGERS
   → Worker picks up scheduled job
   → Claims least-used API key

2. EXPORT RUNS
   → Discovers documents with "Student Submissions" label
   → Exports each one as STL
   → Files saved to: exports/Student_Submissions/2026-07-10_150000/STL/

3. NOTIFICATION (if configured)
   → Discord: "✅ Student Submissions exported: 15 documents, 15 files"

4. HISTORY UPDATE
   → History page shows the export with timestamp
```

---

## Workflow 5: Recovering from a Failed Export

**Goal**: Understand why an export failed and fix it.

### Scenario A: Rate Limited

```
1. SEE THE FAILURE
   → Home page: "Failed" stat card shows "1" (red)
   → Click the card → jumps to History filtered to failed

2. INVESTIGATE
   → History shows: ❌ Robotics Team · Rate limited on Primary key
   → Message: "API rate limit reached. Resets in 12 minutes."
   → Auto-retry scheduled in 8 minutes

3. OPTIONS
   → [Retry Now with Backup Key] — switches to backup key immediately
   → [Wait] — let auto-retry handle it
   → [View API Keys] — check which keys are rate-limited

4. PREVENTION
   → API Keys page: add a second key for this label
   → Labels → Robotics Team → API Keys → Add Backup Key
```

### Scenario B: Invalid Label ID

```
1. SEE THE FAILURE
   → History: ❌ Archive · Label ID not found on Onshape

2. INVESTIGATE
   → Click label name → jumps to Labels page
   → Edit the label
   → Onshape label ID field shows warning: "ID does not match any document"

3. FIX
   → Get correct label ID from Onshape
   → Paste into field
   → Click [Save]
   → Click [Retry Export]

Total clicks to fix: ~6 clicks
```

---

## Workflow 6: Backup & Restore (IT Administrator)

**Goal**: Create a backup before making changes, restore if needed.

### Creating a Backup

```
1. SETTINGS (⌘,)
   → Tab: "Backups"

2. CREATE BACKUP
   → Click [Create Backup]
   → Options dialog:
     [✓] Include configuration
     [✓] Include database
     [ ] Include logs (optional, large)
   → Click [Create]

3. VERIFY
   → Backup list shows: "backup-2026-07-08_143000.zip · 1.2 MB"
   → Can download or leave on device

Total clicks: 4 clicks
```

### Restoring a Backup

```
1. SETTINGS → Backups

2. SELECT BACKUP
   → Click backup from list
   → Details: date, size, contents preview

3. RESTORE
   → Click [Restore]
   → ⚠️ Confirmation: "This will replace current configuration and database.
      A safety snapshot will be created first."
   → Click [Restore anyway]
   → Progress: "Restoring..."
   → ✅ "Restored successfully. Safety snapshot saved."

Total clicks: 5 clicks
```

---

## Workflow 7: Troubleshooting (IT Administrator)

**Goal**: Diagnose why exports aren't running.

### Checklist

```
1. CHECK WORKER STATUS
   → Home page stat card: "Worker: Running ✓" or "Stopped ✗"
   → If stopped: Settings → General → [✓] Auto-start worker → Save
     Or: click [Start Worker] on System card

2. CHECK API KEYS
   → API Keys page
   → Any keys showing ⚠ rate-limited or ❌ failed?
   → Test a key: click [Test] on any key card
   → If all keys failed: add a new key

3. CHECK QUEUE
   → Export page → "Active & Queued" section
   → Any jobs stuck in "Running" for >5 minutes?
   → [Cancel] and [Retry] stuck jobs

4. CHECK LOGS
   → Settings → Logs tab
   → Select "errors" log area
   → Look for ERROR or CRITICAL lines
   → Common issues:
     - "Connection refused" → Onshape API unreachable
     - "Rate limit" → Add more API keys
     - "Disk full" → Free up space or change export location

5. CHECK SYSTEM HEALTH
   → Settings → About tab
   → Disk usage > 90%? → Clean up old exports
   → Temperature > 80°C? → Check Raspberry Pi cooling
```

---

## Workflow 8: Managing Multiple Teams (Engineering Manager)

**Goal**: Keep exports organized across Engineering, Design, and Manufacturing teams.

### Setup

```
1. API KEYS
   → [+ Add Key] for each team's Onshape API key
   → Group by Organization:
     🏢 Engineering Team — 2 keys
     🏢 Design Team — 1 key
     🏢 Manufacturing — 1 key

2. LABELS
   → [+ New Label] for each team's export needs:
     🏷 Engineering Parts · STL+STEP · Daily
     🏷 Design Concepts · STL · Weekly
     🏷 Production Ready · STEP+DXF · On demand

3. SCHEDULES
   → Engineering Parts: Daily at 06:00
   → Design Concepts: Weekly on Monday
   → Production Ready: Manual only (triggered after review)

4. NOTIFICATIONS
   → Settings → Notifications
   → Discord channel: #exports
   → Filters: Export category, all severities
   → Each team sees export results in their channel
```

### Daily Usage

```
1. CHECK HOME
   → "3 labels exported today · 24 files · 0 failures"
   → All green

2. MANUAL EXPORT (if needed)
   → Export page → "Production Ready" → [Export Now]
   → Runs on demand after design review
```

---

## Workflow 9: End-of-Semester Archive (Teacher)

**Goal**: Export all student work before the semester ends, archive it.

```
1. CREATE ARCHIVE LABEL (one time)
   → Labels → [+ New Label]
   → Name: "Semester Archive"
   → Onshape ID: (label applied to all student documents)
   → Formats: [✓] STL [✓] STEP [✓] PDF
   → Schedule: None (manual)

2. END OF SEMESTER
   → Export page
   → Label: "Semester Archive"
   → Date: "All Time" (first export gets everything)
   → Click [Export Now]
   → Progress: "Exporting 142 documents..."

3. VERIFY
   → History: ✅ Semester Archive · 142 docs · 426 files
   → [Show Files] → opens: exports/Semester_Archive/2026-07-08_150000/

4. BACKUP
   → Settings → Backups → [Create Backup]
   → Include logs: [✓] (for archiving)
   → Download backup.zip for safekeeping
```

---

## Workflow 10: Remote Access Setup (IT Administrator)

**Goal**: Access the Export Manager from outside the local network.

### Option A: Tailscale (Recommended)

```
1. INSTALL TAILSCALE
   → SSH into Raspberry Pi
   → curl -fsSL https://tailscale.com/install.sh | sh
   → sudo tailscale up

2. VERIFY IN APP
   → Settings → Remote Access tab
   → Tailscale: ✅ Connected · 100.x.y.z
   → URLs shown: http://[tailscale-ip]:8080

3. ACCESS REMOTELY
   → Install Tailscale on your laptop/phone
   → Navigate to http://[raspberrypi-tailscale-name]:8080
   → Sign in as usual
```

### Option B: Cloudflare Tunnel

```
1. INSTALL CLOUDFLARED
   → SSH into Pi
   → Follow deploy/reverse-proxy.md guide

2. VERIFY
   → Settings → Remote Access
   → Cloudflare Tunnel: ✅ Connected

3. ACCESS
   → https://exports.yourdomain.com
```

---

## Keyboard Shortcuts Reference

| Shortcut | Action |
|---|---|
| `⌘K` | Command palette (search everything) |
| `⌘B` | Toggle sidebar |
| `⌘1` | Go to Home |
| `⌘2` | Go to API Keys |
| `⌘3` | Go to Labels |
| `⌘4` | Go to Export |
| `⌘5` | Go to History |
| `⌘,` | Open Settings |
| `⌘N` | New item (context-dependent) |
| `⌘Enter` | Submit form / Run export |
| `⌘F` | Focus search on current page |
| `Escape` | Close modal / palette / deselect |
| `?` | Show all shortcuts |
| `Space` | Toggle checkbox selection |
| `↑↓` | Navigate list items |

---

*End of User Workflows.*
