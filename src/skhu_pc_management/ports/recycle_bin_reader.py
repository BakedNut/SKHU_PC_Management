from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import RecycleBinStatus


class RecycleBinReader(Protocol):
    def read_status(self) -> RecycleBinStatus:
        """Read recycle bin status without emptying it."""
