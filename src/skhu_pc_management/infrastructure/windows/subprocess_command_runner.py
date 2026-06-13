from __future__ import annotations

import subprocess
from typing import Sequence


class SubprocessCommandRunner:
    def run(self, command: Sequence[str]) -> str:
        completed = subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
        return completed.stdout.strip()
