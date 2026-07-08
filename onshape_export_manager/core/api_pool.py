"""Account selection and rate-limit aware API pool."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from onshape_export_manager.core.database import Database
from onshape_export_manager.core.models import OnshapeAccount


ACCOUNT_STATE_PREFIX = "api_pool.account_state."


class ApiPoolError(RuntimeError):
    """Base error for account pool selection failures."""


class NoEnabledAccountsError(ApiPoolError):
    """Raised when no enabled accounts can be selected."""


class AllAccountsRateLimitedError(ApiPoolError):
    """Raised when every eligible account is inside a rate-limit cooldown."""

    def __init__(self, message: str, next_available_at: datetime | None = None) -> None:
        super().__init__(message)
        self.next_available_at = next_available_at


@dataclass(slots=True)
class AccountRuntimeState:
    """Mutable API state for one Onshape account."""

    name: str
    api_usage: int = 0
    failure_count: int = 0
    rate_limit_status: str = "available"
    last_used: datetime | None = None
    rate_limited_until: datetime | None = None
    last_error: str = ""

    @classmethod
    def from_account(cls, account: OnshapeAccount) -> "AccountRuntimeState":
        return cls(
            name=account.name,
            api_usage=account.api_usage,
            failure_count=account.failure_count,
            rate_limit_status=account.rate_limit_status,
            last_used=account.last_used,
            rate_limited_until=account.rate_limited_until,
            last_error=account.last_error,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AccountRuntimeState":
        return cls(
            name=str(payload["name"]),
            api_usage=int(payload.get("api_usage", 0)),
            failure_count=int(payload.get("failure_count", 0)),
            rate_limit_status=str(payload.get("rate_limit_status", "available")),
            last_used=parse_dt(payload.get("last_used")),
            rate_limited_until=parse_dt(payload.get("rate_limited_until")),
            last_error=str(payload.get("last_error", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_usage": self.api_usage,
            "failure_count": self.failure_count,
            "rate_limit_status": self.rate_limit_status,
            "last_used": serialize_dt(self.last_used),
            "rate_limited_until": serialize_dt(self.rate_limited_until),
            "last_error": self.last_error,
        }

    def is_rate_limited(self, now: datetime) -> bool:
        if self.rate_limit_status != "rate_limited":
            return False
        return self.rate_limited_until is None or self.rate_limited_until > now

    def mark_available_if_cooldown_expired(self, now: datetime) -> None:
        if self.rate_limit_status == "rate_limited" and self.rate_limited_until is not None:
            if self.rate_limited_until <= now:
                self.rate_limit_status = "available"
                self.rate_limited_until = None
                self.last_error = ""


@dataclass(slots=True)
class AccountLease:
    """Represents an account selected for a unit of API work."""

    account: OnshapeAccount
    leased_at: datetime
    state: AccountRuntimeState


class ApiPool:
    """Select enabled accounts for export work and track runtime API health.

    All state-mutating methods are guarded by an internal ``threading.Lock``
    so the pool is safe to use concurrently from the web dashboard thread
    (``snapshot()``, ``available_account_names()``) and the background
    worker thread (``record_success()``, ``record_failure()``, etc.).
    """

    def __init__(
        self,
        accounts: Sequence[OnshapeAccount],
        *,
        database: Database | None = None,
        default_rate_limit_cooldown: timedelta = timedelta(minutes=15),
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._accounts = {account.name: account for account in accounts}
        self._database = database
        self._default_rate_limit_cooldown = default_rate_limit_cooldown
        self._now_fn = now_fn or utc_now
        self._lock = threading.Lock()
        self._states = {
            account.name: self._load_state(account)
            for account in accounts
        }
        self._sync_accounts_from_state()

    def lease(self, assigned_account_names: Sequence[str] | None = None) -> AccountLease:
        """Lease the best available account for a label or export job."""
        now = self._now()
        with self._lock:
            candidates = self._eligible_accounts(assigned_account_names)
            if not candidates:
                raise NoEnabledAccountsError("No enabled Onshape accounts are configured.")

            for account in candidates:
                self._states[account.name].mark_available_if_cooldown_expired(now)

            available = [
                account
                for account in candidates
                if not self._states[account.name].is_rate_limited(now)
            ]
            if not available:
                next_available_at = self._next_available_at(candidates)
                raise AllAccountsRateLimitedError(
                    "Every eligible Onshape account is currently rate limited.",
                    next_available_at=next_available_at,
                )

            account = min(available, key=self._selection_key)
            state = self._states[account.name]
            state.last_used = now
            state.mark_available_if_cooldown_expired(now)
            if state.rate_limit_status not in {"failed", "rate_limited"}:
                state.rate_limit_status = "available"
            self._apply_state_to_account(account.name)
            # Capture the lease details before releasing the lock
            leased_account = account
            leased_state = state
        # Persist outside the lock to avoid holding it during I/O
        self._persist_state(leased_account.name)
        return AccountLease(account=leased_account, leased_at=now, state=leased_state)

    def record_success(self, account_name: str, *, api_calls: int = 1) -> None:
        """Record successful API work for an account."""
        with self._lock:
            state = self._state_for(account_name)
            state.api_usage += max(api_calls, 0)
            state.rate_limit_status = "available"
            state.rate_limited_until = None
            state.last_error = ""
            state.last_used = self._now()
            self._apply_state_to_account(account_name)
        self._persist_state(account_name)

    def record_failure(self, account_name: str, error: str) -> None:
        """Record a non-rate-limit API failure."""
        with self._lock:
            state = self._state_for(account_name)
            state.failure_count += 1
            state.rate_limit_status = "failed"
            state.last_error = error
            state.last_used = self._now()
            self._apply_state_to_account(account_name)
        self._persist_state(account_name)

    def record_rate_limited(
        self,
        account_name: str,
        *,
        reset_at: datetime | None = None,
        cooldown: timedelta | None = None,
        error: str = "rate limited",
    ) -> None:
        """Mark an account as rate limited until reset_at or a cooldown expires."""
        now = self._now()
        with self._lock:
            state = self._state_for(account_name)
            state.failure_count += 1
            state.rate_limit_status = "rate_limited"
            state.rate_limited_until = reset_at or now + (cooldown or self._default_rate_limit_cooldown)
            state.last_error = error
            state.last_used = now
            self._apply_state_to_account(account_name)
        self._persist_state(account_name)

    def record_http_result(
        self,
        account_name: str,
        status_code: int,
        *,
        api_calls: int = 1,
        reset_at: datetime | None = None,
    ) -> None:
        """Update account state from an HTTP response status code."""
        if status_code == 429:
            self.record_rate_limited(account_name, reset_at=reset_at)
        elif status_code >= 500:
            self.record_failure(account_name, f"HTTP {status_code}")
        else:
            self.record_success(account_name, api_calls=api_calls)

    def mark_available(self, account_name: str) -> None:
        """Clear failure and rate-limit status for an account."""
        with self._lock:
            state = self._state_for(account_name)
            state.rate_limit_status = "available"
            state.rate_limited_until = None
            state.last_error = ""
            self._apply_state_to_account(account_name)
        self._persist_state(account_name)

    def snapshot(self) -> list[AccountRuntimeState]:
        """Return current account runtime state sorted by account name."""
        now = self._now()
        with self._lock:
            for state in self._states.values():
                state.mark_available_if_cooldown_expired(now)
            for name in self._states:
                self._apply_state_to_account(name)
            for name in self._states:
                self._persist_state(name)
            return [self._states[name] for name in sorted(self._states)]

    def available_account_names(
        self,
        assigned_account_names: Sequence[str] | None = None,
    ) -> list[str]:
        """Return eligible account names that are currently selectable."""
        now = self._now()
        with self._lock:
            names: list[str] = []
            for account in self._eligible_accounts(assigned_account_names):
                state = self._states[account.name]
                state.mark_available_if_cooldown_expired(now)
                if not state.is_rate_limited(now):
                    names.append(account.name)
            return names

    def _eligible_accounts(
        self,
        assigned_account_names: Sequence[str] | None,
    ) -> list[OnshapeAccount]:
        assigned = set(assigned_account_names or [])
        accounts = [
            account
            for account in self._accounts.values()
            if account.enabled and (not assigned or account.name in assigned)
        ]
        return sorted(accounts, key=lambda account: account.name)

    def _selection_key(self, account: OnshapeAccount) -> tuple[int, int, datetime, str]:
        state = self._states[account.name]
        last_used = state.last_used or datetime.min.replace(tzinfo=timezone.utc)
        return (state.api_usage, state.failure_count, last_used, account.name)

    def _next_available_at(self, accounts: Sequence[OnshapeAccount]) -> datetime | None:
        reset_times = [
            self._states[account.name].rate_limited_until
            for account in accounts
            if self._states[account.name].rate_limited_until is not None
        ]
        if not reset_times:
            return None
        return min(reset_times)

    def _load_state(self, account: OnshapeAccount) -> AccountRuntimeState:
        state = AccountRuntimeState.from_account(account)
        if self._database is None:
            return state
        payload = self._database.get_state(self._state_key(account.name))
        if not payload:
            return state
        try:
            stored = AccountRuntimeState.from_dict(json.loads(payload))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return state
        if stored.name != account.name:
            return state
        return stored

    def _persist_state(self, account_name: str) -> None:
        if self._database is None:
            return
        payload = json.dumps(self._states[account_name].to_dict(), sort_keys=True)
        self._database.set_state(self._state_key(account_name), payload)

    def _apply_state_to_account(self, account_name: str) -> None:
        account = self._accounts[account_name]
        state = self._states[account_name]
        account.api_usage = state.api_usage
        account.failure_count = state.failure_count
        account.rate_limit_status = state.rate_limit_status
        account.last_used = state.last_used
        account.rate_limited_until = state.rate_limited_until
        account.last_error = state.last_error

    def _sync_accounts_from_state(self) -> None:
        for name in self._states:
            self._apply_state_to_account(name)

    def _state_for(self, account_name: str) -> AccountRuntimeState:
        try:
            return self._states[account_name]
        except KeyError as exc:
            raise KeyError(f"Unknown Onshape account: {account_name}") from exc

    def _state_key(self, account_name: str) -> str:
        return f"{ACCOUNT_STATE_PREFIX}{account_name}"

    def _now(self) -> datetime:
        now = self._now_fn()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def serialize_dt(value: datetime | None) -> str | None:
    """Serialize a datetime for JSON state."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def parse_dt(value: Any) -> datetime | None:
    """Parse an optional datetime from JSON state."""
    if not value:
        return None
    if not isinstance(value, str):
        raise ValueError("datetime value must be a string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
