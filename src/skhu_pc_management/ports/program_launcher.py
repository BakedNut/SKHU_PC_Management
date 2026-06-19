from __future__ import annotations

from typing import Protocol


class ProgramLauncher(Protocol):
    def launch_program(self, program_id: str) -> bool:
        """Launch a known program by id."""
