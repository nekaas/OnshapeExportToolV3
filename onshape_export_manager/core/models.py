"""Shared application models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class ExportFormat(StrEnum):
    """Supported export formats."""

    STL = "stl"
    STEP = "step"
    PARASOLID = "parasolid"
    OBJ = "obj"
    IGES = "iges"
    DXF = "dxf"
    PDF = "pdf"
    CUSTOM = "custom"


@dataclass(slots=True)
class OnshapeAccount:
    """An Onshape API account without storing raw secrets in logs."""

    name: str
    access_key: str
    secret_key: str
    description: str = ""
    enabled: bool = True
    api_usage: int = 0
    last_used: datetime | None = None
    failure_count: int = 0
    rate_limit_status: str = "available"
    rate_limited_until: datetime | None = None
    last_error: str = ""


@dataclass(slots=True)
class BambuSettings:
    """Optional Bambu Studio export settings."""

    enabled: bool = False
    create_3mf: bool = False
    open_bambu_studio: bool = False
    auto_arrange: bool = True
    auto_split_plates: bool = True
    machine_profile: str = ""
    process_profile: str = ""
    output_folder: str = ""


@dataclass(slots=True)
class ExportProfile:
    """Configurable export profile."""

    name: str
    formats: list[ExportFormat] = field(default_factory=lambda: [ExportFormat.STL])
    options: dict[str, object] = field(default_factory=dict)
    bambu: BambuSettings = field(default_factory=BambuSettings)
    enabled: bool = True


@dataclass(slots=True)
class LabelDefinition:
    """Maps an Onshape label to accounts, export settings, and scheduling."""

    friendly_name: str
    onshape_label_id: str
    assigned_accounts: list[str]
    export_location: Path
    export_profile: str
    scheduler: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class ExportJobRequest:
    """Manual or scheduled export request."""

    label: LabelDefinition
    profile: ExportProfile
    start_iso: str
    end_iso: str
    destination: Path | None = None
