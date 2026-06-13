from __future__ import annotations

from skhu_pc_management.domain.pc.models import PcInfo


class WmiPcInfoReader:
    def read(self) -> PcInfo:
        raise NotImplementedError("WMI PC information reading is not implemented yet.")
