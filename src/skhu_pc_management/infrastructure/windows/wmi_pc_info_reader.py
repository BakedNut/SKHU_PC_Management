from __future__ import annotations

import getpass
import socket
from dataclasses import dataclass
from typing import Any

from skhu_pc_management.domain.pc.models import DiskInfo, MemoryModuleInfo, PcInfo
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class WmiPcInfoReader:
    registry: Registry | None = None
    command_runner: CommandRunner | None = None

    def read(self) -> PcInfo:
        os_info = self._get_windows_version_info()
        memory_total_gb, memory_type, memory_speed_mhz, memory_modules = self._get_memory_info()
        tpm_installed, tpm_version = self._get_tpm_info()
        secure_boot_enabled, secure_boot_status = self._get_secure_boot_info()

        return PcInfo(
            computer_name=self._get_computer_name(),
            user_name=self._get_user_name(),
            os_name=os_info["caption"],
            windows_build=os_info["build"],
            windows_architecture=os_info["architecture"],
            windows_release=os_info["release"],
            cpu_name=self._get_first_wmi_value("Win32_Processor", "Name"),
            memory_gb=memory_total_gb,
            memory_modules=memory_modules,
            memory_type=memory_type,
            memory_speed_mhz=memory_speed_mhz,
            gpu_names=self._get_gpu_names(),
            disks=self._get_disks(),
            tpm_installed=tpm_installed,
            tpm_version=tpm_version,
            secure_boot_enabled=secure_boot_enabled,
            secure_boot_status=secure_boot_status,
            boot_mode=self._get_boot_mode(),
        )

    @staticmethod
    def _get_computer_name() -> str:
        return socket.gethostname() or "Unknown"

    @staticmethod
    def _get_user_name() -> str:
        try:
            return getpass.getuser() or "Unknown"
        except Exception:
            return "Unknown"

    def _get_windows_version_info(self) -> dict[str, str | None]:
        os_item = self._first_wmi_item("Win32_OperatingSystem")
        caption = _to_string(_get_value(os_item, "Caption")) or "Unknown"
        build = _to_string(_get_value(os_item, "BuildNumber"))
        architecture = _to_string(_get_value(os_item, "OSArchitecture"))
        release = _windows_release(caption, build)
        return {
            "caption": caption,
            "build": build,
            "architecture": architecture,
            "release": release,
        }

    def _get_first_wmi_value(self, wmi_class: str, property_name: str) -> str:
        value = _get_value(self._first_wmi_item(wmi_class), property_name)
        return _to_string(value) or "Unknown"

    def _get_memory_info(self) -> tuple[float | None, str, int | None, list[MemoryModuleInfo]]:
        modules: list[MemoryModuleInfo] = []
        total_bytes = 0
        max_speed: int | None = None
        common_type = "Unknown"

        for index, item in enumerate(self._wmi_items("Win32_PhysicalMemory"), start=1):
            capacity_bytes = _to_int(_get_value(item, "Capacity"))
            speed = _to_int(_get_value(item, "Speed"))
            memory_type = _memory_type_from_code(
                _to_int(_get_value(item, "SMBIOSMemoryType"))
                or _to_int(_get_value(item, "MemoryType"))
                or 0
            )

            if capacity_bytes:
                total_bytes += capacity_bytes
            if speed is not None:
                max_speed = speed if max_speed is None else max(max_speed, speed)
            if common_type == "Unknown" and memory_type != "Unknown":
                common_type = memory_type

            modules.append(
                MemoryModuleInfo(
                    slot=f"Slot {index}",
                    capacity_gb=_bytes_to_gb(capacity_bytes),
                    memory_type=memory_type,
                    speed_mhz=speed,
                )
            )

        return _bytes_to_gb(total_bytes), common_type, max_speed, modules

    def _get_gpu_names(self) -> list[str]:
        gpu_names: list[str] = []
        for item in self._wmi_items("Win32_VideoController"):
            name = _to_string(_get_value(item, "Name")) or "Unknown GPU"
            adapter_compatibility = _to_string(_get_value(item, "AdapterCompatibility")) or ""
            if _is_virtual_gpu(name, adapter_compatibility):
                continue
            if name not in gpu_names:
                gpu_names.append(name)
        return gpu_names

    def _get_disks(self) -> list[DiskInfo]:
        physical_disks = self._get_physical_disks()
        disks: list[DiskInfo] = []
        try:
            for item in self._wmi_items("Win32_DiskDrive"):
                disks.append(_build_disk_info(item, physical_disks))

            if not disks and physical_disks:
                for disk in physical_disks:
                    disks.append(_build_disk_info_from_physical(disk))
        except Exception:
            disks.append(
                DiskInfo(
                    model="디스크 정보를 가져올 수 없습니다",
                    disk_type="Unknown",
                    display_type="알 수 없음",
                )
            )
        return disks

    def _get_disk_type(self, disk: Any) -> str:
        return _infer_disk_type(disk, None)

    def _get_physical_disks(self) -> list["_PhysicalDiskMetadata"]:
        disks: list[_PhysicalDiskMetadata] = []
        for item in self._wmi_items("MSFT_PhysicalDisk", r"root\Microsoft\Windows\Storage"):
            disks.append(
                _PhysicalDiskMetadata(
                    friendly_name=_to_string(_get_value(item, "FriendlyName")) or "",
                    serial_number=_normalize_disk_token(_to_string(_get_value(item, "SerialNumber"))),
                    media_type=_map_physical_media_type(_get_value(item, "MediaType")),
                    bus_type=_map_bus_type(_get_value(item, "BusType")),
                    size_bytes=_to_int(_get_value(item, "Size")) or 0,
                )
            )
        return disks

    def _get_tpm_info(self) -> tuple[bool | None, str | None]:
        item = self._first_wmi_item("Win32_Tpm", namespace=r"root\CIMV2\Security\MicrosoftTpm")
        if item is not None:
            version = (_to_string(_get_value(item, "SpecVersion")) or "Unknown").split(",")[0].strip()
            return True, version

        if self.registry is None:
            return None, None

        try:
            start = self.registry.read_value(
                "HKEY_LOCAL_MACHINE",
                r"SYSTEM\CurrentControlSet\Services\TPM",
                "Start",
            )
        except Exception:
            return None, None

        if start is None:
            return False, "Not installed"
        try:
            return True, "2.0" if int(start) != 3 else "2.0 (disabled)"
        except (TypeError, ValueError):
            return True, "Unknown"

    def _get_secure_boot_info(self) -> tuple[bool | None, str]:
        if self.registry is None:
            return None, "Unknown"

        try:
            value = self.registry.read_value(
                "HKEY_LOCAL_MACHINE",
                r"SYSTEM\CurrentControlSet\Control\SecureBoot\State",
                "UEFISecureBootEnabled",
            )
        except Exception:
            return None, "Unknown"

        if value is None:
            return None, "Unknown"

        enabled = _to_int(value) == 1
        return enabled, "Enabled" if enabled else "Disabled"

    def _get_boot_mode(self) -> str:
        registry_mode = self._get_boot_mode_from_registry()
        if registry_mode != "Unknown":
            return registry_mode

        if self.command_runner is None:
            return "Unknown"

        try:
            output = self.command_runner.run(("bcdedit", "/enum", "{current}"))
        except Exception:
            return "Unknown"

        output_lower = output.lower()
        if "winload.efi" in output_lower:
            return "UEFI"
        if "winload.exe" in output_lower:
            return "Legacy/BIOS"
        return "Unknown"

    def _get_boot_mode_from_registry(self) -> str:
        if self.registry is None:
            return "Unknown"
        try:
            value = self.registry.read_value(
                "HKEY_LOCAL_MACHINE",
                r"System\CurrentControlSet\Control",
                "PEFirmwareType",
            )
        except Exception:
            return "Unknown"

        value_text = _to_string(value)
        if value_text == "2":
            return "UEFI"
        if value_text == "1":
            return "Legacy/BIOS"
        return "Unknown"

    def _first_wmi_item(self, wmi_class: str, namespace: str | None = None) -> Any | None:
        for item in self._wmi_items(wmi_class, namespace):
            return item
        return None

    @staticmethod
    def _wmi_items(wmi_class: str, namespace: str | None = None) -> list[Any]:
        try:
            import wmi

            client = wmi.WMI(namespace=namespace) if namespace else wmi.WMI()
            query_method = getattr(client, wmi_class)
            return list(query_method())
        except Exception:
            return []


@dataclass(frozen=True)
class _PhysicalDiskMetadata:
    friendly_name: str = ""
    serial_number: str = ""
    media_type: str = "Unknown"
    bus_type: str = "Unknown"
    size_bytes: int = 0


def _build_disk_info(disk: Any, physical_disks: list[_PhysicalDiskMetadata]) -> DiskInfo:
    model = _to_string(_get_value(disk, "Model")) or "Unknown"
    serial = _normalize_disk_token(_to_string(_get_value(disk, "SerialNumber")))
    size_bytes = _to_int(_get_value(disk, "Size")) or 0
    matched = _find_best_physical_disk(physical_disks, model, serial, size_bytes)
    disk_type = _infer_disk_type(disk, matched.media_type if matched else None)
    bus_type = _infer_bus_type(disk, model, matched.bus_type if matched else None)
    actual_size_gib = _bytes_to_gb(size_bytes)

    return DiskInfo(
        model=model,
        size_gb=actual_size_gib,
        actual_size_gib=actual_size_gib,
        rated_size=_format_rated_size(size_bytes),
        disk_type=disk_type,
        bus_type=bus_type,
        display_type=_compose_disk_type_display(disk_type, bus_type),
        serial_number=serial or None,
        raw_size_bytes=size_bytes or None,
    )


def _build_disk_info_from_physical(disk: _PhysicalDiskMetadata) -> DiskInfo:
    actual_size_gib = _bytes_to_gb(disk.size_bytes)
    disk_type = disk.media_type or "Unknown"
    bus_type = disk.bus_type or "Unknown"
    return DiskInfo(
        model=disk.friendly_name or "Unknown",
        size_gb=actual_size_gib,
        actual_size_gib=actual_size_gib,
        rated_size=_format_rated_size(disk.size_bytes),
        disk_type=disk_type,
        bus_type=bus_type,
        display_type=_compose_disk_type_display(disk_type, bus_type),
        serial_number=disk.serial_number or None,
        raw_size_bytes=disk.size_bytes or None,
    )


def _find_best_physical_disk(
    physical_disks: list[_PhysicalDiskMetadata],
    model: str,
    serial: str,
    size_bytes: int,
) -> _PhysicalDiskMetadata | None:
    if not physical_disks:
        return None

    if serial:
        for disk in physical_disks:
            if disk.serial_number == serial:
                return disk

    normalized_model = _normalize_disk_token(model)
    if normalized_model:
        for disk in physical_disks:
            normalized_name = _normalize_disk_token(disk.friendly_name)
            if normalized_name and (normalized_name in normalized_model or normalized_model in normalized_name):
                return disk

    if size_bytes > 0:
        tolerance = 4 * 1024**3
        candidates = sorted(physical_disks, key=lambda disk: abs(disk.size_bytes - size_bytes))
        if candidates and abs(candidates[0].size_bytes - size_bytes) <= tolerance:
            return candidates[0]

    return None


def _infer_disk_type(disk: Any, physical_disk_type: str | None) -> str:
    if physical_disk_type and physical_disk_type != "Unknown":
        return physical_disk_type

    rotation_rate = _to_int(_get_value(disk, "MediaRotationRate"))
    if rotation_rate is not None:
        return "SSD" if rotation_rate == 0 else "HDD"

    media_type = (_to_string(_get_value(disk, "MediaType")) or "").lower()
    model = (_to_string(_get_value(disk, "Model")) or "").lower()
    text = f"{media_type} {model}"
    if "nvme" in text or "ssd" in text or "solid state" in text:
        return "SSD"
    if "hdd" in text or "hard disk" in text:
        return "HDD"
    return "Unknown"


def _infer_bus_type(disk: Any, model: str, physical_bus_type: str | None) -> str:
    if physical_bus_type and physical_bus_type != "Unknown":
        return physical_bus_type

    interface_type = _to_string(_get_value(disk, "InterfaceType"))
    if interface_type:
        normalized = interface_type.upper()
        if normalized in {"IDE", "SCSI", "ATA"}:
            return "NVMe" if "nvme" in model.lower() else "SATA"
        if normalized == "USB":
            return "USB"

    model_lower = model.lower()
    if "nvme" in model_lower:
        return "NVMe"
    if "sata" in model_lower:
        return "SATA"
    return "Unknown"


def _compose_disk_type_display(disk_type: str, bus_type: str | None) -> str:
    normalized_type = disk_type or "Unknown"
    if normalized_type == "Unknown":
        normalized_type = "알 수 없음"
    if not bus_type or bus_type == "Unknown":
        return normalized_type
    return f"{normalized_type} ({bus_type})"


def _format_rated_size(size_bytes: int | None) -> str | None:
    if not size_bytes:
        return None

    actual_gib = size_bytes // (1024**3)
    if actual_gib <= 1:
        return "1GB"

    rated_gib = 1
    while rated_gib < actual_gib:
        rated_gib <<= 1

    if rated_gib >= 1024 and rated_gib % 1024 == 0:
        return f"{rated_gib // 1024}TB"
    return f"{rated_gib}GB"


def _normalize_disk_token(value: str | None) -> str:
    if not value:
        return ""
    return "".join(char for char in value if char.isalnum()).upper()


def _map_physical_media_type(value: object) -> str:
    code = _to_int(value)
    if code is not None:
        return {
            3: "HDD",
            4: "SSD",
            5: "SCM",
        }.get(code, "Unknown")

    text = (_to_string(value) or "").strip().lower()
    if text in {"hdd", "hard disk drive"}:
        return "HDD"
    if text in {"ssd", "solid state drive"}:
        return "SSD"
    if text == "scm":
        return "SCM"
    return "Unknown"


def _map_bus_type(value: object) -> str:
    code = _to_int(value)
    if code is not None:
        return {
            3: "ATA",
            4: "SATA",
            7: "USB",
            8: "RAID",
            9: "iSCSI",
            10: "SAS",
            11: "SATA",
            12: "SD",
            13: "MMC",
            14: "Virtual",
            15: "File Backed Virtual",
            16: "Spaces",
            17: "NVMe",
        }.get(code, "Unknown")

    text = (_to_string(value) or "").strip()
    if not text:
        return "Unknown"
    lower = text.lower()
    return {
        "nvme": "NVMe",
        "sata": "SATA",
        "ata": "ATA",
        "usb": "USB",
        "raid": "RAID",
        "sas": "SAS",
    }.get(lower, text)


def _get_value(item: Any | None, property_name: str) -> Any | None:
    if item is None:
        return None
    try:
        return getattr(item, property_name)
    except Exception:
        try:
            return item[property_name]
        except Exception:
            return None


def _to_string(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: Any | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bytes_to_gb(value: int | None) -> float | None:
    if not value:
        return None
    return round(value / (1024**3), 2)


def _windows_release(caption: str, build_text: str | None) -> str | None:
    build = _to_int(build_text)
    if build is None:
        return None

    if "windows 11" in caption.lower():
        if build >= 26200:
            return "25H2"
        if build >= 26100:
            return "24H2"
        if build >= 22631:
            return "23H2"
        if build >= 22621:
            return "22H2"
        if build >= 22000:
            return "21H2"

    if "windows 10" in caption.lower():
        if build >= 19045:
            return "22H2"
        if build >= 19044:
            return "21H2"
        if build >= 19043:
            return "21H1"
        if build >= 19042:
            return "20H2"

    return None


def _memory_type_from_code(code: int) -> str:
    return {
        20: "DDR",
        21: "DDR2",
        24: "DDR3",
        26: "DDR4",
        29: "LPDDR3",
        30: "LPDDR4",
        34: "DDR5",
        35: "LPDDR5",
    }.get(code, "Unknown")


def _is_virtual_gpu(name: str, adapter_compatibility: str) -> bool:
    lower_name = name.lower()
    if any(token in lower_name for token in ("parsec", "virtual", "remote", "basic render driver", "citrix", "vmware", "hyper-v", "radmin")):
        return True

    compatibility = adapter_compatibility.lower()
    return (
        "microsoft corporation" in compatibility
        and "nvidia" not in lower_name
        and "amd" not in lower_name
        and "intel" not in lower_name
    )
