"""Export format definitions — professional presets for CAD/CAM/3D printing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from onshape_export_manager.core.models import ExportFormat


@dataclass(frozen=True, slots=True)
class ExportFormatDefinition:
    """Metadata for one supported export format."""

    format: ExportFormat
    display_name: str
    default_extension: str
    onshape_native: bool = True
    default_options: dict[str, Any] = field(default_factory=dict)


# ── 8 export formats covering all manufacturing needs ─────────────────────
DEFAULT_FORMATS: dict[ExportFormat, ExportFormatDefinition] = {
    # -- STL (binary, millimeter) — standard for 3D printing ---------------
    ExportFormat.STL: ExportFormatDefinition(
        ExportFormat.STL,
        "STL",
        ".stl",
        default_options={"mode": "binary", "units": "millimeter"},
    ),
    # -- STEP — standard for CAM / machining -------------------------------
    ExportFormat.STEP: ExportFormatDefinition(
        ExportFormat.STEP,
        "STEP",
        ".step",
        default_options={"formatName": "STEP", "storeInDocument": False},
    ),
    # -- 3MF — modern 3D printing format -----------------------------------
    ExportFormat.MF3: ExportFormatDefinition(
        ExportFormat.MF3,
        "3MF",
        ".3mf",
        default_options={"formatName": "3MF", "storeInDocument": False},
    ),
    # -- Parasolid — for SolidWorks / Siemens NX ---------------------------
    ExportFormat.PARASOLID: ExportFormatDefinition(
        ExportFormat.PARASOLID,
        "Parasolid",
        ".x_t",
        default_options={"formatName": "PARASOLID", "storeInDocument": False},
    ),
    # -- OBJ — for Blender / rendering -------------------------------------
    ExportFormat.OBJ: ExportFormatDefinition(
        ExportFormat.OBJ,
        "OBJ",
        ".obj",
        default_options={"formatName": "OBJ", "storeInDocument": False},
    ),
    # -- GLTF — for web / AR viewing ---------------------------------------
    ExportFormat.GLTF: ExportFormatDefinition(
        ExportFormat.GLTF,
        "GLTF",
        ".gltf",
        default_options={"formatName": "GLTF", "storeInDocument": False},
    ),
    # -- DXF — for laser cutting / 2D --------------------------------------
    ExportFormat.DXF: ExportFormatDefinition(
        ExportFormat.DXF,
        "DXF",
        ".dxf",
        default_options={"formatName": "DXF", "storeInDocument": False},
    ),
    # -- Native — Onshape document backup ----------------------------------
    ExportFormat.NATIVE: ExportFormatDefinition(
        ExportFormat.NATIVE,
        "Native Backup",
        ".onshape",
        default_options={"formatName": "ONSHAPE", "storeInDocument": False},
    ),
}


def get_format_definition(export_format: ExportFormat) -> ExportFormatDefinition:
    """Return metadata for a supported export format."""
    return DEFAULT_FORMATS[export_format]


def list_format_definitions() -> list[ExportFormatDefinition]:
    """Return all supported export formats."""
    return list(DEFAULT_FORMATS.values())


def default_options_for(export_format: ExportFormat) -> dict[str, Any]:
    """Return a copy of the default option map for one format."""
    return dict(get_format_definition(export_format).default_options)
