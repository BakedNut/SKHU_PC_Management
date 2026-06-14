from __future__ import annotations

from typing import Protocol


class LatestVersionProvider(Protocol):
    def get_latest_version(self, program_id: str) -> str | None:
        """Return latest known version for a program, or None when it cannot be checked."""
