"""Plugin contracts for future expansion."""

from __future__ import annotations

from typing import Protocol


class Plugin(Protocol):
    """Minimal protocol every future plugin must implement."""

    name: str
    version: str

    def activate(self) -> None:
        """Register plugin hooks."""

    def deactivate(self) -> None:
        """Unregister plugin hooks."""
