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
    actual_size_gib: float | None = None
    rated_size: str | None = None
    bus_type: str | None = None
    display_type: str = "Unknown"
    serial_number: str | None = None
    raw_size_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.actual_size_gib is None and self.size_gb is not None:
            object.__setattr__(self, "actual_size_gib", self.size_gb)
        if self.size_gb is None and self.actual_size_gib is not None:
            object.__setattr__(self, "size_gb", self.actual_size_gib)
        if self.display_type == "Unknown" and self.disk_type != "Unknown":
            object.__setattr__(self, "display_type", self.disk_type)


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
