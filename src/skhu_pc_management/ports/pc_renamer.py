from __future__ import annotations

from typing import Protocol


class PcRenamer(Protocol):
    def rename(self, new_name: str) -> bool:
        """Rename the local PC."""
