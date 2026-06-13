from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.pc.models import PcInfo


class PcInfoReader(Protocol):
    def read(self) -> PcInfo:
        """Read current PC information."""
