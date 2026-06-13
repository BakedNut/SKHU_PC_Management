from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MemoryModuleInfo:
    slot: str
    capacity_gb: float | None = None
    memory_type: str = "Unknown"
    speed_mhz: int | None = None


@dataclass(frozen=True)
class DiskInfo:
    model: str = "Unknown"
    size_gb: float | None = None
    disk_type: str = "Unknown"
    name: str = ""
    total_gb: float | None = None
    free_gb: float | None = None


@dataclass(frozen=True)
class PcInfo:
    computer_name: str
    user_name: str
    os_name: str
    cpu_name: str
    memory_gb: float | None = None
    windows_build: str | None = None
    windows_architecture: str | None = None
    windows_release: str | None = None
    memory_modules: list[MemoryModuleInfo] = field(default_factory=list)
    memory_type: str = "Unknown"
    memory_speed_mhz: int | None = None
    gpu_names: list[str] = field(default_factory=list)
    disks: list[DiskInfo] = field(default_factory=list)
    tpm_installed: bool | None = None
    tpm_version: str | None = None
    secure_boot_enabled: bool | None = None
    secure_boot_status: str = "Unknown"
    boot_mode: str = "Unknown"
