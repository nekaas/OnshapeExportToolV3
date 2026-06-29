"""Credential handling helpers."""

from __future__ import annotations

import os


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask a secret for logs and UI display."""
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible)}"


def get_secret_from_env(name: str) -> str | None:
    """Read a secret from the environment."""
    return os.getenv(name)
