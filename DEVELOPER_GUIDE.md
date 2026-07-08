# Developer Guide

## Setup

```bash
git clone <repo>
cd OnshapeExportTool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
onshape_export_manager/
├── app.py                  # Entry point (argparse, banner)
├── web.py                  # FastAPI app, 55+ API routes
├── cli.py                  # Terminal commands
├── core/                   # Business logic (30+ modules)
│   ├── app.py              # Application container
│   ├── configuration.py    # Config models + manager
│   ├── database.py         # SQLite layer
│   ├── worker.py           # Background workers
│   ├── export_engine.py    # Export orchestration
│   ├── ...                 # See SYSTEM_ARCHITECTURE.md
├── config/                 # JSON config files
├── ui/                     # Web UI
│   ├── templates/          # Jinja2 templates
│   └── static/             # app.js, styles.css
├── terminal/               # CLI/TUI
├── tests/                  # 183 tests
└── deploy/                 # systemd, reverse proxy, install scripts
```

## Development Workflow

1. **Read the docs** — Start with README.md and DOMAIN_MODEL.md
2. **Run the app** — `python app.py --mode desktop`
3. **Make changes** — Follow the implementation order in the development contract
4. **Run tests** — `python -m pytest tests/ -q`
5. **Audit** — Navigate every page, click every button
6. **Update docs** — If implementation changed, update affected docs
7. **Commit** — Descriptive conventional commits

## Running the App

```bash
# Desktop mode (localhost, auto-open browser)
python app.py --mode desktop

# Server mode (0.0.0.0, headless)
python app.py --mode server --port 8080

# With custom host/port
python app.py --mode server --host 0.0.0.0 --port 9000

# Environment variables
OEM_MODE=server OEM_PORT=8080 python app.py
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -q

# Specific test file
python -m pytest tests/test_web_api.py -q

# With verbose output
python -m pytest tests/ -v

# Single test
python -m pytest tests/test_web_api.py::test_tree_endpoint -v
```

## Code Conventions

### Python
- Type hints on all function signatures
- Dataclasses for data objects (slots=True where possible)
- Pydantic for API models (`extra="forbid"`)
- Thread safety: use `threading.Lock` for shared mutable state
- Logging: `logger = logging.getLogger(__name__)` with structured messages

### JavaScript
- Alpine.js 3.x for reactivity
- `x-data` for component scope
- `x-if` on `<template>` tags only (not `<div>`)
- Use optional chaining (`?.`) for nullable data
- Toast notifications: `window.oem.toast(title, message, kind)`

### CSS
- Custom properties on `:root` for theming
- `.glass` class for card backgrounds
- `.btn`, `.badge`, `.card`, `.field` component classes
- Dark-first with light theme via class toggle

## Adding a New Feature

1. **Data model** — Add to `core/models.py` and/or `core/configuration.py`
2. **Database** — Add table to `core/database.py` if needed
3. **API** — Add endpoint to `web.py` with Pydantic request model in `core/validation.py`
4. **UI** — Add template section in `ui/templates/section.html`, Alpine.js data in `app.js`
5. **Navigation** — Add to `NAV_ITEMS` in `web.py`
6. **Tests** — Add test file in `tests/`
7. **Docs** — Update README.md, FEATURE_INVENTORY.md, and relevant docs

## Adding an Export Format

1. Add value to `ExportFormat` enum in `core/models.py`
2. Implement translator in `core/export_formats.py`
3. Register in `ExportEngine._export_single_format()`
4. Add format options to `core/validation.py` if needed
5. Add to format list in `GET /api/formats`

## Config File Format

All config files are JSON with Pydantic validation. Add new fields by:
1. Adding to the Pydantic model in `core/configuration.py`
2. Providing a sensible default
3. Updating `ConfigManager.ensure_default_files()` if creating a new file

## Common Pitfalls

- **Don't use `x-if` on `<div>`** — Alpine warns and may not work. Use `<template x-if>`.
- **Don't assume `x-show` prevents evaluation** — Alpine evaluates child expressions during init. Use `x-if` or optional chaining.
- **Thread safety** — The worker pool shares state. Always use locks.
- **Config caching** — Workers cache config for 5s. Call `invalidate_cache()` after changes.
- **Path parameters** — FastAPI decodes `%2F` as `/` in path params. Use query params for values with special characters.
