"""Shared retry policy helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any


DEFAULT_RETRY_HTTP_STATUSES = (429, 500, 502, 503, 504)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Shared retry and exponential backoff settings."""

    max_attempts: int = 4
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 60.0
    retry_http_statuses: tuple[int, ...] = field(default_factory=lambda: DEFAULT_RETRY_HTTP_STATUSES)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_base_seconds <= 0:
            raise ValueError("backoff_base_seconds must be greater than 0")
        if self.backoff_max_seconds <= 0:
            raise ValueError("backoff_max_seconds must be greater than 0")

    def delay_seconds_for_attempt(self, attempt_index: int) -> float:
        """Return capped delay for a zero-based attempt index."""
        return min(
            self.backoff_base_seconds * (2 ** max(attempt_index, 0)),
            self.backoff_max_seconds,
        )

    def delay_for_attempt(self, attempt_index: int) -> float:
        """Compatibility alias for request retry delays."""
        return self.delay_seconds_for_attempt(attempt_index)

    def delay_for_retry(self, retry_count: int) -> timedelta:
        """Return capped delay for a one-based retry count."""
        return timedelta(seconds=self.delay_seconds_for_attempt(max(retry_count - 1, 0)))

    def is_retryable_http_status(self, status_code: int) -> bool:
        """Return True when an HTTP status should be retried."""
        return status_code in self.retry_http_statuses


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """The result of evaluating whether an operation should retry."""

    should_retry: bool
    delay_seconds: float = 0.0
    reason: str = ""


def retry_decision(
    *,
    attempt_index: int,
    max_attempts: int,
    policy: RetryPolicy,
    status_code: int | None = None,
    exception: BaseException | None = None,
) -> RetryDecision:
    """Return retry decision for a failed attempt."""
    if attempt_index >= max_attempts - 1:
        return RetryDecision(False, reason="max attempts reached")
    if status_code is not None and policy.is_retryable_http_status(status_code):
        return RetryDecision(
            True,
            delay_seconds=policy.delay_seconds_for_attempt(attempt_index),
            reason=f"HTTP {status_code}",
        )
    if exception is not None and is_transient_exception(exception):
        return RetryDecision(
            True,
            delay_seconds=policy.delay_seconds_for_attempt(attempt_index),
            reason=type(exception).__name__,
        )
    return RetryDecision(False, reason="not retryable")


def is_transient_exception(exception: BaseException) -> bool:
    """Best-effort transient network exception classifier."""
    name = type(exception).__name__.lower()
    return any(token in name for token in ("timeout", "connection", "temporar"))


def retry_statuses_from_config(values: list[int] | tuple[int, ...] | None) -> tuple[int, ...]:
    """Normalize retry HTTP statuses from config."""
    if not values:
        return DEFAULT_RETRY_HTTP_STATUSES
    return tuple(int(value) for value in values)
