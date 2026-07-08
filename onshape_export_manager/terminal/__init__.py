"""Terminal UI subsystem for the Onshape Export Manager appliance.

Provides a polished, commercial-appliance-grade terminal experience
powered by Rich and Textual. All terminal rendering lives here —
never scatter ``print()`` calls throughout the codebase.

Architecture::

    console.py   → shared Rich Console singleton + mode flags
    theme.py     → colors, styles, Unicode constants
    widgets.py   → reusable Rich renderables (panels, dividers, spinners)
    tables.py    → Rich table helpers
    banner.py    → ASCII art logo and version splash
    boot.py      → staged startup checklist
    wizard.py    → Textual first-run setup wizard
    dashboard.py → live auto-refreshing system status display
    commands.py  → interactive REPL + one-shot CLI dispatcher
    health.py    → health report rendering
    network.py   → network discovery display
    progress.py  → export progress bars and ETA
    metrics.py   → live CPU/RAM/disk/temp
    errors.py    → rich error screens (no tracebacks)
    qr.py        → terminal QR code generation
"""

from __future__ import annotations
