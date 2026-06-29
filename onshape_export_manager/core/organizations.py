"""Onshape Organizations and multi-credential management.

An **Organization** represents a School, Company, Department, Customer, Workshop,
or Engineering Team. Each Organization owns one or more **API credentials**
(e.g. Primary, Backup, Testing, Emergency), so multiple Onshape API key pairs can
be grouped under a single customer without duplicate entries.

Credentials carry a priority and runtime health (requests today, failures,
latency, rate-limit state). The selector prefers lower-priority-number, least-used,
non-rate-limited credentials and automatically fails over to the next one.

This module is additive and backwards compatible: the existing flat
``accounts.json`` continues to work, and :func:`organizations_from_accounts`
migrates it into the richer model for the Web UI.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from onshape_export_manager.core.configuration import (
    ConfigManager,
    resolve_secret_value,
    read_json,
    write_json,
)
from onshape_export_manager.core.security import mask_secret

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.core.database import Database


CREDENTIAL_STATE_PREFIX = "credential.state."
DEFAULT_RATE_LIMIT_COOLDOWN = timedelta(minutes=15)


class OrganizationType(StrEnum):
    """Category of an Onshape Organization."""

    SCHOOL = "school"
    COMPANY = "company"
    DEPARTMENT = "department"
    CUSTOMER = "customer"
    WORKSHOP = "workshop"
    TEAM = "team"
    OTHER = "other"


class OrganizationError(RuntimeError):
    """Raised when an organization or credential edit cannot be applied."""


# -- Pydantic config models -------------------------------------------------


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CredentialConfig(_StrictModel):
    """One API credential pair stored under an organization."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1)
    access_key: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)
    environment: str = "production"
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=999)
    notes: str = ""

    @field_validator("access_key", "secret_key")
    @classmethod
    def validate_secret_reference(cls, value: str) -> str:
        if value.startswith("env:") and len(value) == 4:
            raise ValueError("environment variable references must include a name")
        return value

    def to_runtime(self, organization: str, *, resolve_env: bool = False) -> "Credential":
        return Credential(
            id=self.id,
            name=self.name,
            organization=organization,
            access_key=resolve_secret_value(self.access_key) if resolve_env else self.access_key,
            secret_key=resolve_secret_value(self.secret_key) if resolve_env else self.secret_key,
            environment=self.environment,
            enabled=self.enabled,
            priority=self.priority,
            notes=self.notes,
        )


class OrganizationConfig(_StrictModel):
    """One Onshape Organization with its credentials."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1)
    type: OrganizationType = OrganizationType.COMPANY
    description: str = ""
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=999)
    notes: str = ""
    credentials: list[CredentialConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_credential_names(self) -> "OrganizationConfig":
        names = [credential.name for credential in self.credentials]
        seen: set[str] = set()
        duplicates = {name for name in names if name in seen or seen.add(name)}
        if duplicates:
            raise PydanticCustomError(
                "duplicate_value",
                f"Duplicate credential name in '{self.name}': {', '.join(sorted(duplicates))}",
            )
        return self


class OrganizationsConfig(_StrictModel):
    """Top-level ``organizations.json`` model."""

    organizations: list[OrganizationConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_org_names(self) -> "OrganizationsConfig":
        names = [organization.name for organization in self.organizations]
        seen: set[str] = set()
        duplicates = {name for name in names if name in seen or seen.add(name)}
        if duplicates:
            raise PydanticCustomError(
                "duplicate_value", f"Duplicate organization name: {', '.join(sorted(duplicates))}"
            )
        return self

    def runtime_credentials(self, *, resolve_env: bool = False) -> list["Credential"]:
        return [
            credential.to_runtime(organization.name, resolve_env=resolve_env)
            for organization in self.organizations
            if organization.enabled
            for credential in organization.credentials
        ]


# -- Runtime dataclasses ----------------------------------------------------


@dataclass(slots=True)
class Credential:
    """Runtime view of a credential."""

    id: str
    name: str
    organization: str
    access_key: str
    secret_key: str
    environment: str = "production"
    enabled: bool = True
    priority: int = 1
    notes: str = ""


@dataclass(slots=True)
class CredentialState:
    """Mutable runtime health for one credential."""

    credential_id: str
    requests_today: int = 0
    requests_date: str = ""
    failure_count: int = 0
    latency_ms: float = 0.0
    rate_limit_status: str = "available"
    rate_limited_until: datetime | None = None
    last_used: datetime | None = None
    last_error: str = ""

    def roll_day(self, today: str) -> None:
        if self.requests_date != today:
            self.requests_date = today
            self.requests_today = 0

    def is_rate_limited(self, now: datetime) -> bool:
        if self.rate_limit_status != "rate_limited":
            return False
        return self.rate_limited_until is None or self.rate_limited_until > now

    def clear_expired_cooldown(self, now: datetime) -> None:
        if (
            self.rate_limit_status == "rate_limited"
            and self.rate_limited_until is not None
            and self.rate_limited_until <= now
        ):
            self.rate_limit_status = "available"
            self.rate_limited_until = None
            self.last_error = ""

    def health(self) -> str:
        if self.rate_limit_status == "rate_limited":
            return "rate_limited"
        if self.rate_limit_status == "failed":
            return "failed"
        if self.failure_count > 0:
            return "degraded"
        return "healthy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "requests_today": self.requests_today,
            "requests_date": self.requests_date,
            "failure_count": self.failure_count,
            "latency_ms": round(self.latency_ms, 1),
            "rate_limit_status": self.rate_limit_status,
            "rate_limited_until": _iso(self.rate_limited_until),
            "last_used": _iso(self.last_used),
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CredentialState":
        return cls(
            credential_id=str(payload["credential_id"]),
            requests_today=int(payload.get("requests_today", 0)),
            requests_date=str(payload.get("requests_date", "")),
            failure_count=int(payload.get("failure_count", 0)),
            latency_ms=float(payload.get("latency_ms", 0.0)),
            rate_limit_status=str(payload.get("rate_limit_status", "available")),
            rate_limited_until=_parse(payload.get("rate_limited_until")),
            last_used=_parse(payload.get("last_used")),
            last_error=str(payload.get("last_error", "")),
        )


# -- Credential selection (priority + failover) -----------------------------


def order_credentials(
    credentials: Sequence[Credential],
    states: dict[str, CredentialState],
    now: datetime,
) -> list[Credential]:
    """Return credentials ordered for use (best first), with failover fallback.

    Enabled, non-rate-limited credentials come first, sorted by priority (lower
    is preferred), then least requests today, then fewest failures, then least
    recently used. Rate-limited credentials are returned last, soonest-recovering
    first, so callers can still fail over to them once cooldowns expire.
    """
    available: list[Credential] = []
    cooling: list[Credential] = []
    for credential in credentials:
        if not credential.enabled:
            continue
        state = states.get(credential.id)
        if state is not None:
            state.clear_expired_cooldown(now)
        if state is not None and state.is_rate_limited(now):
            cooling.append(credential)
        else:
            available.append(credential)

    available.sort(key=lambda cred: _selection_key(cred, states.get(cred.id)))
    cooling.sort(key=lambda cred: _cooldown_key(states.get(cred.id), now))
    return available + cooling


def _selection_key(credential: Credential, state: CredentialState | None) -> tuple[int, int, int, datetime]:
    requests_today = state.requests_today if state else 0
    failures = state.failure_count if state else 0
    last_used = (state.last_used if state and state.last_used else datetime.min.replace(tzinfo=timezone.utc))
    return (credential.priority, requests_today, failures, last_used)


def _cooldown_key(state: CredentialState | None, now: datetime) -> datetime:
    if state and state.rate_limited_until:
        return state.rate_limited_until
    return now


class CredentialPool:
    """Selects credentials with priority + failover and tracks health in SQLite."""

    def __init__(
        self,
        credentials: Sequence[Credential],
        *,
        database: "Database | None" = None,
        cooldown: timedelta = DEFAULT_RATE_LIMIT_COOLDOWN,
        now_fn=None,
    ) -> None:
        self._credentials = {credential.id: credential for credential in credentials}
        self._database = database
        self._cooldown = cooldown
        self._now_fn = now_fn or _utc_now
        self._states = {credential.id: self._load_state(credential.id) for credential in credentials}

    def lease(self, candidate_ids: Sequence[str] | None = None) -> Credential:
        """Lease the best available credential, optionally restricted to ids."""
        now = self._now()
        today = now.date().isoformat()
        candidates = self._candidates(candidate_ids)
        if not candidates:
            raise OrganizationError("No enabled credentials are available for selection.")
        for state in self._states.values():
            state.roll_day(today)
        ordered = order_credentials(candidates, self._states, now)
        if not ordered:
            raise OrganizationError("No selectable credentials (all disabled).")
        chosen = ordered[0]
        state = self._states[chosen.id]
        if state.is_rate_limited(now):
            raise OrganizationError("All eligible credentials are currently rate limited.")
        state.last_used = now
        self._persist(chosen.id)
        return chosen

    def record_success(self, credential_id: str, *, latency_ms: float | None = None) -> None:
        state = self._state(credential_id)
        state.roll_day(self._now().date().isoformat())
        state.requests_today += 1
        state.rate_limit_status = "available"
        state.rate_limited_until = None
        state.last_error = ""
        state.last_used = self._now()
        if latency_ms is not None:
            state.latency_ms = latency_ms if state.latency_ms == 0 else (state.latency_ms * 0.7 + latency_ms * 0.3)
        self._persist(credential_id)

    def record_failure(self, credential_id: str, error: str) -> None:
        state = self._state(credential_id)
        state.failure_count += 1
        state.rate_limit_status = "failed"
        state.last_error = error
        state.last_used = self._now()
        self._persist(credential_id)

    def record_rate_limited(self, credential_id: str, *, reset_at: datetime | None = None) -> None:
        now = self._now()
        state = self._state(credential_id)
        state.failure_count += 1
        state.rate_limit_status = "rate_limited"
        state.rate_limited_until = reset_at or now + self._cooldown
        state.last_used = now
        self._persist(credential_id)

    def snapshot(self) -> list[CredentialState]:
        now = self._now()
        for state in self._states.values():
            state.clear_expired_cooldown(now)
        return [self._states[cid] for cid in self._states]

    def state_for(self, credential_id: str) -> CredentialState | None:
        return self._states.get(credential_id)

    def _candidates(self, candidate_ids: Sequence[str] | None) -> list[Credential]:
        if candidate_ids is None:
            return list(self._credentials.values())
        wanted = set(candidate_ids)
        return [cred for cred in self._credentials.values() if cred.id in wanted]

    def _state(self, credential_id: str) -> CredentialState:
        try:
            return self._states[credential_id]
        except KeyError as exc:
            raise OrganizationError(f"Unknown credential id: {credential_id}") from exc

    def _load_state(self, credential_id: str) -> CredentialState:
        if self._database is None:
            return CredentialState(credential_id=credential_id)
        payload = self._database.get_state(self._key(credential_id))
        if not payload:
            return CredentialState(credential_id=credential_id)
        try:
            import json

            return CredentialState.from_dict(json.loads(payload))
        except (ValueError, KeyError, TypeError):
            return CredentialState(credential_id=credential_id)

    def _persist(self, credential_id: str) -> None:
        if self._database is None:
            return
        import json

        self._database.set_state(self._key(credential_id), json.dumps(self._states[credential_id].to_dict()))

    def _key(self, credential_id: str) -> str:
        return f"{CREDENTIAL_STATE_PREFIX}{credential_id}"

    def _now(self) -> datetime:
        now = self._now_fn()
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


# -- CRUD manager -----------------------------------------------------------


@dataclass(slots=True)
class OrganizationManager:
    """Create, edit, and delete organizations and credentials in organizations.json."""

    config_manager: ConfigManager

    def load(self) -> OrganizationsConfig:
        path = self.config_manager.organizations_file
        if not path.exists():
            write_json(path, {"organizations": []})
        return OrganizationsConfig.model_validate(read_json(path))

    def save(self, config: OrganizationsConfig) -> None:
        OrganizationsConfig.model_validate(config.model_dump(mode="json"))
        write_json(self.config_manager.organizations_file, config.model_dump(mode="json"))

    def create_organization(
        self,
        name: str,
        *,
        org_type: str = "company",
        description: str = "",
        priority: int = 1,
        notes: str = "",
    ) -> OrganizationConfig:
        config = self.load()
        if any(org.name == name for org in config.organizations):
            raise OrganizationError(f"organization '{name}' already exists")
        organization = OrganizationConfig(
            name=name, type=OrganizationType(org_type), description=description,
            priority=priority, notes=notes,
        )
        config.organizations.append(organization)
        self.save(config)
        return organization

    def update_organization(self, org_id: str, **changes: Any) -> OrganizationConfig:
        config = self.load()
        organization = self._find_org(config, org_id)
        data = organization.model_dump(mode="json")
        for key in ("name", "type", "description", "enabled", "priority", "notes"):
            if key in changes and changes[key] is not None:
                data[key] = changes[key]
        updated = OrganizationConfig.model_validate(data)
        config.organizations = [updated if org.id == org_id else org for org in config.organizations]
        self.save(config)
        return updated

    def delete_organization(self, org_id: str) -> None:
        config = self.load()
        self._find_org(config, org_id)
        config.organizations = [org for org in config.organizations if org.id != org_id]
        self.save(config)

    def duplicate_organization(self, org_id: str) -> OrganizationConfig:
        config = self.load()
        organization = self._find_org(config, org_id)
        clone = OrganizationConfig.model_validate(organization.model_dump(mode="json"))
        clone.id = uuid4().hex
        clone.name = _unique_name(organization.name, {org.name for org in config.organizations})
        for credential in clone.credentials:
            credential.id = uuid4().hex
        config.organizations.append(clone)
        self.save(config)
        return clone

    def set_organization_enabled(self, org_id: str, enabled: bool) -> OrganizationConfig:
        return self.update_organization(org_id, enabled=enabled)

    def add_credential(
        self,
        org_id: str,
        *,
        name: str,
        access_key: str,
        secret_key: str,
        environment: str = "production",
        priority: int = 1,
        notes: str = "",
    ) -> CredentialConfig:
        config = self.load()
        organization = self._find_org(config, org_id)
        if any(cred.name == name for cred in organization.credentials):
            raise OrganizationError(f"credential '{name}' already exists in '{organization.name}'")
        credential = CredentialConfig(
            name=name, access_key=access_key, secret_key=secret_key,
            environment=environment, priority=priority, notes=notes,
        )
        organization.credentials.append(credential)
        self.save(config)
        return credential

    def update_credential(self, org_id: str, credential_id: str, **changes: Any) -> CredentialConfig:
        config = self.load()
        organization = self._find_org(config, org_id)
        credential = self._find_credential(organization, credential_id)
        data = credential.model_dump(mode="json")
        for key in ("name", "access_key", "secret_key", "environment", "enabled", "priority", "notes"):
            if key in changes and changes[key] is not None:
                data[key] = changes[key]
        updated = CredentialConfig.model_validate(data)
        organization.credentials = [
            updated if cred.id == credential_id else cred for cred in organization.credentials
        ]
        self.save(config)
        return updated

    def delete_credential(self, org_id: str, credential_id: str) -> None:
        config = self.load()
        organization = self._find_org(config, org_id)
        self._find_credential(organization, credential_id)
        organization.credentials = [c for c in organization.credentials if c.id != credential_id]
        self.save(config)

    def set_credential_enabled(self, org_id: str, credential_id: str, enabled: bool) -> CredentialConfig:
        return self.update_credential(org_id, credential_id, enabled=enabled)

    def import_from_accounts(self, *, overwrite: bool = False) -> OrganizationsConfig:
        """Migrate the flat accounts.json into organizations (one org per account)."""
        config = self.load()
        if config.organizations and not overwrite:
            return config
        accounts_path = self.config_manager.accounts_file
        if not accounts_path.exists():
            return config
        accounts = read_json(accounts_path).get("accounts", [])
        migrated = organizations_from_accounts(accounts)
        self.save(migrated)
        return migrated

    def _find_org(self, config: OrganizationsConfig, org_id: str) -> OrganizationConfig:
        for organization in config.organizations:
            if organization.id == org_id:
                return organization
        raise OrganizationError(f"organization '{org_id}' not found")

    def _find_credential(self, organization: OrganizationConfig, credential_id: str) -> CredentialConfig:
        for credential in organization.credentials:
            if credential.id == credential_id:
                return credential
        raise OrganizationError(f"credential '{credential_id}' not found")


def organizations_from_accounts(accounts: list[dict[str, Any]]) -> OrganizationsConfig:
    """Build an OrganizationsConfig from legacy flat account dicts."""
    organizations: list[OrganizationConfig] = []
    for account in accounts:
        name = str(account.get("name", "")).strip()
        if not name:
            continue
        organizations.append(
            OrganizationConfig(
                name=name,
                type=OrganizationType.COMPANY,
                description=str(account.get("description", "")),
                enabled=bool(account.get("enabled", True)),
                credentials=[
                    CredentialConfig(
                        name="Primary",
                        access_key=str(account.get("access_key", "")) or "env:UNSET_ACCESS_KEY",
                        secret_key=str(account.get("secret_key", "")) or "env:UNSET_SECRET_KEY",
                        priority=1,
                    )
                ],
            )
        )
    return OrganizationsConfig(organizations=organizations)


def serialize_organization(organization: OrganizationConfig, states: dict[str, CredentialState] | None = None) -> dict[str, Any]:
    """Serialize an organization for the API/UI, masking secrets."""
    states = states or {}
    return {
        "id": organization.id,
        "name": organization.name,
        "type": organization.type.value,
        "description": organization.description,
        "enabled": organization.enabled,
        "priority": organization.priority,
        "notes": organization.notes,
        "credential_count": len(organization.credentials),
        "credentials": [serialize_credential(cred, states.get(cred.id)) for cred in organization.credentials],
    }


def serialize_credential(credential: CredentialConfig, state: CredentialState | None = None) -> dict[str, Any]:
    payload = {
        "id": credential.id,
        "name": credential.name,
        "environment": credential.environment,
        "enabled": credential.enabled,
        "priority": credential.priority,
        "notes": credential.notes,
        "access_key": mask_secret(credential.access_key),
        "secret_key": "********",
        "health": state.health() if state else "unknown",
        "requests_today": state.requests_today if state else 0,
        "failure_count": state.failure_count if state else 0,
        "latency_ms": round(state.latency_ms, 1) if state else 0.0,
        "rate_limited": bool(state and state.is_rate_limited(_utc_now())),
        "last_used": _iso(state.last_used) if state else None,
    }
    return payload


def _unique_name(base: str, existing: set[str]) -> str:
    candidate = f"{base} (copy)"
    counter = 2
    while candidate in existing:
        candidate = f"{base} (copy {counter})"
        counter += 1
    return candidate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
