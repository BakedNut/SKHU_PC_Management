from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from skhu_pc_management.domain.agent.models import AgentReport
from skhu_pc_management.domain.checks.models import CheckResult, InstalledProgramInfo
from skhu_pc_management.domain.network.models import NetworkAdapterInfo
from skhu_pc_management.domain.pc.models import DiskInfo, PcInfo


@dataclass(frozen=True)
class BuildAgentReport:
    def execute(
        self,
        pc_info: PcInfo,
        network_adapters: list[NetworkAdapterInfo] | None = None,
        check_results: list[CheckResult] | None = None,
        installed_programs: list[InstalledProgramInfo] | None = None,
    ) -> AgentReport:
        pc_name = _required_text(pc_info.computer_name, "pcName")
        mac_address = _required_text(pc_info.mac_address, "macAddress")

        return AgentReport(
            pcName=pc_name,
            macAddress=mac_address,
            reportedAt=datetime.now().astimezone(),
            username=_empty_to_none(pc_info.user_name),
            osVersion=_format_os_version(pc_info),
            cpu=_empty_to_none(pc_info.cpu_name),
            ram=_format_ram(pc_info.memory_gb),
            gpu=_format_gpu(pc_info),
            ipAddress=_empty_to_none(pc_info.ipv4_address),
            networkAdapters=[
                _map_network_adapter(adapter)
                for adapter in (network_adapters or [])
            ],
            disks=[
                _map_disk(disk)
                for disk in pc_info.disks
            ],
            checkResults=[
                _map_check_result(result)
                for result in (check_results or [])
            ],
            installedSoftware=[
                _map_installed_program(program)
                for program in (installed_programs or [])
            ],
        )


BuildAgentReportUseCase = BuildAgentReport


def _required_text(value: str | None, field_name: str) -> str:
    text = _empty_to_none(value)

    if text is None:
        raise ValueError(f"{field_name} is required.")

    return text


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _format_os_version(pc_info: PcInfo) -> str | None:
    parts = [
        _empty_to_none(pc_info.os_name),
        _empty_to_none(pc_info.windows_release),
        _empty_to_none(pc_info.windows_build),
        _empty_to_none(pc_info.windows_ubr),
        _empty_to_none(pc_info.windows_architecture),
    ]

    values = [part for part in parts if part]

    if not values:
        return None

    return " / ".join(values)


def _format_ram(memory_gb: float | None) -> str | None:
    if memory_gb is None:
        return None

    return f"{memory_gb:.1f} GB"


def _format_gpu(pc_info: PcInfo) -> str | None:
    if pc_info.gpu_names:
        return ", ".join(pc_info.gpu_names)

    return _empty_to_none(pc_info.gpu_name)


def _map_disk(disk: DiskInfo) -> dict[str, Any]:
    return {
        "model": _empty_to_none(disk.model),
        "diskType": _empty_to_none(disk.display_type)
        or _empty_to_none(disk.disk_type),
        "busType": _empty_to_none(disk.bus_type),
        "totalSizeGb": _float_to_int(disk.total_gb or disk.size_gb),
        "freeSizeGb": _float_to_int(disk.free_gb),
    }


def _map_network_adapter(adapter: NetworkAdapterInfo) -> dict[str, Any]:
    return {
        "name": _empty_to_none(adapter.name),
        "description": _empty_to_none(adapter.description),
        "macAddress": _empty_to_none(adapter.mac_address),
        "ipAddress": _first_or_none(adapter.ip_addresses),
        "subnetMask": _empty_to_none(adapter.subnet_mask),
        "gateway": _empty_to_none(adapter.gateway),
        "dnsServers": list(adapter.dns_servers),
        "dhcpEnabled": adapter.is_dhcp_enabled,
        "enabled": adapter.is_enabled,
    }


def _map_check_result(result: CheckResult) -> dict[str, Any]:
    return {
        "checkGroup": _map_check_group(result.category),
        "checkKey": _empty_to_none(result.check_id) or _empty_to_none(result.name),
        "displayName": _empty_to_none(result.label) or _empty_to_none(result.name),
        "status": _map_check_status(result.status, result.passed),
        "detail": _empty_to_none(result.detail)
        or _empty_to_none(result.message),
    }


def _map_installed_program(program: InstalledProgramInfo) -> dict[str, Any]:
    return {
        "name": _empty_to_none(program.name),
        "version": _empty_to_none(program.version),
        "vendor": None,
        "installPath": _empty_to_none(program.path),
    }


def _map_check_group(category: str | None) -> str:
    match _empty_to_none(category):
        case "program" | "office":
            return "SETTING_CHECK"
        case "power" | "scheduled_task" | "recycle_bin" | "browser_history":
            return "SETTING_CHECK"
        case _:
            return "PC_CHECK"


def _map_check_status(status: str | None, passed: bool) -> str:
    normalized = (_empty_to_none(status) or "").lower()

    if normalized == "ok" or passed:
        return "OK"

    if normalized == "warning":
        return "WARN"

    if normalized == "error":
        return "FAIL"

    return "UNKNOWN"


def _first_or_none(values: tuple[str, ...]) -> str | None:
    if not values:
        return None

    return _empty_to_none(values[0])


def _float_to_int(value: float | None) -> int | None:
    if value is None:
        return None

    return int(round(value))