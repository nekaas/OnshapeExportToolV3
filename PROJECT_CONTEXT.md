# Project Context

## Origin

Onshape Export Manager was built to solve a recurring problem in CAD-to-manufacturing workflows: Onshape documents need to be regularly exported to STL, STEP, or other formats for 3D printing, CNC machining, or sharing with external partners. Manual exports through the Onshape web UI are tedious and error-prone.

## Problem Statement

Engineering teams using Onshape CAD need:
1. **Automated exports** — documents tagged with specific labels exported on a schedule
2. **Multi-format output** — same document exported as STL for printing, STEP for machining
3. **Multi-account support** — teams with multiple Onshape accounts need credential management
4. **Reliability** — retry logic, failure tracking, health monitoring
5. **On-premise operation** — no cloud dependency; runs on local hardware or Raspberry Pi
6. **Simple operation** — a non-technical user should be able to configure and run exports

## Target Users

### Primary: CAD/Engineering Team Lead
- Configures API accounts, creates Groups, sets schedules
- Checks dashboard for failures, monitors health
- Runs manual exports when needed

### Secondary: Shop Floor / Manufacturing
- Opens the dashboard to verify exports completed
- Downloads export files for their machines

### Tertiary: IT/DevOps
- Deploys on Raspberry Pi or server
- Manages remote access, backups, SSL certificates
- Monitors system health

## Design Principles

1. **Local-first** — Everything runs on local hardware. No cloud dependency except the Onshape API itself.
2. **Config as JSON** — All configuration is human-readable JSON. Easy to version control, backup, and edit manually.
3. **Single-owner auth** — One admin account. No user management complexity.
4. **Glassmorphism dark UI** — Dark-first premium aesthetic. Charts for at-a-glance health.
5. **Convention over configuration** — Sensible defaults. Most users only need to set up accounts and labels.
6. **Progressive disclosure** — Dashboard shows overview. Click through for details. Settings for advanced configuration.

## Constraints

- **No external database** — SQLite only. No PostgreSQL, MySQL, or Redis required.
- **No cloud services** — No S3, no cloud functions, no managed queues.
- **Single binary requirement** — Everything in one Python process (web server + worker threads).
- **Raspberry Pi compatible** — Must run on ARM, minimal RAM, SD card storage.
- **Offline-capable** — Core export functionality works without internet (except reaching Onshape API).

## Success Criteria

1. A new user can go from `pip install` to first successful export in under 10 minutes
2. Scheduled exports run reliably for weeks without intervention
3. The dashboard clearly communicates system health at a glance
4. Failed exports are retried automatically and failures are surfaced prominently
5. The system can be managed entirely through the web UI (no CLI required after setup)
