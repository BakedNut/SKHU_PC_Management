from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence


class ProcessLauncher(Protocol):
    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        """Launch a process."""
