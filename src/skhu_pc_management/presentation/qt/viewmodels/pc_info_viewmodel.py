from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
from typing import Any


@dataclass
class PcInfoViewModel:
    load_pc_info_use_case: Any
    open_pc_name_settings_use_case: Any | None = None
    status_message: str = "PC 정보를 불러오지 않았습니다."
    rows: list[tuple[str, str]] = field(default_factory=list)
    pc_name: str = "알 수 없음"
    user_name: str = "알 수 없음"
    windows_version: str = "알 수 없음"
    windows_version_detail: str = "알 수 없음"
    cpu: str = "알 수 없음"
    ram: str = "알 수 없음"
    gpu: str = "알 수 없음"
    gpu_memory: str = "알 수 없음"
    disks: list[tuple[str, str, str, str]] = field(default_factory=list)
    network_adapter: str = "알 수 없음"
    ipv4_address: str = "알 수 없음"
    mac_address: str = "알 수 없음"
    disk_nvme_summary: str = "없음"
    disk_ssd_summary: str = "없음"
    disk_hdd_summary: str = "없음"
    disk_unknown_summary: str = "없음"
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
                _format_windows_detail(
                    pc_info.windows_build,
                    getattr(pc_info, "windows_ubr", None),
                    pc_info.windows_architecture,
                )
            )
            self.cpu = _display_text(pc_info.cpu_name)
            self.ram = _format_ram(pc_info)
            self.gpu = _display_text(getattr(pc_info, "gpu_name", None)) if getattr(pc_info, "gpu_name", None) else (
                "\n".join(pc_info.gpu_names) if pc_info.gpu_names else "알 수 없음"
            )
            self.gpu_memory = _display_text(getattr(pc_info, "gpu_memory", None))
            self.disks = _disk_rows(pc_info.disks)
            self.network_adapter = _format_network_adapter(pc_info)
            self.ipv4_address = _format_network_ip(pc_info)
            self.mac_address = _format_network_mac(pc_info)
            self.disk_nvme_summary = _display_text(getattr(pc_info, "disk_nvme_summary", None)) or "없음"
            self.disk_ssd_summary = _display_text(getattr(pc_info, "disk_ssd_summary", None)) or "없음"
            self.disk_hdd_summary = _display_text(getattr(pc_info, "disk_hdd_summary", None)) or "없음"
            self.disk_unknown_summary = _display_text(getattr(pc_info, "disk_unknown_summary", None)) or "없음"
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
                ("GPU 메모리", self.gpu_memory),
                ("디스크", _format_disks(pc_info.disks)),
                ("네트워크 어댑터", self.network_adapter),
                ("IP 주소", self.ipv4_address),
                ("MAC 주소", self.mac_address),
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

    def open_pc_name_settings(self) -> Any:
        if self.open_pc_name_settings_use_case is None:
            self.status_message = "PC 이름 변경 화면 열기 기능이 구성되지 않았습니다."
            return None
        result = self.open_pc_name_settings_use_case.execute()
        self.status_message = result.message
        return result


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


def _format_windows_detail(build: object | None, ubr: object | None, architecture: object | None) -> str:
    build_text = _clean_text(build)
    ubr_text = _clean_text(ubr)
    architecture_text = _normalize_architecture(_clean_text(architecture))

    version_text = ""
    if build_text and ubr_text:
        version_text = f"{build_text}.{ubr_text}"
    elif build_text:
        version_text = build_text

    if version_text and architecture_text:
        return f"{version_text} ({architecture_text})"
    if version_text:
        return version_text
    return architecture_text or "알 수 없음"


def _clean_text(value: object | None) -> str:
    if value in (None, "", "Unknown"):
        return ""
    return str(value).strip()


def _normalize_architecture(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"64-bit", "64 bit", "x64", "amd64", "64비트"}:
        return "64비트"
    if normalized in {"32-bit", "32 bit", "x86", "32비트"}:
        return "32비트"
    return value


def _format_ram(pc_info: Any) -> str:
    base = "알 수 없음" if pc_info.memory_gb is None else f"{pc_info.memory_gb:g}GB"
    module_summary = _format_memory_modules(getattr(pc_info, "memory_modules", []))
    if module_summary:
        return f"{base} ({len(pc_info.memory_modules)}개: {module_summary})"

    details = []
    if pc_info.memory_type != "Unknown":
        details.append(pc_info.memory_type)
    if pc_info.memory_speed_mhz:
        details.append(f"{pc_info.memory_speed_mhz}MHz")
    return base if not details else f"{base} ({', '.join(details)})"


def _format_memory_modules(modules: list[Any]) -> str:
    groups: Counter[tuple[str, int | None, float | None]] = Counter()
    for module in modules:
        capacity = getattr(module, "capacity_gb", None)
        memory_type = getattr(module, "memory_type", "Unknown")
        speed = getattr(module, "speed_mhz", None)
        if capacity is None:
            continue
        groups[(memory_type if memory_type != "Unknown" else "", speed, capacity)] += 1
    if not groups:
        return ""

    parts: list[str] = []
    for (memory_type, speed, capacity), count in groups.items():
        prefix = memory_type
        if memory_type and speed:
            prefix = f"{memory_type}-{speed}"
        elif speed:
            prefix = f"{speed}MHz"
        capacity_text = f"{capacity:g}GB"
        parts.append(f"{prefix + ' ' if prefix else ''}{capacity_text} x{count}")
    return ", ".join(parts)


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


def _format_network_adapter(pc_info: Any) -> str:
    network_info = getattr(pc_info, "network_info", None)
    if network_info is None:
        return "알 수 없음"
    adapter_name = _clean_text(getattr(network_info, "adapter_name", None))
    adapter_type = _clean_text(getattr(network_info, "adapter_type", None))
    if not adapter_name and not adapter_type:
        return "알 수 없음"
    if adapter_name and adapter_type:
        return f"{adapter_name} ({adapter_type})"
    return adapter_name or adapter_type or "알 수 없음"


def _format_network_ip(pc_info: Any) -> str:
    network_info = getattr(pc_info, "network_info", None)
    if network_info is not None:
        return _display_text(getattr(network_info, "ip_address", None))
    return _display_text(getattr(pc_info, "ipv4_address", None))


def _format_network_mac(pc_info: Any) -> str:
    network_info = getattr(pc_info, "network_info", None)
    if network_info is not None:
        return _display_text(getattr(network_info, "mac_address", None))
    return _display_text(getattr(pc_info, "mac_address", None))


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
