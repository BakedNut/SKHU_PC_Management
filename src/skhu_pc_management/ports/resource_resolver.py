from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ResourceResolver(Protocol):
    def resolve(self, relative_path: str) -> Path:
        """Resolve a packaged resource path."""
