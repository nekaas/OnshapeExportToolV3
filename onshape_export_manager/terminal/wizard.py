"""Interactive first-run setup wizard for the terminal appliance.

Guides a new user through owner creation, API account setup, storage
configuration, and label creation — all via Rich-styled prompts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.prompt import Confirm, Prompt
from rich.text import Text

from .banner import print_banner
from .console import console
from .theme import heading, muted, success
from .widgets import appliance_panel, info_panel, section_divider


def run_wizard(app: object | None = None) -> bool:
    """Run the interactive first-run setup wizard.

    Returns True if setup completed successfully.
    """
    print_banner(mode="Setup Wizard")
    console.print("")
    console.print(
        appliance_panel(
            "Welcome to Onshape Export Manager!\n\n"
            "This wizard will guide you through the initial setup.\n"
            "You can re-run it anytime with the [bold]wizard[/bold] command.",
            title="First-Run Setup",
        )
    )
    console.print("")

    steps: list[tuple[str, Any]] = [
        ("Create owner account", lambda: _step_owner(app)),
        ("Add Onshape API account", lambda: _step_api_account(app)),
        ("Configure storage location", lambda: _step_storage(app)),
        ("Create your first label", lambda: _step_label(app)),
        ("Complete setup", lambda: _step_complete(app)),
    ]

    for i, (label, fn) in enumerate(steps, 1):
        console.print(section_divider(f"Step {i}/{len(steps)}: {label}"))
        try:
            ok = fn()
            if not ok:
                console.print("[yellow]Step skipped.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled.[/yellow]")
            return False

    console.print("")
    console.print(appliance_panel(
        "Setup complete! Your appliance is ready.\n\n"
        "Start the worker with: [bold]onshape-export-manager worker[/bold]\n"
        "Or launch the dashboard: [bold]onshape-export-manager dashboard[/bold]",
        title="Setup Complete",
    ))
    return True


# -- Steps -------------------------------------------------------------------


def _step_owner(app: object | None = None) -> bool:
    """Create the appliance owner account."""
    if app is None:
        console.print("[yellow]Application not available — skipping.[/yellow]")
        return False
    auth = getattr(app, "auth_service", None) or _get_auth(app)
    if auth is None:
        console.print("[yellow]Auth service not available — skipping.[/yellow]")
        return False
    if auth.is_configured():
        console.print(success("Owner account already exists."))
        return True

    console.print("Create an owner account to secure your appliance.")
    username = Prompt.ask("  Username", default="admin")
    while True:
        password = Prompt.ask("  Password", password=True)
        if len(password) < 8:
            console.print("[red]Password must be at least 8 characters.[/red]")
            continue
        confirm = Prompt.ask("  Confirm password", password=True)
        if password != confirm:
            console.print("[red]Passwords do not match.[/red]")
            continue
        break

    try:
        auth.create_owner(username.strip(), password)
        # Create a session so the current terminal session is authenticated
        token = auth.create_session(remember=True)
        console.print(success(f"Owner '{username}' created."))
        return True
    except Exception as exc:
        console.print(f"[red]Failed to create owner: {exc}[/red]")
        return False


def _step_api_account(app: object | None = None) -> bool:
    """Add an Onshape API account."""
    if app is None:
        return False
    console.print("Add your Onshape API access key pair.")
    console.print(muted("Find these at https://dev-portal.onshape.com/keys"))

    name = Prompt.ask("  Account name", default="Primary")
    access_key = Prompt.ask("  Access key")
    secret_key = Prompt.ask("  Secret key", password=True)

    if not access_key or not secret_key:
        console.print("[yellow]Skipped — no keys provided.[/yellow]")
        return False

    try:
        cm = getattr(app, "config_manager", None)
        if cm is None:
            console.print("[yellow]Config manager not available.[/yellow]")
            return False
        import json
        from onshape_export_manager.core.configuration import read_json, write_json, AccountsConfig

        data = read_json(cm.accounts_file)
        accounts = data.get("accounts", [])
        accounts.append({
            "name": name.strip(),
            "access_key": access_key.strip(),
            "secret_key": secret_key.strip(),
            "description": "",
        })
        AccountsConfig.model_validate({"accounts": accounts})
        write_json(cm.accounts_file, {"accounts": accounts})
        console.print(success(f"Account '{name}' added."))
        return True
    except Exception as exc:
        console.print(f"[red]Failed to add account: {exc}[/red]")
        return False


def _step_storage(app: object | None = None) -> bool:
    """Configure the export storage location."""
    if app is None:
        return False
    paths = getattr(app, "paths", None)
    current = str(getattr(paths, "exports_dir", "/mnt/usb/exports")) if paths else "/mnt/usb/exports"
    console.print(f"Current export location: [dim]{current}[/dim]")
    console.print(muted("On a Raspberry Pi, use /mnt/usb/exports for a USB drive."))

    if Confirm.ask("  Change storage location?", default=False):
        new_path = Prompt.ask("  New path", default=current)
        p = Path(new_path).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            console.print(success(f"Storage location set to: {p}"))
            return True
        except OSError as exc:
            console.print(f"[red]Cannot create directory: {exc}[/red]")
            return False
    return True


def _step_label(app: object | None = None) -> bool:
    """Create the first Onshape label mapping."""
    if app is None:
        return False
    if not Confirm.ask("  Create a label now?", default=True):
        console.print("[yellow]Skipped. You can create labels later.[/yellow]")
        return False

    console.print("A label maps an Onshape document tag to an export configuration.")
    name = Prompt.ask("  Label name", default="Ready for Export")
    label_id = Prompt.ask("  Onshape label ID (24-char hex)")

    if not label_id or len(label_id.strip()) < 10:
        console.print("[yellow]Invalid label ID — skipping.[/yellow]")
        return False

    try:
        cm = getattr(app, "config_manager", None)
        if cm is None:
            return False
        from onshape_export_manager.core.configuration import read_json, write_json, LabelsConfig

        data = read_json(cm.labels_file)
        labels = data.get("labels", [])
        labels.append({
            "friendly_name": name.strip(),
            "onshape_label_id": label_id.strip(),
            "assigned_accounts": [],
            "export_location": "exports",
            "export_profile": "STL",
            "scheduler": None,
            "enabled": True,
        })
        LabelsConfig.model_validate({"labels": labels})
        write_json(cm.labels_file, {"labels": labels})
        console.print(success(f"Label '{name}' created."))
        return True
    except Exception as exc:
        console.print(f"[red]Failed to create label: {exc}[/red]")
        return False


def _step_complete(app: object | None = None) -> bool:
    """Mark setup as complete."""
    if app is None:
        return False
    db = getattr(app, "database", None)
    if db is not None:
        db.set_state("setup.completed", "true")
    console.print(success("Setup marked complete."))
    return True


def _get_auth(app: object) -> object | None:
    """Get or create the auth service from the application."""
    try:
        from onshape_export_manager.core.auth import AuthService
        db = getattr(app, "database", None)
        if db is not None:
            return AuthService(db)
    except Exception:
        pass
    return None
