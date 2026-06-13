from __future__ import annotations

import sys
from pathlib import Path


class PyInstallerResourceResolver:
    def resolve(self, relative_path: str) -> Path:
        base_path = Path(getattr(sys, "_MEIPASS", Path.cwd()))
        return base_path / relative_path
