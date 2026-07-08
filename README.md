<div align="center">

# Onshape Export Manager

**Your Onshape parts, exported automatically. Set it up once. It runs forever.**

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Tests](https://img.shields.io/badge/tests-165%20passing-brightgreen.svg)]()

</div>

---

## What Is This?

The Onshape Export Manager is a **self-hosted desktop appliance** that automates CAD file exports from [Onshape](https://www.onshape.com/). Tag your documents in Onshape, set up the app once, and your STL, STEP, OBJ, and other CAD files are exported automatically — on a schedule or on demand.

It runs on a **Raspberry Pi** (or any Linux/macOS machine) and provides a polished, browser-based dashboard for management. Think of it like a network printer for your CAD files.

### Who Is This For?

- **3D printing labs & makerspaces** — Keep STLs current for Bambu Studio, PrusaSlicer, or Cura
- **Engineering teams** — Auto-export STEP/Parasolid for downstream CAD/CAM workflows
- **Educators** — Batch export and archive student project portfolios
- **Manufacturing shops** — Nightly production part exports for toolpath generation
- **Hobbyists** — Set-and-forget STL exports on a $35 Raspberry Pi

---

## Quick Start

```bash
git clone https://github.com/your-org/onshape-export-manager.git
cd onshape-export-manager
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                          # desktop mode — opens browser
python app.py --mode server --host 0.0.0.0 --port 8080   # server mode
```

Open `http://localhost:8080` → Create admin account → Add API key → Create label → Export!

Files land in `./exports/{Label}/{date}/{FORMAT}/`.

---

## Core Features

- **Multi-format export**: STL (binary/ASCII), STEP, OBJ, IGES, Parasolid, DXF, PDF
- **Multi-account pool**: Load-balance across API keys with automatic rate-limit failover
- **Scheduled exports**: Set daily/weekly/monthly schedules per label
- **Managed queue**: Every export with retry, exponential backoff, and cancel/retry controls
- **Real-time dashboard**: Live charts, account health, export activity, SSE streaming
- **Notifications**: Discord, Slack, Teams, Email, and webhook alerts
- **Backup & Restore**: ZIP-based config/database backups with safety snapshots
- **CLI & API**: Full command-line interface and 50+ REST endpoints

---

## Documentation

| Document | Purpose |
|---|---|
| [README.md](README.md) | Project overview and quick start |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Complete subsystem guide for developers |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Architecture reference — data models, API, threading |
| [UX_AUDIT.md](UX_AUDIT.md) | 55 usability issues, ranked by severity |
| [UI_GUIDELINES.md](UI_GUIDELINES.md) | Design system — typography, colors, components, a11y |
| [USER_WORKFLOWS.md](USER_WORKFLOWS.md) | Every user workflow documented |
| [MASTER_UI_REDESIGN_PLAN.md](MASTER_UI_REDESIGN_PLAN.md) | 10-phase UX redesign roadmap |
| [MASTER_IMPROVEMENT_PLAN.md](MASTER_IMPROVEMENT_PLAN.md) | 58-item technical improvement backlog |
| [PROJECT_AUDIT.md](PROJECT_AUDIT.md) | Honest engineering review of the codebase |
| [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) | 31 architectural shortcuts and code smells |
| [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) | Feature roadmap |
| [SECURITY.md](SECURITY.md) | Security architecture |
| [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) | Feature audit against core mission |

---

## Architecture

```
Browser (Alpine.js + Chart.js + Tailwind)
        │ HTTP / SSE / WebSocket
FastAPI (50+ endpoints + Jinja2 templates)
        │
Core Services (Queue · Scheduler · ExportEngine · ApiPool · Notifications · Audit)
        │
BackgroundWorker (daemon thread, asyncio loop, 5s tick)
        │
SQLite (WAL mode — history, queue, scheduler, events, telemetry)
```

For full details: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

---

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q                          # 165 tests
python -m pytest tests/ --cov=onshape_export_manager --cov-report=html
```

### Project Structure

```
onshape_export_manager/
├── app.py              # Application container (service wiring)
├── cli.py              # CLI (argparse)
├── web.py              # FastAPI (routes, auth, SSE, WS)
├── core/               # 28 service modules (100-300 lines each)
├── ui/static/          # app.js + styles.css
├── ui/templates/       # Jinja2 templates
├── config/             # JSON config files
├── tests/              # pytest (24 test files)
└── deploy/             # systemd, install scripts, reverse proxy guide
```

---

## Deployment

### Raspberry Pi (systemd)
```bash
sudo bash deploy/install.sh
bash deploy/manage.sh start|stop|status|logs
```

### Docker
```bash
docker build -t onshape-export-manager .
docker run -p 8080:8080 -v ./exports:/app/exports -v ./config:/app/config onshape-export-manager
```

### Remote Access
Works with Tailscale, Cloudflare Tunnel, Nginx, Caddy. See [deploy/reverse-proxy.md](deploy/reverse-proxy.md).

---

## License

MIT License — see [LICENSE](LICENSE).

*Built for makers, engineers, and educators who want their CAD files where they need them, when they need them.*
