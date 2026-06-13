from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PcInfoViewModel:
    load_pc_info_use_case: Any
    status_message: str = "PC 정보를 불러오지 않았습니다."
    rows: list[tuple[str, str]] = field(default_factory=list)
    is_busy: bool = False

    def refresh(self) -> None:
        self.is_busy = True
        self.status_message = "PC 정보를 불러오는 중입니다..."
        try:
            pc_info = self.load_pc_info_use_case.execute()
            self.rows = [
                ("PC 이름", pc_info.computer_name),
                ("사용자", pc_info.user_name),
                ("Windows", _join_non_empty(pc_info.os_name, pc_info.windows_release, pc_info.windows_build, pc_info.windows_architecture)),
                ("CPU", pc_info.cpu_name),
                ("RAM", _format_ram(pc_info)),
                ("GPU", "\n".join(pc_info.gpu_names) if pc_info.gpu_names else "Unknown"),
                ("디스크", _format_disks(pc_info.disks)),
                ("TPM", _format_tpm(pc_info)),
                ("Secure Boot", pc_info.secure_boot_status),
                ("Boot Mode", pc_info.boot_mode),
            ]
            self.status_message = "PC 정보를 불러왔습니다."
        except Exception as exc:
            self.rows = []
            self.status_message = f"PC 정보 조회 실패: {exc}"
        finally:
            self.is_busy = False


def _join_non_empty(*values: object | None) -> str:
    return " ".join(str(value) for value in values if value not in (None, ""))


def _format_ram(pc_info: Any) -> str:
    base = "Unknown" if pc_info.memory_gb is None else f"{pc_info.memory_gb:g} GB"
    details = []
    if pc_info.memory_type != "Unknown":
        details.append(pc_info.memory_type)
    if pc_info.memory_speed_mhz:
        details.append(f"{pc_info.memory_speed_mhz} MHz")
    if pc_info.memory_modules:
        details.append(f"{len(pc_info.memory_modules)} slots")
    return base if not details else f"{base} ({', '.join(details)})"


def _format_disks(disks: list[Any]) -> str:
    if not disks:
        return "Unknown"
    lines = []
    for disk in disks:
        size = "N/A" if disk.size_gb is None else f"{disk.size_gb:g} GB"
        lines.append(f"{disk.model} / {size} / {disk.disk_type}")
    return "\n".join(lines)


def _format_tpm(pc_info: Any) -> str:
    if pc_info.tpm_installed is None:
        return "Unknown"
    status = "Installed" if pc_info.tpm_installed else "Not installed"
    return status if not pc_info.tpm_version else f"{status} ({pc_info.tpm_version})"
