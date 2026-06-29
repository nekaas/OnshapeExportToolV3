"""Optional Bambu Studio integration boundary.

The existing proof-of-concept Bambu workflow will be moved here during the
Bambu integration stage without changing its behavior.
"""

from __future__ import annotations

import re


def safe_name(name: str) -> str:
    """Strip illegal filename characters and spaces for slicer-safe paths."""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


class BambuStudioRunner:
    """Runs Bambu Studio CLI workflows for compatible export profiles."""

    def create_project(self) -> None:
        raise NotImplementedError("Bambu Studio integration is implemented in Stage 14.")
