from __future__ import annotations

from typing import Protocol


class Clipboard(Protocol):
    def set_text(self, text: str) -> None:
        """Copy text to the clipboard."""
