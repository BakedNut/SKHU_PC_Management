from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Sequence


class WindowsProcessLauncher:
    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        subprocess.Popen([str(executable), *args], shell=False)
