"""JSON configuration loading, validation, and default file management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from onshape_export_manager.core.export_formats import default_options_for
from onshape_export_manager.core.models import (
    BambuSettings,
    ExportFormat,
    ExportProfile,
    LabelDefinition,
    OnshapeAccount,
)
from onshape_export_manager.core.settings import AppPaths


class ConfigError(RuntimeError):
    """Raised when application configuration cannot be loaded or validated."""


class StrictConfigModel(BaseModel):
    """Base model that rejects unknown JSON keys."""

    model_config = ConfigDict(extra="forbid")


class RetrySettingsConfig(StrictConfigModel):
    """Retry behavior for transient export and API failures."""

    max_attempts: int = Field(default=4, ge=1, le=20)
    backoff_base_seconds: float = Field(default=1.0, gt=0)
    backoff_max_seconds: float = Field(default=60.0, gt=0)
    retry_http_statuses: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )


class FolderSettingsConfig(StrictConfigModel):
    """Folder behavior for export output."""

    exports_dir: str = "exports"
    timestamp_format: str = "%Y-%m-%d_%H%M%S"
    never_overwrite: bool = True


class SchedulerSettingsConfig(StrictConfigModel):
    """Global scheduler settings."""

    enabled: bool = False
    timezone: str = "local"


class LoggingSettingsConfig(StrictConfigModel):
    """Application logging settings."""

    level: str = "INFO"
    retention_days: int = Field(default=30, ge=1)
    mask_secrets: bool = True

    @field_validator("level")
    @classmethod
    def normalize_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized


class UiSettingsConfig(StrictConfigModel):
    """Web and terminal UI settings."""

    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8000, ge=1, le=65535)
    theme: str = "system"


class ServerSettingsConfig(StrictConfigModel):
    """Operating mode and headless server settings."""

    mode: str = "desktop"
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    behind_proxy: bool = False
    auto_open_browser: bool = True

    @field_validator("mode")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"desktop", "server"}:
            raise ValueError("mode must be 'desktop' or 'server'")
        return normalized


class GlobalBambuSettingsConfig(StrictConfigModel):
    """Global Bambu Studio paths and defaults."""

    enabled: bool = False
    bambu_studio_exe: str = ""
    profile_root: str = ""
    machine_profile: str = ""
    process_profile: str = ""
    output_folder: str = ""


class NotificationChannelConfig(StrictConfigModel):
    """One configured notification channel (Discord, Slack, Teams, email, webhook).

    A channel is matched against published events by category and minimum
    severity; matching events are formatted and delivered to ``target``.
    """

    id: str = Field(min_length=1)
    name: str = Field(default="", max_length=120)
    kind: str = "webhook"
    enabled: bool = True
    target: str = ""  # webhook URL, or "host:port" / address for email
    min_severity: str = "info"
    categories: list[str] = Field(default_factory=list)  # empty = all categories
    options: dict[str, Any] = Field(default_factory=dict)  # kind-specific (smtp auth, etc.)

    @field_validator("kind")
    @classmethod
    def normalize_kind(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"discord", "slack", "teams", "email", "webhook"}
        if normalized not in allowed:
            raise ValueError(f"kind must be one of {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("min_severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"debug", "info", "success", "warning", "error", "critical"}
        if normalized not in allowed:
            raise ValueError(f"min_severity must be one of {', '.join(sorted(allowed))}")
        return normalized


class NotificationsSettingsConfig(StrictConfigModel):
    """Notification delivery settings: a list of channels plus a master switch."""

    enabled: bool = True
    channels: list[NotificationChannelConfig] = Field(default_factory=list)


class AppConfig(StrictConfigModel):
    """Global application configuration from config.json."""

    onshape_base_url: str = "https://cad.onshape.com/api/v6"
    worker_count: int = Field(default=4, ge=1, le=64)
    worker_autostart: bool = True
    worker_poll_seconds: float = Field(default=5.0, ge=0.5, le=3600.0)
    request_timeout_seconds: int = Field(default=30, ge=1)
    export_timeout_seconds: int = Field(default=120, ge=1)
    folders: FolderSettingsConfig = Field(default_factory=FolderSettingsConfig)
    retry: RetrySettingsConfig = Field(default_factory=RetrySettingsConfig)
    scheduler: SchedulerSettingsConfig = Field(default_factory=SchedulerSettingsConfig)
    logging: LoggingSettingsConfig = Field(default_factory=LoggingSettingsConfig)
    ui: UiSettingsConfig = Field(default_factory=UiSettingsConfig)
    server: ServerSettingsConfig = Field(default_factory=ServerSettingsConfig)
    bambu: GlobalBambuSettingsConfig = Field(default_factory=GlobalBambuSettingsConfig)
    notifications: NotificationsSettingsConfig = Field(default_factory=NotificationsSettingsConfig)


class AccountConfig(StrictConfigModel):
    """One Onshape API account entry from accounts.json."""

    name: str = Field(min_length=1)
    access_key: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)
    description: str = ""
    enabled: bool = True
    api_usage: int = Field(default=0, ge=0)
    last_used: str | None = None
    failure_count: int = Field(default=0, ge=0)
    rate_limit_status: str = "available"

    @field_validator("access_key", "secret_key")
    @classmethod
    def validate_secret_reference(cls, value: str) -> str:
        if value.startswith("env:") and len(value) == 4:
            raise ValueError("environment variable references must include a name")
        return value

    def to_runtime_model(self, *, resolve_env: bool = False) -> OnshapeAccount:
        return OnshapeAccount(
            name=self.name,
            access_key=resolve_secret_value(self.access_key) if resolve_env else self.access_key,
            secret_key=resolve_secret_value(self.secret_key) if resolve_env else self.secret_key,
            description=self.description,
            enabled=self.enabled,
            api_usage=self.api_usage,
            last_used=parse_config_datetime(self.last_used),
            failure_count=self.failure_count,
            rate_limit_status=self.rate_limit_status,
        )


class AccountsConfig(StrictConfigModel):
    """Top-level accounts.json model."""

    accounts: list[AccountConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_account_names(self) -> "AccountsConfig":
        ensure_unique([account.name for account in self.accounts], "account name")
        return self


class LabelConfig(StrictConfigModel):
    """One label entry from labels.json."""

    friendly_name: str = Field(min_length=1)
    onshape_label_id: str = Field(min_length=24, max_length=24)
    assigned_accounts: list[str] = Field(default_factory=list)
    export_location: str = "exports"
    export_profile: str = "STL"
    scheduler: str | None = None
    enabled: bool = True

    def to_runtime_model(self, base_dir: Path) -> LabelDefinition:
        export_location = Path(self.export_location)
        if not export_location.is_absolute():
            export_location = base_dir / export_location
        return LabelDefinition(
            friendly_name=self.friendly_name,
            onshape_label_id=self.onshape_label_id,
            assigned_accounts=list(self.assigned_accounts),
            export_location=export_location,
            export_profile=self.export_profile,
            scheduler=self.scheduler,
            enabled=self.enabled,
        )


class LabelsConfig(StrictConfigModel):
    """Top-level labels.json model."""

    labels: list[LabelConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_label_names(self) -> "LabelsConfig":
        ensure_unique([label.friendly_name for label in self.labels], "label name")
        return self


class ProfileBambuSettingsConfig(StrictConfigModel):
    """Bambu options stored per export profile."""

    enabled: bool = False
    create_3mf: bool = False
    open_bambu_studio: bool = False
    auto_arrange: bool = True
    auto_split_plates: bool = True
    machine_profile: str = ""
    process_profile: str = ""
    output_folder: str = ""

    def to_runtime_model(self) -> BambuSettings:
        return BambuSettings(
            enabled=self.enabled,
            create_3mf=self.create_3mf,
            open_bambu_studio=self.open_bambu_studio,
            auto_arrange=self.auto_arrange,
            auto_split_plates=self.auto_split_plates,
            machine_profile=self.machine_profile,
            process_profile=self.process_profile,
            output_folder=self.output_folder,
        )


class ExportProfileConfig(StrictConfigModel):
    """One export profile entry from export_profiles.json."""

    name: str = Field(min_length=1)
    formats: list[ExportFormat] = Field(default_factory=lambda: [ExportFormat.STL])
    options: dict[str, Any] = Field(default_factory=dict)
    bambu: ProfileBambuSettingsConfig = Field(default_factory=ProfileBambuSettingsConfig)
    enabled: bool = True

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, value: list[ExportFormat]) -> list[ExportFormat]:
        if not value:
            raise ValueError("at least one export format is required")
        return value

    def to_runtime_model(self) -> ExportProfile:
        return ExportProfile(
            name=self.name,
            formats=list(self.formats),
            options=dict(self.options),
            bambu=self.bambu.to_runtime_model(),
            enabled=self.enabled,
        )


class ExportProfilesConfig(StrictConfigModel):
    """Top-level export_profiles.json model."""

    profiles: list[ExportProfileConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_profile_names(self) -> "ExportProfilesConfig":
        ensure_unique([profile.name for profile in self.profiles], "export profile name")
        return self


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    """Validated configuration loaded from all JSON files."""

    app: AppConfig
    accounts: AccountsConfig
    labels: LabelsConfig
    export_profiles: ExportProfilesConfig

    def runtime_accounts(self, *, resolve_env: bool = False) -> list[OnshapeAccount]:
        return [account.to_runtime_model(resolve_env=resolve_env) for account in self.accounts.accounts]

    def runtime_labels(self, base_dir: Path) -> list[LabelDefinition]:
        return [label.to_runtime_model(base_dir) for label in self.labels.labels]

    def runtime_export_profiles(self) -> list[ExportProfile]:
        return [profile.to_runtime_model() for profile in self.export_profiles.profiles]


class ConfigManager:
    """Manages JSON configuration files."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    @property
    def config_file(self) -> Path:
        return self.paths.config_dir / "config.json"

    @property
    def accounts_file(self) -> Path:
        return self.paths.config_dir / "accounts.json"

    @property
    def labels_file(self) -> Path:
        return self.paths.config_dir / "labels.json"

    @property
    def export_profiles_file(self) -> Path:
        return self.paths.config_dir / "export_profiles.json"

    @property
    def organizations_file(self) -> Path:
        return self.paths.config_dir / "organizations.json"

    def ensure_default_files(self, *, overwrite: bool = False) -> None:
        """Create missing config files with safe defaults."""
        defaults = {
            self.config_file: default_app_config(),
            self.accounts_file: default_accounts_config(),
            self.labels_file: default_labels_config(),
            self.export_profiles_file: default_export_profiles_config(),
            self.organizations_file: {"organizations": []},
        }
        for path, payload in defaults.items():
            if overwrite or not path.exists():
                write_json(path, payload)

    def load(self) -> LoadedConfig:
        """Load and validate all configuration files."""
        self.ensure_default_files()
        loaded = LoadedConfig(
            app=AppConfig.model_validate(read_json(self.config_file)),
            accounts=AccountsConfig.model_validate(read_json(self.accounts_file)),
            labels=LabelsConfig.model_validate(read_json(self.labels_file)),
            export_profiles=ExportProfilesConfig.model_validate(
                read_json(self.export_profiles_file)
            ),
        )
        validate_cross_references(loaded)
        return loaded


def ensure_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise PydanticCustomError("duplicate_value", f"Duplicate {label}: {duplicate_list}")


def validate_cross_references(config: LoadedConfig) -> None:
    """Validate references between labels, accounts, and export profiles."""
    account_names = {account.name for account in config.accounts.accounts}
    profile_names = {profile.name for profile in config.export_profiles.profiles}

    errors: list[str] = []
    for label in config.labels.labels:
        missing_accounts = sorted(set(label.assigned_accounts) - account_names)
        if missing_accounts:
            errors.append(
                f"label '{label.friendly_name}' references missing accounts: "
                f"{', '.join(missing_accounts)}"
            )
        if label.export_profile not in profile_names:
            errors.append(
                f"label '{label.friendly_name}' references missing export profile: "
                f"{label.export_profile}"
            )
    if errors:
        raise ConfigError("; ".join(errors))


def resolve_secret_value(value: str) -> str:
    """Resolve a raw secret or an env:VARIABLE_NAME reference."""
    if not value.startswith("env:"):
        return value
    env_name = value[4:]
    secret = os.getenv(env_name)
    if secret is None:
        raise ConfigError(f"Missing required environment variable: {env_name}")
    return secret


def parse_config_datetime(value: str | None) -> datetime | None:
    """Parse an optional ISO datetime from JSON config."""
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing configuration file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration file must contain a JSON object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON object atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def default_app_config() -> dict[str, Any]:
    return {
        "onshape_base_url": "https://cad.onshape.com/api/v6",
        "worker_count": 4,
        "request_timeout_seconds": 30,
        "export_timeout_seconds": 120,
        "folders": {
            "exports_dir": "exports",
            "timestamp_format": "%Y-%m-%d_%H%M%S",
            "never_overwrite": True,
        },
        "retry": {
            "max_attempts": 4,
            "backoff_base_seconds": 1.0,
            "backoff_max_seconds": 60.0,
            "retry_http_statuses": [429, 500, 502, 503, 504],
        },
        "scheduler": {"enabled": False, "timezone": "local"},
        "logging": {"level": "INFO", "retention_days": 30, "mask_secrets": True},
        "ui": {"web_host": "127.0.0.1", "web_port": 8000, "theme": "system"},
        "server": {
            "mode": "desktop",
            "host": "0.0.0.0",
            "port": 8080,
            "behind_proxy": False,
            "auto_open_browser": True,
        },
        "bambu": {
            "enabled": False,
            "bambu_studio_exe": "",
            "profile_root": "",
            "machine_profile": "",
            "process_profile": "",
            "output_folder": "",
        },
    }


def default_accounts_config() -> dict[str, Any]:
    return {"accounts": []}


def default_labels_config() -> dict[str, Any]:
    return {"labels": []}


def default_export_profiles_config() -> dict[str, Any]:
    return {
        "profiles": [
            default_single_format_profile(
                "STL",
                ExportFormat.STL,
                options={"resolution": "medium"},
            ),
            default_single_format_profile(
                "STEP",
                ExportFormat.STEP,
                options={"stepVersionString": "AP242"},
            ),
            default_single_format_profile("OBJ", ExportFormat.OBJ),
            default_single_format_profile("IGES", ExportFormat.IGES),
            default_single_format_profile("Parasolid", ExportFormat.PARASOLID),
            default_multi_format_profile(
                "Mesh Bundle",
                [ExportFormat.STL, ExportFormat.OBJ],
                overrides={ExportFormat.STL: {"resolution": "medium"}},
            ),
            default_multi_format_profile(
                "CAD Bundle",
                [ExportFormat.STEP, ExportFormat.PARASOLID, ExportFormat.IGES],
                overrides={ExportFormat.STEP: {"stepVersionString": "AP242"}},
            ),
            default_multi_format_profile(
                "Multi Format",
                [
                    ExportFormat.STL,
                    ExportFormat.STEP,
                    ExportFormat.OBJ,
                    ExportFormat.PARASOLID,
                    ExportFormat.IGES,
                ],
                overrides={
                    ExportFormat.STL: {"resolution": "medium"},
                    ExportFormat.STEP: {"stepVersionString": "AP242"},
                },
            ),
            default_single_format_profile(
                "Bambu STL",
                ExportFormat.STL,
                options={"resolution": "medium"},
                bambu=default_bambu_settings(enabled=True, open_bambu_studio=True),
            ),
        ]
    }


def default_bambu_settings(
    *,
    enabled: bool = False,
    create_3mf: bool = False,
    open_bambu_studio: bool = False,
) -> dict[str, Any]:
    """Return editable default Bambu settings for an export profile."""
    return {
        "enabled": enabled,
        "create_3mf": create_3mf,
        "open_bambu_studio": open_bambu_studio,
        "auto_arrange": True,
        "auto_split_plates": True,
        "machine_profile": "",
        "process_profile": "",
        "output_folder": "",
    }


def default_single_format_profile(
    name: str,
    export_format: ExportFormat,
    *,
    options: dict[str, Any] | None = None,
    bambu: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a default profile for one export format."""
    profile_options = default_options_for(export_format)
    if options:
        profile_options.update(options)
    return {
        "name": name,
        "formats": [export_format.value],
        "options": profile_options,
        "bambu": bambu or default_bambu_settings(),
        "enabled": True,
    }


def default_multi_format_profile(
    name: str,
    formats: list[ExportFormat],
    *,
    overrides: dict[ExportFormat, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a default profile that exports several formats in one run."""
    overrides = overrides or {}
    options: dict[str, Any] = {}
    for export_format in formats:
        format_options = default_options_for(export_format)
        format_options.update(overrides.get(export_format, {}))
        options[export_format.value] = format_options
    return {
        "name": name,
        "formats": [export_format.value for export_format in formats],
        "options": options,
        "bambu": default_bambu_settings(),
        "enabled": True,
    }
