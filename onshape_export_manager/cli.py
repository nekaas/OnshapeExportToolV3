"""Command-line entrypoint for Onshape Export Manager."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError

from onshape_export_manager import __version__
from onshape_export_manager.app import create_app
from onshape_export_manager.core.api_pool import ApiPoolError
from onshape_export_manager.core.configuration import ConfigError
from onshape_export_manager.core.export_formats import list_format_definitions
from onshape_export_manager.core.models import ExportJobRequest
from onshape_export_manager.core.profile_manager import (
    ExportProfileManager,
    ExportProfileManagerError,
    parse_format_list,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="onshape-export-manager",
        description="Manage Onshape exports across accounts, labels, and profiles.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create the application directory structure and exit.",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create missing JSON configuration files and exit.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate JSON configuration files and exit.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize or migrate the SQLite database and exit.",
    )
    parser.add_argument(
        "--database-status",
        action="store_true",
        help="Show SQLite schema version and table counts.",
    )
    parser.add_argument(
        "--accounts-status",
        action="store_true",
        help="Show configured Onshape account runtime status.",
    )
    parser.add_argument(
        "--queue-status",
        action="store_true",
        help="Show export queue counts by state.",
    )
    parser.add_argument(
        "--scheduler-status",
        action="store_true",
        help="Show scheduler job count and running state.",
    )
    parser.add_argument(
        "--list-export-formats",
        action="store_true",
        help="Show supported Onshape Part Studio export formats.",
    )
    parser.add_argument(
        "--list-export-profiles",
        action="store_true",
        help="Show configured export profiles.",
    )
    parser.add_argument(
        "--run-export",
        metavar="LABEL",
        help="Run a manual export for a configured label friendly name.",
    )
    parser.add_argument(
        "--add-export-profile",
        metavar="PROFILE",
        help="Create a new export profile using --formats.",
    )
    parser.add_argument(
        "--formats",
        metavar="LIST",
        help="Comma or space separated formats for --add-export-profile.",
    )
    parser.add_argument(
        "--replace-profile",
        action="store_true",
        help="Allow --add-export-profile to replace an existing profile.",
    )
    parser.add_argument(
        "--bambu-profile",
        action="store_true",
        help="Enable Bambu post-processing settings on --add-export-profile.",
    )
    parser.add_argument(
        "--profile",
        metavar="PROFILE",
        help="Override the label's configured export profile for --run-export.",
    )
    parser.add_argument(
        "--start",
        metavar="ISO_DATETIME",
        help="Start of the modified-date window for --run-export.",
    )
    parser.add_argument(
        "--end",
        metavar="ISO_DATETIME",
        help="End of the modified-date window for --run-export.",
    )
    parser.add_argument(
        "--destination",
        metavar="PATH",
        help="Override the label export folder for --run-export.",
    )
    parser.add_argument(
        "--run-worker",
        action="store_true",
        help="Run the background export worker (drains the queue, advances the scheduler) until interrupted.",
    )
    parser.add_argument(
        "--drain-once",
        action="store_true",
        help="Run a single worker tick (advance scheduler + drain due jobs) and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    app = create_app()
    if args.init or args.init_config:
        app.config_manager.ensure_default_files()
        print(f"Initialized Onshape Export Manager at {app.paths.package_dir}")
    elif args.init_db:
        app.database.initialize()
        print(f"Initialized database at {app.database.path}")
    elif args.database_status:
        status = app.database.status()
        print(f"Database: {app.database.path}")
        print(f"Schema version: {status['schema_version']}")
        print(f"Export history rows: {status['export_history']}")
        print(f"Queue rows: {status['export_queue']}")
        print(f"Scheduler job rows: {status['scheduler_jobs']}")
        print(f"State rows: {status['application_state']}")
    elif args.accounts_status:
        pool = app.create_api_pool()
        states = pool.snapshot()
        if not states:
            print("No Onshape accounts configured.")
        for state in states:
            last_used = state.last_used.isoformat() if state.last_used else "-"
            limited_until = (
                state.rate_limited_until.isoformat()
                if state.rate_limited_until
                else "-"
            )
            print(
                f"{state.name}: status={state.rate_limit_status} "
                f"usage={state.api_usage} failures={state.failure_count} "
                f"last_used={last_used} rate_limited_until={limited_until}"
            )
    elif args.queue_status:
        manager = app.create_queue_manager()
        stats = manager.stats()
        print(f"Queue total: {stats.total}")
        print(f"Pending: {stats.pending}")
        print(f"Running: {stats.running}")
        print(f"Completed: {stats.completed}")
        print(f"Failed: {stats.failed}")
        print(f"Cancelled: {stats.cancelled}")
    elif args.scheduler_status:
        running = app.database.get_state("scheduler.running", "false")
        jobs = app.database.list_scheduler_jobs()
        enabled = [job for job in jobs if job.enabled]
        print(f"Scheduler running: {running}")
        print(f"Scheduler jobs: {len(jobs)}")
        print(f"Enabled jobs: {len(enabled)}")
    elif args.list_export_formats:
        for item in list_format_definitions(part_studio_only=True):
            print(f"{item.format.value}: {item.display_name} ({item.default_extension})")
    elif args.list_export_profiles:
        try:
            config = app.config_manager.load()
        except (ConfigError, ValidationError) as exc:
            print(f"Configuration invalid: {exc}")
            return 1
        for profile in config.export_profiles.profiles:
            formats = ", ".join(item.value for item in profile.formats)
            status = "enabled" if profile.enabled else "disabled"
            bambu = "bambu" if profile.bambu.enabled else "onshape"
            print(f"{profile.name}: {formats} [{status}, {bambu}]")
    elif args.run_export:
        try:
            result = asyncio.run(run_export_from_args(app, args))
        except (ApiPoolError, ConfigError, RuntimeError, ValidationError, ValueError) as exc:
            print(f"Export could not start: {exc}")
            return 1
        print(f"Export success: {result.success}")
        print(f"Documents seen: {result.documents_seen}")
        print(f"Files exported: {len(result.exported_files)}")
        if result.export_folder:
            print(f"Export folder: {result.export_folder}")
        for path in result.exported_files:
            print(f"  {path}")
        for item in result.skipped_items:
            print(f"Skipped: {item}")
        for item in result.failed_items:
            print(f"Failed: {item}")
        return 0 if result.success else 2
    elif args.add_export_profile:
        if not args.formats:
            print("--add-export-profile requires --formats")
            return 1
        try:
            manager = ExportProfileManager(app.config_manager)
            profile = manager.add_profile(
                args.add_export_profile,
                parse_format_list(args.formats),
                replace=args.replace_profile,
                bambu_enabled=args.bambu_profile,
                open_bambu_studio=args.bambu_profile,
            )
        except (ConfigError, ValidationError, ExportProfileManagerError) as exc:
            print(f"Export profile could not be saved: {exc}")
            return 1
        print(
            "Saved export profile "
            f"{profile['name']}: {', '.join(profile['formats'])}"
        )
    elif args.validate_config:
        try:
            config = app.config_manager.load()
        except (ConfigError, ValidationError) as exc:
            print(f"Configuration invalid: {exc}")
            return 1
        print(
            "Configuration valid: "
            f"{len(config.accounts.accounts)} account(s), "
            f"{len(config.labels.labels)} label(s), "
            f"{len(config.export_profiles.profiles)} export profile(s)."
        )
    elif args.drain_once:
        from onshape_export_manager.core.worker import BackgroundWorker

        worker = BackgroundWorker(app)
        if app.scheduler is not None:
            worker._sync_scheduler_jobs()
            app.scheduler.start()
        result = worker.run_once()
        print(
            "Worker tick complete: "
            f"scheduled={result.scheduled_enqueued} run={result.jobs_run} "
            f"succeeded={result.jobs_succeeded} failed={result.jobs_failed}"
        )
        for error in result.errors:
            print(f"  error: {error}")
        return 0 if not result.jobs_failed else 2
    elif args.run_worker:
        import time

        from onshape_export_manager.core.worker import BackgroundWorker

        worker = BackgroundWorker(app)
        worker.start()
        print("Background worker running. Press Ctrl+C to stop.")
        try:
            while worker.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping worker…")
        finally:
            worker.stop()
        return 0
    else:
        print("Onshape Export Manager CLI is ready.")
    return 0


async def run_export_from_args(app, args: argparse.Namespace):
    """Build and execute a manual export request from CLI arguments."""
    config = app.config_manager.load()
    labels = {
        label.friendly_name: label
        for label in config.runtime_labels(app.paths.package_dir)
        if label.enabled
    }
    label = labels.get(args.run_export)
    if label is None:
        available = ", ".join(sorted(labels)) or "none"
        raise ValueError(f"unknown or disabled label '{args.run_export}'. Available labels: {available}")

    profiles = {
        profile.name: profile
        for profile in config.runtime_export_profiles()
        if profile.enabled
    }
    profile_name = args.profile or label.export_profile
    profile = profiles.get(profile_name)
    if profile is None:
        available = ", ".join(sorted(profiles)) or "none"
        raise ValueError(f"unknown or disabled export profile '{profile_name}'. Available profiles: {available}")

    start_iso, end_iso = export_window(args.start, args.end)
    destination = Path(args.destination).expanduser() if args.destination else None
    engine = app.create_export_engine(resolve_env=True)
    return await engine.run_manual_export(
        ExportJobRequest(
            label=label,
            profile=profile,
            start_iso=start_iso,
            end_iso=end_iso,
            destination=destination,
        )
    )


def export_window(start_value: str | None, end_value: str | None) -> tuple[str, str]:
    """Return ISO datetimes for a CLI export window."""
    end = parse_cli_datetime(end_value) if end_value else datetime.now(timezone.utc)
    start = parse_cli_datetime(start_value) if start_value else end - timedelta(days=1)
    if start > end:
        raise ValueError("--start must be before or equal to --end")
    return start.isoformat(), end.isoformat()


def parse_cli_datetime(value: str) -> datetime:
    """Parse an ISO datetime, accepting trailing Z for UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    raise SystemExit(main())
