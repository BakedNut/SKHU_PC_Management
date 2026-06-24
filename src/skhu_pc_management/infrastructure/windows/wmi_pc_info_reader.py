from __future__ import annotations

import json
import socket
from dataclasses import dataclass
import getpass
import re
from typing import Any

from skhu_pc_management.domain.pc.models import DiskInfo, MemoryModuleInfo, PcInfo, PcNetworkInfo
from skhu_pc_management.infrastructure.windows.dxgi_gpu_reader import read_dxgi_gpu_info
from skhu_pc_management.infrastructure.windows.network_identity_reader import normalize_mac_address
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
        gpu_name, gpu_memory, gpu_names = self._get_gpu_info()
        disks = self._get_disks()
        disk_summaries = _disk_type_summaries(disks)
        network_info = self._get_active_network_info()

        return PcInfo(
            computer_name=self._get_computer_name(),
            user_name=self._get_user_name(),
            os_name=os_info["caption"],
            windows_build=os_info["build"],
            windows_ubr=os_info["ubr"],
            windows_architecture=os_info["architecture"],
            windows_release=os_info["release"],
            cpu_name=self._get_first_wmi_value("Win32_Processor", "Name"),
            memory_gb=memory_total_gb,
            memory_modules=memory_modules,
            memory_type=memory_type,
            memory_speed_mhz=memory_speed_mhz,
            gpu_name=gpu_name,
            gpu_memory=gpu_memory,
            gpu_names=gpu_names,
            disks=disks,
            ipv4_address=network_info.ip_address if network_info else None,
            mac_address=network_info.mac_address if network_info else None,
            network_info=network_info,
            disk_nvme_summary=disk_summaries["NVMe"],
            disk_ssd_summary=disk_summaries["SSD"],
            disk_hdd_summary=disk_summaries["HDD"],
            disk_unknown_summary=disk_summaries["Unknown"],
            tpm_installed=tpm_installed,
            tpm_version=tpm_version,
            secure_boot_enabled=secure_boot_enabled,
            secure_boot_status=secure_boot_status,
            boot_mode=self._get_boot_mode(),
        )

    @staticmethod
    def _get_computer_name() -> str:
        return _get_windows_computer_name() or socket.gethostname() or "Unknown"

    @staticmethod
    def _get_user_name() -> str:
        user_name = _get_windows_user_name()
        if user_name:
            return user_name
        try:
            return getpass.getuser() or "Unknown"
        except Exception:
            return "Unknown"

    def _get_windows_version_info(self) -> dict[str, str | None]:
        os_item = self._first_wmi_item("Win32_OperatingSystem")
        raw_caption = _to_string(_get_value(os_item, "Caption"))
        caption = _normalize_os_caption(raw_caption)
        build = _to_string(_get_value(os_item, "BuildNumber"))
        architecture = _to_string(_get_value(os_item, "OSArchitecture"))
        release = _windows_release(raw_caption or caption, build)
        ubr = self._get_windows_ubr()
        return {
            "caption": caption,
            "build": build,
            "ubr": ubr,
            "architecture": architecture,
            "release": release,
        }

    def _get_windows_ubr(self) -> str | None:
        if self.registry is None:
            return None
        try:
            return _to_string(
                self.registry.read_value(
                    "HKEY_LOCAL_MACHINE",
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                    "UBR",
                )
            )
        except Exception:
            return None

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

    def _get_gpu_info(self) -> tuple[str | None, str | None, list[str]]:
        dxgi_info = self._read_dxgi_gpu_info()
        if dxgi_info is not None:
            return dxgi_info

        candidates: list[_GpuCandidate] = []
        has_basic_display = False
        for item in self._wmi_items("Win32_VideoController"):
            name = _to_string(_get_value(item, "Name")) or "Unknown GPU"
            adapter_compatibility = _to_string(_get_value(item, "AdapterCompatibility")) or ""
            adapter_ram = _to_int(_get_value(item, "AdapterRAM"))
            if _is_basic_display_adapter(name):
                has_basic_display = True
                continue
            if _is_virtual_gpu(name, adapter_compatibility):
                continue
            candidates.append(
                _GpuCandidate(
                    name=name,
                    adapter_memory_bytes=adapter_ram,
                    is_integrated=_is_integrated_gpu(name, adapter_ram),
                )
            )

        selected = _select_representative_gpu(candidates)
        gpu_names = _unique_preserving_order(candidate.name for candidate in candidates)
        if selected is not None:
            return selected.name, _format_gpu_memory(selected), gpu_names
        if has_basic_display:
            return "드라이버 없음", "알 수 없음", ["드라이버 없음"]
        return None, None, gpu_names

    def _get_disks(self) -> list[DiskInfo]:
        physical_disks = self._get_physical_disks()
        disk_type_by_index = self._get_disk_type_by_index()
        disks: list[DiskInfo] = []
        try:
            for item in self._wmi_items("Win32_DiskDrive"):
                if _is_usb_or_removable_disk(item):
                    continue
                disks.append(_build_disk_info(item, physical_disks, disk_type_by_index))

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

    def _get_active_network_info(self) -> PcNetworkInfo | None:
        candidate = self._get_active_network_info_with_powershell()
        if candidate is None:
            candidate = self._get_active_network_info_with_wmi()
        if candidate is None:
            return None
        return PcNetworkInfo(
            adapter_name=candidate.adapter_name,
            adapter_type=candidate.adapter_type,
            ip_address=candidate.ip_address,
            mac_address=normalize_mac_address(candidate.mac_address) or candidate.mac_address,
            description=candidate.description,
        )

    def _get_active_network_info_with_powershell(self) -> "_NetworkCandidate | None":
        if self.command_runner is None:
            return None
        try:
            output = self.command_runner.run(
                (
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    _ACTIVE_NETWORK_INFO_SCRIPT,
                )
            )
            candidates = _parse_powershell_network_candidates(output)
        except Exception:
            return None
        return _select_network_candidate(candidates)

    def _get_active_network_info_with_wmi(self) -> "_NetworkCandidate | None":
        adapters_by_index = {
            _to_int(_get_value(item, "Index")): item
            for item in self._wmi_items("Win32_NetworkAdapter")
            if _to_int(_get_value(item, "Index")) is not None
        }
        candidates: list[_NetworkCandidate] = []
        for item in self._wmi_items("Win32_NetworkAdapterConfiguration"):
            candidate = _network_candidate_from_wmi_item(item, adapters_by_index)
            if candidate is not None:
                candidates.append(candidate)
        return _select_network_candidate(candidates)

    def _read_dxgi_gpu_info(self) -> tuple[str, str, list[str]] | None:
        return read_dxgi_gpu_info()

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

    def _get_disk_type_by_index(self) -> dict[int, str]:
        return _build_disk_type_by_index_from_storage_wmi(
            self._wmi_items("MSFT_Disk", r"root\Microsoft\Windows\Storage"),
            self._wmi_items("MSFT_PhysicalDisk", r"root\Microsoft\Windows\Storage"),
        )

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


@dataclass(frozen=True)
class _GpuCandidate:
    name: str
    adapter_memory_bytes: int | None = None
    is_integrated: bool = False


@dataclass(frozen=True)
class _NetworkCandidate:
    adapter_name: str
    adapter_type: str
    ip_address: str
    mac_address: str | None = None
    description: str = ""
    interface_metric: int = 9999
    route_metric: int = 9999


def _build_disk_info(
    disk: Any,
    physical_disks: list[_PhysicalDiskMetadata],
    disk_type_by_index: dict[int, str] | None = None,
) -> DiskInfo:
    model = _to_string(_get_value(disk, "Model")) or "Unknown"
    serial = _normalize_disk_token(_to_string(_get_value(disk, "SerialNumber")))
    size_bytes = _to_int(_get_value(disk, "Size")) or 0
    matched = _find_best_physical_disk(physical_disks, model, serial, size_bytes)
    disk_index = _resolve_disk_index(disk)
    mapped_type = disk_type_by_index.get(disk_index) if disk_type_by_index is not None and disk_index is not None else None
    ioctl_type = _detect_disk_type_from_physical_drive(disk_index) if not mapped_type and disk_index is not None else "Unknown"
    disk_type = _disk_type_from_mapped_type(mapped_type) or _disk_type_from_mapped_type(ioctl_type) or _infer_disk_type(disk, matched.media_type if matched else None)
    bus_type = _bus_type_from_mapped_type(mapped_type or ioctl_type) or _infer_bus_type(disk, model, matched.bus_type if matched else None)
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


def _is_usb_or_removable_disk(disk: Any) -> bool:
    text = " ".join(
        _to_string(_get_value(disk, name)) or ""
        for name in ("Model", "InterfaceType", "PNPDeviceID", "DeviceID", "MediaType")
    ).lower()
    return any(token in text for token in ("usb", "usbstor", "removable"))


def _resolve_disk_index(disk: Any) -> int | None:
    index = _to_int(_get_value(disk, "Index"))
    if index is not None:
        return index
    device_id = _to_string(_get_value(disk, "DeviceID")) or ""
    match = re.search(r"physicaldrive(\d+)", device_id, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _build_disk_type_by_index_from_storage_wmi(disk_rows: list[Any], physical_rows: list[Any]) -> dict[int, str]:
    physical_by_unique_id: dict[str, Any] = {}
    physical_list: list[Any] = []
    for row in physical_rows:
        unique_id = _normalize_storage_key(_to_string(_get_value(row, "UniqueId")))
        if unique_id and unique_id not in physical_by_unique_id:
            physical_by_unique_id[unique_id] = row
        physical_list.append(row)

    result: dict[int, str] = {}
    for row in disk_rows:
        index = _to_int(_get_value(row, "Number"))
        if index is None:
            continue
        physical = _find_storage_physical_disk(row, physical_by_unique_id, physical_list)
        disk_type = _classify_disk_type_from_storage_metadata(row, physical)
        if disk_type:
            result[index] = disk_type
    return result


def _find_storage_physical_disk(disk_row: Any, physical_by_unique_id: dict[str, Any], physical_list: list[Any]) -> Any | None:
    unique_id = _normalize_storage_key(_to_string(_get_value(disk_row, "UniqueId")))
    if unique_id and unique_id in physical_by_unique_id:
        return physical_by_unique_id[unique_id]

    disk_model = _normalize_storage_key(_to_string(_get_value(disk_row, "Model")) or _to_string(_get_value(disk_row, "FriendlyName")))
    disk_size = _to_int(_get_value(disk_row, "Size")) or 0
    for candidate in physical_list:
        candidate_model = _normalize_storage_key(
            _to_string(_get_value(candidate, "Model")) or _to_string(_get_value(candidate, "FriendlyName"))
        )
        candidate_size = _to_int(_get_value(candidate, "Size")) or 0
        if disk_model and candidate_model != disk_model:
            continue
        if disk_size and candidate_size and disk_size != candidate_size:
            continue
        return candidate
    return None


def _classify_disk_type_from_storage_metadata(disk_row: Any, physical_row: Any | None) -> str:
    bus_type = _to_int(_get_value(physical_row, "BusType")) if physical_row is not None else None
    if bus_type is None:
        bus_type = _to_int(_get_value(disk_row, "BusType"))
    if bus_type == 17:
        return "NVMe"

    media_type = _to_int(_get_value(physical_row, "MediaType")) if physical_row is not None else None
    if media_type == 3:
        return "HDD"
    if media_type in {4, 5}:
        return "SSD"
    return ""


def _normalize_storage_key(value: str | None) -> str:
    return (value or "").strip().lower()


def _disk_type_from_mapped_type(value: str | None) -> str | None:
    if value == "NVMe":
        return "SSD"
    if value in {"SSD", "HDD"}:
        return value
    return None


def _bus_type_from_mapped_type(value: str | None) -> str | None:
    return "NVMe" if value == "NVMe" else None


def _detect_disk_type_from_physical_drive(index: int | None) -> str:
    if index is None or index < 0:
        return "Unknown"
    bus_type = _query_physical_drive_bus_type(index)
    if bus_type == 17:
        return "NVMe"
    seek_penalty = _query_physical_drive_seek_penalty(index)
    if seek_penalty is True:
        return "HDD"
    if seek_penalty is False:
        return "SSD"
    return "Unknown"


def _query_physical_drive_bus_type(index: int) -> int | None:
    try:
        import ctypes
        from ctypes import wintypes

        IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
        StorageDeviceProperty = 0
        PropertyStandardQuery = 0
        GENERIC_READ = 0
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = -1

        class STORAGE_PROPERTY_QUERY(ctypes.Structure):
            _fields_ = (("PropertyId", wintypes.DWORD), ("QueryType", wintypes.DWORD), ("AdditionalParameters", ctypes.c_ubyte * 1))

        class STORAGE_DESCRIPTOR_HEADER(ctypes.Structure):
            _fields_ = (("Version", wintypes.DWORD), ("Size", wintypes.DWORD))

        handle = ctypes.windll.kernel32.CreateFileW(
            rf"\\.\PhysicalDrive{index}",
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            return None
        try:
            query = STORAGE_PROPERTY_QUERY(StorageDeviceProperty, PropertyStandardQuery)
            header = STORAGE_DESCRIPTOR_HEADER()
            returned = wintypes.DWORD()
            ok = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_STORAGE_QUERY_PROPERTY,
                ctypes.byref(query),
                ctypes.sizeof(query),
                ctypes.byref(header),
                ctypes.sizeof(header),
                ctypes.byref(returned),
                None,
            )
            if not ok or header.Size < 28:
                return None
            buffer = ctypes.create_string_buffer(header.Size)
            ok = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_STORAGE_QUERY_PROPERTY,
                ctypes.byref(query),
                ctypes.sizeof(query),
                buffer,
                header.Size,
                ctypes.byref(returned),
                None,
            )
            if not ok:
                return None
            return int(buffer.raw[28])
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        return None


def _query_physical_drive_seek_penalty(index: int) -> bool | None:
    try:
        import ctypes
        from ctypes import wintypes

        IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
        StorageDeviceSeekPenaltyProperty = 7
        PropertyStandardQuery = 0
        GENERIC_READ = 0
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = -1

        class STORAGE_PROPERTY_QUERY(ctypes.Structure):
            _fields_ = (("PropertyId", wintypes.DWORD), ("QueryType", wintypes.DWORD), ("AdditionalParameters", ctypes.c_ubyte * 1))

        class DEVICE_SEEK_PENALTY_DESCRIPTOR(ctypes.Structure):
            _fields_ = (("Version", wintypes.DWORD), ("Size", wintypes.DWORD), ("IncursSeekPenalty", wintypes.BOOL))

        handle = ctypes.windll.kernel32.CreateFileW(
            rf"\\.\PhysicalDrive{index}",
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            return None
        try:
            query = STORAGE_PROPERTY_QUERY(StorageDeviceSeekPenaltyProperty, PropertyStandardQuery)
            descriptor = DEVICE_SEEK_PENALTY_DESCRIPTOR()
            returned = wintypes.DWORD()
            ok = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_STORAGE_QUERY_PROPERTY,
                ctypes.byref(query),
                ctypes.sizeof(query),
                ctypes.byref(descriptor),
                ctypes.sizeof(descriptor),
                ctypes.byref(returned),
                None,
            )
            if not ok:
                return None
            return bool(descriptor.IncursSeekPenalty)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        return None


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


def _disk_type_summaries(disks: list[DiskInfo]) -> dict[str, str]:
    buckets: dict[str, list[str]] = {"NVMe": [], "SSD": [], "HDD": [], "Unknown": []}
    for disk in disks:
        category = _disk_summary_category(disk)
        buckets[category].append(disk.rated_size or "알 수 없음")
    return {key: _summarize_capacity_bucket(values) for key, values in buckets.items()}


def _disk_summary_category(disk: DiskInfo) -> str:
    bus_type = (disk.bus_type or "").lower()
    display_type = (disk.display_type or "").lower()
    disk_type = (disk.disk_type or "").upper()
    if "nvme" in bus_type or "nvme" in display_type:
        return "NVMe"
    if disk_type == "SSD":
        return "SSD"
    if disk_type == "HDD":
        return "HDD"
    return "Unknown"


def _summarize_capacity_bucket(values: list[str]) -> str:
    if not values:
        return "없음"
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    parts = [f"{size} x{count}" for size, count in sorted(counts.items(), key=lambda item: _capacity_sort_key(item[0]), reverse=True)]
    return f"{len(values)}개({', '.join(parts)})"


def _capacity_sort_key(value: str) -> int:
    match = re.fullmatch(r"(\d+)(GB|TB)", value)
    if not match:
        return 0
    amount = int(match.group(1))
    return amount * (1024 if match.group(2) == "TB" else 1)


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


def _parse_boolish(value: Any | None) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "enabled", "yes", "on", "1", "예", "사용", "사용함"}:
        return True
    if text in {"false", "disabled", "no", "off", "0", "아니요", "사용 안 함", "사용안함"}:
        return False
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


def _normalize_os_caption(caption: str | None) -> str:
    text = (caption or "").strip()
    if not text:
        return "알 수 없음(운영체제 캡션 없음)"
    if text.lower().startswith("microsoft "):
        text = text[len("Microsoft ") :]
    for token in ("(R)", "(r)", "(TM)", "(tm)", "®", "™"):
        text = text.replace(token, "")
    text = re.sub(r"\s+", " ", text).strip()
    return text or "알 수 없음(운영체제 캡션 없음)"


def _memory_type_from_code(code: int) -> str:
    return {
        20: "DDR",
        21: "DDR2",
        24: "DDR3",
        26: "DDR4",
        27: "LPDDR3",
        29: "LPDDR3",
        30: "LPDDR4",
        34: "DDR5",
        35: "LPDDR5",
    }.get(code, "Unknown")


def _is_virtual_gpu(name: str, adapter_compatibility: str) -> bool:
    lower_name = name.lower()
    if any(
        token in lower_name
        for token in (
            "parsec",
            "virtual",
            "remote",
            "basic render driver",
            "citrix",
            "vmware",
            "virtualbox",
            "hyper-v",
            "radmin",
            "rdp",
            "software adapter",
        )
    ):
        return True

    compatibility = adapter_compatibility.lower()
    return (
        "microsoft corporation" in compatibility
        and "nvidia" not in lower_name
        and "amd" not in lower_name
        and "intel" not in lower_name
    )


def _is_basic_display_adapter(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in ("microsoft basic display adapter", "microsoft 기본 디스플레이 어댑터", "기본 디스플레이 어댑터"))


def _is_integrated_gpu(name: str, adapter_memory_bytes: int | None) -> bool:
    lower = name.lower()
    if any(token in lower for token in ("intel", "iris", "uhd graphics", "radeon graphics")):
        if not adapter_memory_bytes or adapter_memory_bytes <= 512 * 1024**2:
            return True
    return False


def _select_representative_gpu(candidates: list[_GpuCandidate]) -> _GpuCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda candidate: candidate.adapter_memory_bytes or 0, reverse=True)[0]


def _format_gpu_memory(candidate: _GpuCandidate | None) -> str:
    if candidate is None:
        return "알 수 없음"
    if _is_suspicious_wmi_gpu_memory(candidate.name, candidate.adapter_memory_bytes):
        return "알 수 없음"
    if candidate.is_integrated:
        return "없음(내장그래픽)"
    if not candidate.adapter_memory_bytes:
        return "없음(내장그래픽)" if candidate.is_integrated else "알 수 없음"
    gb = max(1, round(candidate.adapter_memory_bytes / 1024**3))
    return f"{gb}GB"


def _is_suspicious_wmi_gpu_memory(name: str, adapter_ram: int | None) -> bool:
    if not adapter_ram:
        return False
    lower = name.lower()
    if any(vendor in lower for vendor in ("nvidia", "geforce", "rtx", "gtx", "radeon", "amd")):
        return adapter_ram <= 1024**3
    return False


def _unique_preserving_order(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _parse_powershell_network_candidates(output: str) -> list[_NetworkCandidate]:
    if not output.strip():
        return []
    data = json.loads(output)
    items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
    candidates: list[_NetworkCandidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate = _network_candidate_from_powershell_item(item)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _network_candidate_from_powershell_item(item: dict[str, Any]) -> _NetworkCandidate | None:
    name = _to_string(item.get("Name")) or ""
    description = _to_string(item.get("InterfaceDescription")) or name
    status = (_to_string(item.get("Status")) or "").lower()
    if status != "up":
        return None
    return _network_candidate_from_values(
        adapter_name=name,
        description=description,
        ip_address=_to_string(item.get("IpAddress")),
        mac_address=_to_string(item.get("MacAddress")),
        gateway=_to_string(item.get("Gateway")),
        interface_metric=_to_int(item.get("InterfaceMetric")),
        route_metric=_to_int(item.get("RouteMetric")),
    )


def _network_candidate_from_wmi_item(item: Any, adapters_by_index: dict[int | None, Any]) -> _NetworkCandidate | None:
    if _parse_boolish(_get_value(item, "IPEnabled")) is False:
        return None

    adapter = adapters_by_index.get(_to_int(_get_value(item, "Index")))
    if adapter is None or not _wmi_adapter_is_up(adapter):
        return None

    name = (
        _to_string(_get_value(adapter, "NetConnectionID"))
        or _to_string(_get_value(adapter, "Name"))
        or _to_string(_get_value(item, "Caption"))
        or _to_string(_get_value(item, "Description"))
        or ""
    )
    description = _to_string(_get_value(adapter, "Description")) or _to_string(_get_value(item, "Description")) or name
    ipv4_addresses = [value for value in _to_string_list(_get_value(item, "IPAddress")) if _is_valid_display_ipv4(value)]
    gateways = [value for value in _to_string_list(_get_value(item, "DefaultIPGateway")) if _is_valid_display_ipv4(value)]
    return _network_candidate_from_values(
        adapter_name=name,
        description=description,
        ip_address=ipv4_addresses[0] if ipv4_addresses else None,
        mac_address=_to_string(_get_value(item, "MACAddress")),
        gateway=gateways[0] if gateways else None,
        interface_metric=_to_int(_get_value(item, "IPConnectionMetric")),
        route_metric=9999,
    )


def _network_candidate_from_values(
    adapter_name: str,
    description: str,
    ip_address: str | None,
    mac_address: str | None,
    gateway: str | None,
    interface_metric: int | None,
    route_metric: int | None,
) -> _NetworkCandidate | None:
    if not adapter_name:
        return None
    if _is_excluded_network_adapter(adapter_name, description):
        return None
    adapter_type = _classify_network_adapter(adapter_name, description)
    if adapter_type is None:
        return None
    if not ip_address or not _is_valid_display_ipv4(ip_address):
        return None
    if not gateway or not _is_valid_display_ipv4(gateway):
        return None
    return _NetworkCandidate(
        adapter_name=adapter_name,
        adapter_type=adapter_type,
        ip_address=ip_address,
        description=description,
        mac_address=mac_address,
        interface_metric=interface_metric or 9999,
        route_metric=route_metric or 9999,
    )


def _select_network_candidate(candidates: list[_NetworkCandidate]) -> _NetworkCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=_network_candidate_sort_key)[0]


def _network_candidate_sort_key(candidate: _NetworkCandidate) -> tuple[int, int, int, str]:
    adapter_type_priority = 0 if candidate.adapter_type == "Ethernet" else 1
    return (
        adapter_type_priority,
        candidate.interface_metric or 9999,
        candidate.route_metric or 9999,
        candidate.adapter_name.lower(),
    )


def _is_excluded_network_adapter(name: str, description: str = "") -> bool:
    lower = f"{name} {description}".lower()
    return any(
        token in lower
        for token in (
            "virtual",
            "virtualbox",
            "vmware",
            "hyper-v",
            "vpn",
            "openvpn",
            "wireguard",
            "tailscale",
            "zerotier",
            "tap",
            "tun",
            "tunnel",
            "docker",
            "wsl",
            "bluetooth",
            "loopback",
            "teredo",
            "isatap",
            "pseudo",
            "npcap",
            "hamachi",
            "fortinet",
            "anyconnect",
            "pulse secure",
            "check point",
        )
    )


def _classify_network_adapter(name: str, description: str) -> str | None:
    lower = f"{name} {description}".lower()
    if any(token in lower for token in ("wi-fi", "wifi", "wireless", "wlan", "802.11", "무선")):
        return "Wi-Fi"
    if any(
        token in lower
        for token in (
            "ethernet",
            "이더넷",
            "realtek",
            "intel(r) ethernet",
            "gbe",
            "2.5gbe",
            "gigabit",
            "lan",
            "i219",
            "i225",
            "i226",
        )
    ):
        return "Ethernet"
    return None


def _wmi_adapter_is_up(adapter: Any) -> bool:
    net_enabled = _parse_boolish(_get_value(adapter, "NetEnabled"))
    if net_enabled is not None:
        return net_enabled
    status = (_to_string(_get_value(adapter, "NetConnectionStatus")) or "").lower()
    if status in {"2", "connected", "up"}:
        return True
    text_status = (_to_string(_get_value(adapter, "Status")) or "").lower()
    return text_status in {"ok", "up"}


def _is_ipv4_address(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def _is_valid_display_ipv4(value: str) -> bool:
    if not _is_ipv4_address(value):
        return False
    return not (value.startswith("127.") or value.startswith("169.254.") or value == "0.0.0.0")


def _to_string_list(value: Any | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        return [str(item).strip() for item in value if str(item).strip()]
    except TypeError:
        text = str(value).strip()
        return [text] if text else []


def _get_windows_computer_name() -> str | None:
    try:
        import ctypes
        from ctypes import wintypes

        ComputerNameNetBIOS = 0
        size = wintypes.DWORD(256)
        buffer = ctypes.create_unicode_buffer(size.value)
        if ctypes.windll.kernel32.GetComputerNameExW(ComputerNameNetBIOS, buffer, ctypes.byref(size)):
            return buffer.value.strip() or None
    except Exception:
        return None
    return None


def _get_windows_user_name() -> str | None:
    try:
        import ctypes
        from ctypes import wintypes

        size = wintypes.DWORD(256)
        buffer = ctypes.create_unicode_buffer(size.value)
        if ctypes.windll.advapi32.GetUserNameW(buffer, ctypes.byref(size)):
            return buffer.value.strip("\x00").strip() or None
    except Exception:
        return None
    return None


_ACTIVE_NETWORK_INFO_SCRIPT = r"""
$ErrorActionPreference = 'Stop'

$adapters = Get-NetAdapter -Physical | Where-Object {
    $_.Status -eq 'Up' -and $_.HardwareInterface -eq $true
}

$result = foreach ($a in $adapters) {
    $ipcfg = Get-NetIPConfiguration -InterfaceIndex $a.ifIndex
    $ipv4 = $ipcfg.IPv4Address |
        Where-Object {
            $_.IPAddress -and
            $_.IPAddress -notmatch '^127\.' -and
            $_.IPAddress -notmatch '^169\.254\.' -and
            $_.IPAddress -ne '0.0.0.0'
        } |
        Select-Object -First 1

    $gateway = $ipcfg.IPv4DefaultGateway | Select-Object -First 1
    $ipInterface = Get-NetIPInterface -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Select-Object -First 1
    $route = Get-NetRoute -InterfaceIndex $a.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Sort-Object RouteMetric |
        Select-Object -First 1

    if ($ipv4 -and $gateway) {
        [PSCustomObject]@{
            Name = $a.Name
            InterfaceDescription = $a.InterfaceDescription
            Status = $a.Status
            MacAddress = $a.MacAddress
            InterfaceIndex = $a.ifIndex
            IpAddress = $ipv4.IPAddress
            Gateway = $gateway.NextHop
            InterfaceMetric = if ($ipInterface) { $ipInterface.InterfaceMetric } else { 9999 }
            RouteMetric = if ($route) { $route.RouteMetric } else { 9999 }
        }
    }
}

$result | ConvertTo-Json -Depth 4
""".strip()
