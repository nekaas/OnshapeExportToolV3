# Domain Model

## Entity Relationship Diagram

```
Organization (1) ──< (N) Credential
     │
     │ (imported from)
     ▼
OnshapeAccount ──< (N) Group (Label)
     │                    │
     │                    │ (references)
     │                    ▼
     │              ExportProfile
     │                    │
     │                    │ (produces)
     ▼                    ▼
  ExportJob ──────> ExportHistoryEntry
```

## Core Entities

### OnshapeAccount
**What it is:** An API credential for one Onshape instance.
**Identity:** `name` (unique string)
**Attributes:**
- `access_key` — Onshape API access key (or `env:VAR` reference)
- `secret_key` — Onshape API secret key (or `env:VAR` reference)
- `description` — human-readable note
- `enabled` — whether this account is active
- `health` — runtime status: `healthy`, `degraded`, `rate_limited`, `failed`, `disabled`
- `api_usage` — today's API call count
- `failure_count` — consecutive failure counter
- `last_used` — timestamp of last API call

**Lifecycle:** Created via UI (API Keys page). Tested for connectivity. Disabled when failing repeatedly. Never automatically deleted.

**Storage:** `config/accounts.json` (flat) or `config/organizations.json` (hierarchical)

---

### Organization
**What it is:** A logical grouping of Onshape credentials, typically one Onshape enterprise/team.
**Identity:** `id` (auto-generated)
**Attributes:**
- `name` — e.g., "Engineering Team", "Acme Corp"
- `type` — `school`, `company`, `department`, `customer`, `workshop`, `team`, `other`
- `description` — optional note
- `enabled` — whether this org's credentials are active
- `priority` — credential selection priority (1-999)

**Relationships:** Has many Credentials. Groups are NOT directly linked to Organizations.

**Storage:** `config/organizations.json`

---

### Credential
**What it is:** One API key pair within an Organization.
**Identity:** `id` within parent Organization
**Attributes:**
- `name` — e.g., "Primary", "Secondary"
- `access_key`, `secret_key` — Onshape API credentials
- `environment` — `production` or `development`
- `enabled`, `priority` — selection controls

**Lifecycle:** Created under an Organization. Tested individually. Deleted when rotated.

---

### Group (aka Label)
**What it is:** The central connecting entity. Maps an Onshape document label to export settings and accounts.

**Identity:** `friendly_name` (unique string)

**Attributes:**
- `friendly_name` — human-readable name (e.g., "Robotics Team Parts")
- `onshape_label_id` — 24-character hex ID from Onshape
- `assigned_accounts` — list of OnshapeAccount names to use
- `export_profile` — name of the ExportProfile to apply
- `export_location` — output subdirectory (default: `exports`)
- `scheduler` — optional recurring interval string (`15min`, `30min`, `hourly`, `daily`, `weekly`, `monthly`)
- `enabled` — whether this Group is active

**Rules:**
- A Group must reference at least one existing OnshapeAccount
- A Group must reference an existing ExportProfile
- `onshape_label_id` must be exactly 24 characters
- `friendly_name` must be unique across all Groups
- A Group can be assigned to multiple accounts for redundancy
- Deleting a Group does NOT delete its export history

**Storage:** `config/labels.json`

---

### ExportProfile
**What it is:** A named export configuration defining format(s) and options.

**Identity:** `name` (unique string)

**Attributes:**
- `name` — e.g., "STL", "STEP", "Multi Format"
- `formats` — list of `ExportFormat` enum values
- `options` — per-format settings (units, resolution, etc.)
- `bambu` — optional Bambu Studio integration settings

**ExportFormat enum values:**
`STL`, `STEP`, `PARASOLID`, `OBJ`, `IGES`, `DXF`, `PDF`, `CUSTOM`

**Lifecycle:** Created via API Keys or Settings UI. Referenced by Groups. Deleting a profile that's in use is blocked.

**Storage:** `config/export_profiles.json`

---

### ExportJob (Queue Entry)
**What it is:** A single export request in the processing queue.

**Identity:** `id` (UUID4)

**Attributes:**
- `label_name` — which Group to export
- `profile_name` — which profile to use (may override Group default)
- `payload` — JSON with date range, destination, chaining info
- `status` — `pending`, `running`, `completed`, `failed`, `cancelled`
- `retry_count` — number of retry attempts
- `next_run_at` — when to retry (null if not retrying)
- `last_error` — error message from last failure
- `created_at`, `started_at`, `completed_at`

**State machine:**
```
pending → running → completed
pending → running → failed → pending (retry, ≤3 attempts)
pending → cancelled
failed → permanent failure (retry_count > 3)
```

**Storage:** `export_queue` table in SQLite

---

### ExportHistoryEntry
**What it is:** A completed or permanently failed export record.

**Identity:** `id` (auto-increment)

**Attributes:**
- `account_name` — which OnshapeAccount was used
- `label_name` — which Group
- `export_profile` — which profile
- `exported_files` — JSON list of output file paths
- `duration_seconds` — total processing time
- `success` — boolean
- `failures` — JSON list of per-file failures
- `retry_count`
- `started_at`, `completed_at`

**Storage:** `export_history` table in SQLite. Never pruned automatically.

---

### SchedulerJob
**What it is:** A recurring trigger that creates ExportJobs on a schedule.

**Attributes:**
- `label_name` — which Group to export
- `interval` — frequency string
- `enabled` — whether currently active
- `next_run_at` — next scheduled trigger time
- `last_run_at` — last time it fired

**Lifecycle:** Created/updated when a Group with a schedule is saved. Deleted when schedule is removed.

**Storage:** `scheduler_jobs` table in SQLite

---

### Event
**What it is:** An auditable action in the system.

**Attributes:**
- `type` — `EventType` enum (AUTH_LOGIN, JOB_ENQUEUED, JOB_COMPLETED, etc.)
- `severity` — `info`, `success`, `warning`, `error`, `critical`
- `message` — human-readable description
- `data` — optional JSON payload
- `actor` — who triggered it
- `timestamp`

**Storage:** In-memory ring buffer (recent) + `events` table (persisted)

---

## Configuration Top-Level Model

```python
AppConfig:
  accounts: AccountsConfig        # list of OnshapeAccount
  labels: LabelsConfig            # list of LabelConfig (Groups)
  export_profiles: ExportProfilesConfig
  worker_count: int = 4
  worker_autostart: bool = True
  worker_poll_seconds: float = 5.0
  request_timeout_seconds: int = 30
  export_timeout_seconds: int = 120
  retry: RetrySettingsConfig
  folders: FolderSettingsConfig
  scheduler: SchedulerSettingsConfig
  logging: LoggingSettingsConfig
  ui: UiSettingsConfig
  server: ServerSettingsConfig
  notifications: list[NotificationChannelConfig]
```
