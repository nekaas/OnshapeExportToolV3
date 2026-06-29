"""Helpers for editing export profile configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from onshape_export_manager.core.configuration import (
    ConfigManager,
    ExportProfilesConfig,
    default_bambu_settings,
    default_multi_format_profile,
    default_single_format_profile,
    read_json,
    write_json,
)
from onshape_export_manager.core.export_formats import get_format_definition
from onshape_export_manager.core.models import ExportFormat


class ExportProfileManagerError(RuntimeError):
    """Raised when an export profile edit cannot be applied."""


@dataclass(slots=True)
class ExportProfileManager:
    """Edit export profiles while preserving JSON validation."""

    config_manager: ConfigManager

    def add_profile(
        self,
        name: str,
        formats: Iterable[ExportFormat],
        *,
        replace: bool = False,
        bambu_enabled: bool = False,
        open_bambu_studio: bool = False,
    ) -> dict[str, object]:
        """Add or replace an export profile in ``export_profiles.json``."""
        profile_name = name.strip()
        if not profile_name:
            raise ExportProfileManagerError("export profile name cannot be empty")

        format_list = normalize_profile_formats(formats)
        payload = read_json(self.config_manager.export_profiles_file)
        existing = ExportProfilesConfig.model_validate(payload)
        existing_names = {profile.name for profile in existing.profiles}
        if profile_name in existing_names and not replace:
            raise ExportProfileManagerError(
                f"export profile '{profile_name}' already exists; use --replace-profile"
            )

        bambu = default_bambu_settings(
            enabled=bambu_enabled,
            open_bambu_studio=open_bambu_studio,
        )
        if len(format_list) == 1:
            new_profile = default_single_format_profile(
                profile_name,
                format_list[0],
                bambu=bambu,
            )
        else:
            new_profile = default_multi_format_profile(profile_name, format_list)
            new_profile["bambu"] = bambu

        profiles = [
            profile.model_dump(mode="json")
            for profile in existing.profiles
            if profile.name != profile_name
        ]
        profiles.append(new_profile)
        updated = {"profiles": profiles}
        ExportProfilesConfig.model_validate(updated)
        write_json(self.config_manager.export_profiles_file, updated)
        return new_profile


def parse_format_list(raw_formats: str) -> list[ExportFormat]:
    """Parse comma or whitespace separated export format names."""
    tokens = [
        token.strip().lower()
        for chunk in raw_formats.split(",")
        for token in chunk.split()
        if token.strip()
    ]
    if not tokens:
        raise ExportProfileManagerError("at least one export format is required")

    formats: list[ExportFormat] = []
    for token in tokens:
        try:
            formats.append(ExportFormat(token))
        except ValueError as exc:
            raise ExportProfileManagerError(f"unsupported export format: {token}") from exc
    return normalize_profile_formats(formats)


def normalize_profile_formats(formats: Iterable[ExportFormat]) -> list[ExportFormat]:
    """Return unique, Part Studio-capable export formats in input order."""
    normalized: list[ExportFormat] = []
    seen: set[ExportFormat] = set()
    for export_format in formats:
        if export_format in seen:
            continue
        definition = get_format_definition(export_format)
        if export_format == ExportFormat.CUSTOM or not definition.supports_part_studio:
            raise ExportProfileManagerError(
                f"{export_format.value} is not available as a built-in Part Studio profile"
            )
        normalized.append(export_format)
        seen.add(export_format)

    if not normalized:
        raise ExportProfileManagerError("at least one export format is required")
    return normalized
