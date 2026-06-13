from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.pc.models import PcInfo
from skhu_pc_management.ports.pc_info_reader import PcInfoReader


@dataclass(frozen=True)
class LoadPcInfo:
    pc_info_reader: PcInfoReader

    def execute(self) -> PcInfo:
        return self.pc_info_reader.read()


LoadPcInfoUseCase = LoadPcInfo
