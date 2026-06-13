from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiskInfo:
    name: str
    total_gb: float
    free_gb: float


@dataclass(frozen=True)
class PcInfo:
    computer_name: str
    user_name: str
    os_name: str
    cpu_name: str
    memory_gb: float
    disks: list[DiskInfo] = field(default_factory=list)
