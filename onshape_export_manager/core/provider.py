"""Unified credential provider protocol.

Defines the common interface that both :class:`ApiPool` (flat accounts) and
:class:`CredentialPool` (hierarchical organizations) satisfy.  New code should
accept a ``CredentialProvider`` rather than coupling to a specific
implementation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CredentialProvider(Protocol):
    """Protocol for credential selection and health tracking.

    Both ``ApiPool`` and ``CredentialPool`` satisfy this interface, allowing
    the export engine and worker to operate against either flat accounts or
    hierarchical organizations without code changes.
    """

    def lease(self, candidates: Any = None) -> Any:
        """Select the best available credential for a unit of work."""
        ...

    def record_success(self, identifier: str, **kwargs: Any) -> None:
        """Record a successful API call for the given credential."""
        ...

    def record_failure(self, identifier: str, error: str) -> None:
        """Record a non-rate-limit failure for the given credential."""
        ...

    def record_rate_limited(self, identifier: str, **kwargs: Any) -> None:
        """Mark a credential as rate-limited (429 response)."""
        ...

    def snapshot(self) -> list[Any]:
        """Return current runtime state for all credentials."""
        ...
