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

    label: str = Field(..., min_length=1, description="Friendly name of the label to export")
    profile: str | None = Field(None, description="Export profile name (uses label default if omitted)")
    start: str | None = Field(None, description="ISO 8601 start date filter (inclusive)")
    end: str | None = Field(None, description="ISO 8601 end date filter (inclusive)")
    destination: str | None = Field(None, min_length=1, description="Custom export destination path")


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
