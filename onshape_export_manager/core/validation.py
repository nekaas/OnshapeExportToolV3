"""API request/response validation models.

Pydantic models used by FastAPI endpoints for automatic request validation,
OpenAPI schema generation, and consistent error reporting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# -- Manual export ---------------------------------------------------------


class ManualExportRequest(BaseModel):
    """Request body for ``POST /api/exports/run`` and ``/api/exports/preview``."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(None, min_length=1, description="Friendly name of a single label to export")
    labels: list[str] | None = Field(None, min_length=1, description="Multiple label names to export as a group")
    profile: str | None = Field(None, description="Export profile name (uses label default if omitted)")
    start: str | None = Field(None, description="ISO 8601 start date filter (inclusive)")
    end: str | None = Field(None, description="ISO 8601 end date filter (inclusive)")
    destination: str | None = Field(None, min_length=1, description="Custom export destination path")

    @model_validator(mode="after")
    def _at_least_one_label(self) -> "ManualExportRequest":
        if not self.label and not self.labels:
            raise ValueError("Either 'label' or 'labels' must be provided")
        return self


# -- Labels ------------------------------------------------------------------


class CreateLabelRequest(BaseModel):
    """Request body for ``POST /api/labels``."""

    model_config = ConfigDict(extra="forbid")

    friendly_name: str = Field(..., min_length=1, max_length=128)
    onshape_label_id: str = Field(..., min_length=1, max_length=64)
    assigned_accounts: list[str] = Field(default_factory=list)
    export_location: str = Field(default="exports", min_length=1)
    export_profile: str = Field(default="STL", min_length=1)
    scheduler: dict[str, Any] | None = None
    enabled: bool = True

    @field_validator("friendly_name")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("friendly_name must not be empty or whitespace")
        return v.strip()


# -- Organizations -----------------------------------------------------------


class CreateOrganizationRequest(BaseModel):
    """Request body for ``POST /api/organizations``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(default="other", pattern=r"^(school|company|department|customer|workshop|team|other)$")
    description: str = Field(default="")
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=999)
    notes: str = Field(default="")


class AddCredentialRequest(BaseModel):
    """Request body for ``POST /api/organizations/{org_id}/credentials``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128)
    access_key: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=1)
    environment: str = Field(default="production")
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=999)
    notes: str = Field(default="")


# -- Export profiles ---------------------------------------------------------


class CreateProfileRequest(BaseModel):
    """Request body for ``POST /api/profiles``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128)
    formats: list[str] = Field(..., min_length=1)
    options: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


# -- Notifications -----------------------------------------------------------


class CreateNotificationRequest(BaseModel):
    """Request body for ``POST /api/notifications``."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., pattern=r"^(discord|slack|teams|email|webhook)$")
    name: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1)
    enabled: bool = True
    categories: list[str] | None = None
    min_severity: str = Field(default="warning")
    options: dict[str, Any] = Field(default_factory=dict)


class UpdateNotificationRequest(BaseModel):
    """Request body for ``PUT /api/notifications/{channel_id}``."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=128)
    kind: str | None = Field(None, pattern=r"^(discord|slack|teams|email|webhook)$")
    target: str | None = Field(None, min_length=1)
    enabled: bool | None = None
    categories: list[str] | None = None
    min_severity: str | None = None
    options: dict[str, Any] | None = None


# -- Setup wizard ------------------------------------------------------------


class CreateOwnerRequest(BaseModel):
    """Request body for ``POST /api/setup/owner``."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=256)


class SetStorageRequest(BaseModel):
    """Request body for ``POST /api/setup/storage``."""

    model_config = ConfigDict(extra="forbid")

    exports_dir: str = Field(..., min_length=1)


# -- Per-format export option schemas (Item 28) ------------------------------


class StlOptions(BaseModel):
    """Options for STL export."""

    model_config = ConfigDict(extra="allow")  # allow future Onshape options

    mode: str = Field(default="binary", pattern=r"^(binary|text)$")
    units: str = Field(default="millimeter", pattern=r"^(inch|millimeter|centimeter|meter|foot|yard)$")
    resolution: str = Field(default="medium", pattern=r"^(coarse|medium|fine)$")


class StepOptions(BaseModel):
    """Options for STEP export."""

    model_config = ConfigDict(extra="allow")

    formatName: str = Field(default="STEP")
    storeInDocument: bool = False
    stepVersionString: str | None = None


class ParasolidOptions(BaseModel):
    """Options for Parasolid export."""

    model_config = ConfigDict(extra="allow")

    formatName: str = Field(default="PARASOLID")
    storeInDocument: bool = False


class ObjOptions(BaseModel):
    """Options for OBJ export."""

    model_config = ConfigDict(extra="allow")

    formatName: str = Field(default="OBJ")
    storeInDocument: bool = False


class IgesOptions(BaseModel):
    """Options for IGES export."""

    model_config = ConfigDict(extra="allow")

    formatName: str = Field(default="IGES")
    storeInDocument: bool = False


# Per-format option validator lookup
_FORMAT_OPTION_VALIDATORS: dict[str, type[BaseModel]] = {
    "stl": StlOptions,
    "step": StepOptions,
    "parasolid": ParasolidOptions,
    "obj": ObjOptions,
    "iges": IgesOptions,
}


def validate_export_options(formats: list[str], options: dict[str, Any]) -> None:
    """Validate per-format export options against their schemas.

    Raises ``ValidationError`` if any format's options are invalid.
    Formats with no registered schema (dxf, pdf, custom) pass through.
    Unknown formats are silently ignored.
    """
    from pydantic import ValidationError as PydanticValidationError

    errors: list[str] = []
    for fmt in formats:
        key = fmt.lower()
        validator = _FORMAT_OPTION_VALIDATORS.get(key)
        if validator is None:
            continue  # no strict schema for this format
        fmt_options = options.get(fmt, options.get(key, {}))
        if not isinstance(fmt_options, dict):
            continue
        try:
            validator.model_validate(fmt_options)
        except PydanticValidationError as exc:
            for err in exc.errors():
                loc = " → ".join(str(p) for p in err["loc"])
                errors.append(f"{fmt}.{loc}: {err['msg']}")
    if errors:
        raise ValueError("Invalid export options: " + "; ".join(errors))
