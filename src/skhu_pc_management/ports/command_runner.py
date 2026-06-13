from __future__ import annotations

from typing import Protocol, Sequence


class CommandRunner(Protocol):
    def run(self, command: Sequence[str]) -> str:
        """Run a command and return stdout."""
