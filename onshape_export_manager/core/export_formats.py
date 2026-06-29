"""Export format definitions and registry."""

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
    supports_part_studio: bool = True
    supports_drawing: bool = False
    onshape_native: bool = True
    default_options: dict[str, Any] = field(default_factory=dict)


DEFAULT_FORMATS: dict[ExportFormat, ExportFormatDefinition] = {
    ExportFormat.STL: ExportFormatDefinition(
        ExportFormat.STL,
        "STL",
        ".stl",
        default_options={"mode": "binary", "units": "millimeter"},
    ),
    ExportFormat.STEP: ExportFormatDefinition(
        ExportFormat.STEP,
        "STEP",
        ".step",
        default_options={"formatName": "STEP", "storeInDocument": False},
    ),
    ExportFormat.PARASOLID: ExportFormatDefinition(
        ExportFormat.PARASOLID,
        "Parasolid",
        ".x_t",
        default_options={"formatName": "PARASOLID", "storeInDocument": False},
    ),
    ExportFormat.OBJ: ExportFormatDefinition(
        ExportFormat.OBJ,
        "OBJ",
        ".obj",
        default_options={"formatName": "OBJ", "storeInDocument": False},
    ),
    ExportFormat.IGES: ExportFormatDefinition(
        ExportFormat.IGES,
        "IGES",
        ".iges",
        default_options={"formatName": "IGES", "storeInDocument": False},
    ),
    ExportFormat.DXF: ExportFormatDefinition(
        ExportFormat.DXF,
        "DXF",
        ".dxf",
        default_options={"formatName": "DXF", "storeInDocument": False},
    ),
    ExportFormat.PDF: ExportFormatDefinition(
        ExportFormat.PDF,
        "PDF Drawing",
        ".pdf",
        supports_part_studio=False,
        supports_drawing=True,
        default_options={"formatName": "PDF", "storeInDocument": False},
    ),
    ExportFormat.CUSTOM: ExportFormatDefinition(
        ExportFormat.CUSTOM,
        "Custom",
        "",
        supports_part_studio=False,
        onshape_native=False,
    ),
}


def get_format_definition(export_format: ExportFormat) -> ExportFormatDefinition:
    """Return metadata for a supported export format."""
    return DEFAULT_FORMATS[export_format]


def list_format_definitions(
    *,
    part_studio_only: bool = False,
    drawing_only: bool = False,
) -> list[ExportFormatDefinition]:
    """Return supported export formats in display order."""
    definitions = list(DEFAULT_FORMATS.values())
    if part_studio_only:
        definitions = [item for item in definitions if item.supports_part_studio]
    if drawing_only:
        definitions = [item for item in definitions if item.supports_drawing]
    return definitions


def default_options_for(export_format: ExportFormat) -> dict[str, Any]:
    """Return a copy of the default option map for one format."""
    return dict(get_format_definition(export_format).default_options)
