from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PcInfoViewModel:
    load_pc_info_use_case: Any
    status_message: str = "PC 정보를 불러오지 않았습니다."
    rows: list[tuple[str, str]] = field(default_factory=list)
    pc_name: str = "알 수 없음"
    user_name: str = "알 수 없음"
    windows_version: str = "알 수 없음"
    windows_version_detail: str = "알 수 없음"
    cpu: str = "알 수 없음"
    ram: str = "알 수 없음"
    gpu: str = "알 수 없음"
    disks: list[tuple[str, str, str, str]] = field(default_factory=list)
    tpm_version: str = "알 수 없음"
    tpm_status_text: str = "알 수 없음"
    secure_boot_status_text: str = "알 수 없음"
    boot_mode: str = "알 수 없음"
    is_busy: bool = False

    def refresh(self) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "PC 정보를 불러오는 중입니다..."
        try:
            pc_info = self.load_pc_info_use_case.execute()
            self.pc_name = _display_text(pc_info.computer_name)
            self.user_name = _display_text(pc_info.user_name)
            self.windows_version = _display_text(_join_non_empty(pc_info.os_name, pc_info.windows_release))
            self.windows_version_detail = _display_text(
                _join_non_empty(pc_info.windows_build, pc_info.windows_architecture)
            )
            self.cpu = _display_text(pc_info.cpu_name)
            self.ram = _format_ram(pc_info)
            self.gpu = "\n".join(pc_info.gpu_names) if pc_info.gpu_names else "알 수 없음"
            self.disks = _disk_rows(pc_info.disks)
            self.tpm_version = _display_text(pc_info.tpm_version)
            self.tpm_status_text = _format_tpm(pc_info)
            self.secure_boot_status_text = _display_text(pc_info.secure_boot_status)
            self.boot_mode = _display_text(pc_info.boot_mode)
            self.rows = [
                ("PC 이름", self.pc_name),
                ("사용자", self.user_name),
                ("Windows", _display_windows_summary(self.windows_version, self.windows_version_detail)),
                ("CPU", self.cpu),
                ("RAM", self.ram),
                ("GPU", self.gpu),
                ("디스크", _format_disks(pc_info.disks)),
                ("TPM", self.tpm_status_text),
                ("Secure Boot", self.secure_boot_status_text),
                ("Boot Mode", self.boot_mode),
            ]
            self.status_message = "PC 정보를 불러왔습니다."
        except Exception as exc:
            self.rows = []
            self.status_message = f"PC 정보 조회 실패: {exc}"
        finally:
            self.is_busy = False


def _join_non_empty(*values: object | None) -> str:
    return " ".join(str(value) for value in values if value not in (None, ""))


def _display_text(value: object | None) -> str:
    if value in (None, "", "Unknown"):
        return "알 수 없음"
    if value == "Installed":
        return "설치됨"
    if value == "Not installed":
        return "설치되지 않음"
    return str(value)


def _format_ram(pc_info: Any) -> str:
    base = "알 수 없음" if pc_info.memory_gb is None else f"{pc_info.memory_gb:g} GB"
    details = []
    if pc_info.memory_type != "Unknown":
        details.append(pc_info.memory_type)
    if pc_info.memory_speed_mhz:
        details.append(f"{pc_info.memory_speed_mhz} MHz")
    if pc_info.memory_modules:
        details.append(f"{len(pc_info.memory_modules)} slots")
    return base if not details else f"{base} ({', '.join(details)})"


def _display_windows_summary(version: str, detail: str) -> str:
    if version == "알 수 없음":
        return version
    if detail == "알 수 없음":
        return version
    return f"{version} {detail}"


def _format_disks(disks: list[Any]) -> str:
    if not disks:
        return "알 수 없음"
    lines = []
    for disk in disks:
        actual_size = getattr(disk, "actual_size_gib", None)
        size = "N/A" if actual_size is None else f"{actual_size:g} GiB"
        rated_size = getattr(disk, "rated_size", None)
        type_text = getattr(disk, "display_type", None) or getattr(disk, "disk_type", "알 수 없음")
        parts = [str(disk.model), size]
        if rated_size:
            parts.append(f"정격 {rated_size}")
        parts.append(_display_text(type_text))
        lines.append(" / ".join(parts))
    return "\n".join(lines)


def _disk_rows(disks: list[Any]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for disk in disks:
        model = _display_text(getattr(disk, "model", None))
        type_text = _display_text(getattr(disk, "display_type", None) or getattr(disk, "disk_type", None))
        rated_size = _display_text(getattr(disk, "rated_size", None))
        actual_size = getattr(disk, "actual_size_gib", None)
        actual_text = "알 수 없음" if actual_size is None else f"{actual_size:g} GiB"
        rows.append((model, type_text, rated_size, actual_text))
    return rows


def _format_tpm(pc_info: Any) -> str:
    if pc_info.tpm_installed is None:
        return "알 수 없음"
    status = "설치됨" if pc_info.tpm_installed else "설치되지 않음"
    return status if not pc_info.tpm_version else f"{status} ({pc_info.tpm_version})"
