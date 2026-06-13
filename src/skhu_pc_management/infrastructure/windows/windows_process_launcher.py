from __future__ import annotations

from pathlib import Path
from typing import Sequence


class WindowsProcessLauncher:
    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        raise NotImplementedError(f"Process launch is not implemented yet: {executable} {list(args)}")
