from __future__ import annotations

from typing import Sequence


class SubprocessCommandRunner:
    def run(self, command: Sequence[str]) -> str:
        raise NotImplementedError(f"Command execution is not implemented yet: {list(command)}")
