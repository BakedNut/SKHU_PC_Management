from __future__ import annotations

from typing import Protocol


class OfficeLauncher(Protocol):
    def launch_excel(self) -> str:
        """Launch Excel and return the launched executable or command description."""
