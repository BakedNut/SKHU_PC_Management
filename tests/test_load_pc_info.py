from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo, LoadPcInfoUseCase
from skhu_pc_management.domain.pc.models import DiskInfo, MemoryModuleInfo, PcInfo, PcNetworkInfo
from skhu_pc_management.infrastructure.windows.dxgi_gpu_reader import (
    DxgiGpuInfo,
    format_dxgi_gpu_memory,
    is_basic_display_adapter_name,
    is_integrated_dxgi_gpu,
    is_virtual_display_adapter_name,
    select_representative_dxgi_gpu,
)
from skhu_pc_management.infrastructure.windows.network_identity_reader import (
    IF_TYPE_ETHERNET_CSMACD,
    IF_TYPE_IEEE80211,
    NetworkIdentityCandidate,
    _extract_adapter_guid,
    _first_ipv4_from_registry_value,
    _ipv4_tuple_from_registry_value,
    normalize_mac_address,
    read_network_adapters_fast,
    select_network_identity_candidate,
)
from skhu_pc_management.infrastructure.windows import network_identity_reader
from skhu_pc_management.infrastructure.windows import wmi_pc_info_reader
from skhu_pc_management.infrastructure.windows.wmi_pc_info_reader import (
    _PhysicalDiskMetadata,
    _GpuCandidate,
    _NetworkCandidate,
    _build_disk_type_by_index_from_storage_wmi,
    _build_disk_info,
    _detect_disk_type_from_physical_drive,
    _disk_type_summaries,
    _format_rated_size,
    _format_gpu_memory,
    _is_usb_or_removable_disk,
    _memory_type_from_code,
    _normalize_os_caption,
    _resolve_disk_index,
    _select_network_candidate,
    _select_representative_gpu,
    WmiPcInfoReader,
)


class FakePcInfoReader:
    def __init__(self, pc_info: PcInfo) -> None:
        self.pc_info = pc_info
        self.read_count = 0

    def read(self) -> PcInfo:
        self.read_count += 1
        return self.pc_info


@dataclass
class WmiItem:
    Caption: str | None = None
    BuildNumber: str | None = None
    OSArchitecture: str | None = None
    Name: str | None = None
    Capacity: str | None = None
    Speed: str | None = None
    SMBIOSMemoryType: str | None = None
    MemoryType: str | None = None
    AdapterCompatibility: str | None = None
    AdapterRAM: str | None = None
    Model: str | None = None
    Size: str | None = None
    SerialNumber: str | None = None
    MediaRotationRate: str | None = None
    MediaType: Any | None = None
    InterfaceType: str | None = None
    PNPDeviceID: str | None = None
    DeviceID: str | None = None
    Index: str | None = None
    Number: Any | None = None
    UniqueId: str | None = None
    FriendlyName: str | None = None
    BusType: Any | None = None
    SpecVersion: str | None = None
    IPEnabled: Any | None = None
    Description: str | None = None
    IPAddress: Any | None = None
    DefaultIPGateway: Any | None = None
    MACAddress: str | None = None
    IPConnectionMetric: Any | None = None
    NetConnectionID: str | None = None
    NetConnectionStatus: Any | None = None
    NetEnabled: Any | None = None
    Status: str | None = None


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], object] = {}
        self.reads: list[tuple[str, str, str]] = []

    def set_value(self, root: str, path: str, name: str, value: object) -> None:
        self.values[(root, path, name)] = value

    def read_value(self, root: str, path: str, name: str) -> object | None:
        self.reads.append((root, path, name))
        return self.values.get((root, path, name))

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        raise AssertionError("PC info loading must not write registry values")


class FailingRegistry(FakeRegistry):
    def read_value(self, root: str, path: str, name: str) -> object | None:
        raise OSError("registry read failed")


class FakeCommandRunner:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...]) -> str:
        self.commands.append(command)
        return self.output


class ControlledWmiPcInfoReader(WmiPcInfoReader):
    def __init__(
        self,
        wmi_items_by_class: dict[tuple[str, str | None], list[Any]],
        registry: FakeRegistry | None = None,
        command_runner: FakeCommandRunner | None = None,
    ) -> None:
        super().__init__(registry=registry, command_runner=command_runner)
        object.__setattr__(self, "wmi_items_by_class", wmi_items_by_class)
        object.__setattr__(self, "wmi_call_counts", {})

    def _wmi_items(self, wmi_class: str, namespace: str | None = None) -> list[Any]:
        key = (wmi_class, namespace)
        self.wmi_call_counts[key] = self.wmi_call_counts.get(key, 0) + 1
        return self.wmi_items_by_class.get((wmi_class, namespace), [])

    def _read_dxgi_gpu_info(self) -> tuple[str, str, list[str]] | None:
        return None

    def _read_network_identity(self) -> tuple[str, str] | None:
        return None


@pytest.fixture(autouse=True)
def disable_low_level_network_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wmi_pc_info_reader, "read_active_network_info", lambda: None)


def test_load_pc_info_use_case_uses_reader_port() -> None:
    expected = PcInfo(
        computer_name="PC01",
        user_name="student",
        os_name="Windows 11 Pro",
        windows_build="26100",
        windows_architecture="64-bit",
        windows_release="24H2",
        cpu_name="Intel CPU",
        memory_gb=16.0,
        memory_modules=[MemoryModuleInfo(slot="Slot 1", capacity_gb=16.0, memory_type="DDR4", speed_mhz=3200)],
        gpu_names=["NVIDIA GPU"],
        disks=[DiskInfo(model="Samsung SSD", size_gb=512.0, disk_type="SSD")],
        tpm_installed=True,
        tpm_version="2.0",
        secure_boot_enabled=True,
        secure_boot_status="Enabled",
        boot_mode="UEFI",
    )
    reader = FakePcInfoReader(expected)

    result = LoadPcInfo(reader).execute()

    assert result == expected
    assert reader.read_count == 1


def test_load_pc_info_use_case_alias_exists() -> None:
    expected = PcInfo(
        computer_name="PC01",
        user_name="student",
        os_name="Windows",
        cpu_name="CPU",
    )

    assert LoadPcInfoUseCase(FakePcInfoReader(expected)).execute() == expected


def test_pc_info_models_can_represent_missing_values() -> None:
    pc_info = PcInfo(
        computer_name="Unknown",
        user_name="Unknown",
        os_name="Unknown",
        cpu_name="Unknown",
        memory_gb=None,
        disks=[DiskInfo(model="Unknown", size_gb=None, disk_type="Unknown")],
        tpm_installed=None,
        secure_boot_enabled=None,
        boot_mode="Unknown",
    )

    assert pc_info.memory_gb is None
    assert pc_info.disks[0].size_gb is None
    assert pc_info.tpm_installed is None


def test_wmi_reader_maps_structured_values_without_real_windows_calls() -> None:
    registry = FakeRegistry()
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SYSTEM\CurrentControlSet\Control\SecureBoot\State",
        "UEFISecureBootEnabled",
        1,
    )
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"System\CurrentControlSet\Control",
        "PEFirmwareType",
        2,
    )
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "UBR",
        3323,
    )
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_OperatingSystem", None): [
                WmiItem(Caption="Microsoft Windows 11 Pro", BuildNumber="26100", OSArchitecture="64-bit")
            ],
            ("Win32_Processor", None): [WmiItem(Name="Intel Core")],
            ("Win32_PhysicalMemory", None): [
                WmiItem(Capacity=str(16 * 1024**3), Speed="3200", SMBIOSMemoryType="26")
            ],
            ("Win32_VideoController", None): [
                WmiItem(Name="Microsoft Basic Display Adapter", AdapterCompatibility="Microsoft"),
                WmiItem(Name="NVIDIA RTX", AdapterCompatibility="NVIDIA", AdapterRAM=str(8 * 1024**3)),
            ],
            ("Win32_DiskDrive", None): [
                WmiItem(
                    Model="Samsung NVMe SSD",
                    Size=str(512 * 1024**3),
                    MediaRotationRate="0",
                    InterfaceType="SCSI",
                )
            ],
            ("Win32_NetworkAdapterConfiguration", None): [
                WmiItem(
                    IPEnabled=True,
                    Index="1",
                    Caption="Realtek Ethernet",
                    Description="Realtek Gaming 2.5GbE Family Controller",
                    IPAddress=["192.168.0.10"],
                    DefaultIPGateway=["192.168.0.1"],
                    MACAddress="AA-BB-CC-DD-EE-FF",
                    IPConnectionMetric="25",
                )
            ],
            ("Win32_NetworkAdapter", None): [
                WmiItem(
                    Index="1",
                    NetConnectionID="이더넷",
                    Name="Realtek Ethernet",
                    Description="Realtek Gaming 2.5GbE Family Controller",
                    NetEnabled=True,
                )
            ],
            ("Win32_Tpm", r"root\CIMV2\Security\MicrosoftTpm"): [WmiItem(SpecVersion="2.0, 1.3")],
        },
        registry=registry,
    )

    pc_info = reader.read()

    assert pc_info.os_name == "Windows 11 Pro"
    assert pc_info.windows_build == "26100"
    assert pc_info.windows_ubr == "3323"
    assert pc_info.windows_release == "24H2"
    assert pc_info.cpu_name == "Intel Core"
    assert pc_info.memory_gb == 16.0
    assert pc_info.memory_modules[0].memory_type == "DDR4"
    assert pc_info.gpu_name == "NVIDIA RTX"
    assert pc_info.gpu_memory == "8GB"
    assert pc_info.gpu_names == ["NVIDIA RTX"]
    assert pc_info.ipv4_address == "192.168.0.10"
    assert pc_info.mac_address == "AA-BB-CC-DD-EE-FF"
    assert pc_info.network_info == PcNetworkInfo(
        adapter_name="이더넷",
        adapter_type="Ethernet",
        ip_address="192.168.0.10",
        mac_address="AA-BB-CC-DD-EE-FF",
        description="Realtek Gaming 2.5GbE Family Controller",
    )
    assert pc_info.disk_nvme_summary == "1개(512GB x1)"
    assert pc_info.disk_ssd_summary == "없음"
    assert pc_info.disks == [
        DiskInfo(
            model="Samsung NVMe SSD",
            size_gb=512.0,
            actual_size_gib=512.0,
            rated_size="512GB",
            disk_type="SSD",
            bus_type="NVMe",
            display_type="SSD (NVMe)",
            raw_size_bytes=512 * 1024**3,
        )
    ]
    assert pc_info.tpm_installed is True
    assert pc_info.tpm_version == "2.0"
    assert pc_info.secure_boot_enabled is True
    assert pc_info.boot_mode == "UEFI"


def test_wmi_reader_uses_bcdedit_fallback_through_command_runner() -> None:
    command_runner = FakeCommandRunner(output="path \\Windows\\system32\\winload.efi")
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.boot_mode == "UEFI"
    assert command_runner.commands[-1] == ("bcdedit", "/enum", "{current}")


def test_wmi_reader_returns_unknowns_when_values_are_missing() -> None:
    reader = ControlledWmiPcInfoReader({})

    pc_info = reader.read()

    assert pc_info.os_name == "알 수 없음(운영체제 캡션 없음)"
    assert pc_info.cpu_name == "Unknown"
    assert pc_info.memory_gb is None
    assert pc_info.gpu_names == []
    assert pc_info.disks == []
    assert pc_info.tpm_installed is None
    assert pc_info.secure_boot_status == "Unknown"
    assert pc_info.boot_mode == "Unknown"


def test_pc_info_model_windows_ubr_is_optional() -> None:
    pc_info = PcInfo(
        computer_name="PC01",
        user_name="student",
        os_name="Windows",
        cpu_name="CPU",
    )

    assert pc_info.windows_ubr is None


def test_wmi_reader_reads_windows_ubr_from_registry_port() -> None:
    registry = FakeRegistry()
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "UBR",
        8655,
    )
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_OperatingSystem", None): [
                WmiItem(Caption="Microsoft Windows 11 Pro", BuildNumber="26200", OSArchitecture="64비트")
            ],
        },
        registry=registry,
    )

    pc_info = reader.read()

    assert pc_info.windows_ubr == "8655"
    assert (
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "UBR",
    ) in registry.reads


def test_wmi_reader_ignores_windows_ubr_registry_read_failure() -> None:
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_OperatingSystem", None): [
                WmiItem(Caption="Microsoft Windows 11 Pro", BuildNumber="26200", OSArchitecture="64비트")
            ],
        },
        registry=FailingRegistry(),
    )

    pc_info = reader.read()

    assert pc_info.windows_build == "26200"
    assert pc_info.windows_ubr is None


def test_wmi_reader_uses_os_registry_fast_path_without_operating_system_wmi() -> None:
    registry = FakeRegistry()
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "ProductName",
        "Microsoft Windows 11 Pro",
    )
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "DisplayVersion",
        "24H2",
    )
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "CurrentBuildNumber",
        "26100",
    )
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "UBR",
        3323,
    )
    reader = ControlledWmiPcInfoReader({}, registry=registry)

    os_info = reader._get_windows_version_info()

    assert os_info["caption"] == "Windows 11 Pro"
    assert os_info["build"] == "26100"
    assert os_info["release"] == "24H2"
    assert os_info["ubr"] == "3323"
    assert reader.wmi_call_counts.get(("Win32_OperatingSystem", None), 0) == 0


def test_disk_info_can_be_built_from_win32_diskdrive_only() -> None:
    disk = _build_disk_info(
        WmiItem(Model="Samsung NVMe SSD", Size=str(256 * 1024**3), MediaRotationRate="0", InterfaceType="SCSI"),
        [],
    )

    assert disk.model == "Samsung NVMe SSD"
    assert disk.actual_size_gib == 256.0
    assert disk.rated_size == "256GB"
    assert disk.disk_type == "SSD"
    assert disk.bus_type == "NVMe"
    assert disk.display_type == "SSD (NVMe)"


def test_disk_info_matches_msft_physical_disk_by_serial() -> None:
    disk = _build_disk_info(
        WmiItem(
            Model="Samsung SSD 970 EVO Plus 500GB",
            SerialNumber="S4EWNX0M123456",
            Size=str(500 * 1024**3),
            InterfaceType="SCSI",
        ),
        [
            _PhysicalDiskMetadata(
                friendly_name="Samsung SSD 970 EVO Plus 500GB",
                serial_number="S4EWNX0M123456",
                media_type="SSD",
                bus_type="NVMe",
                size_bytes=500 * 1024**3,
            )
        ],
    )

    assert disk.display_type == "SSD (NVMe)"
    assert disk.bus_type == "NVMe"
    assert disk.rated_size == "512GB"


def test_disk_info_matches_msft_physical_disk_by_model_and_size_when_serial_is_missing() -> None:
    disk = _build_disk_info(
        WmiItem(Model="WDC WD10EZEX SATA Disk", Size=str(953 * 1024**3), InterfaceType="SCSI"),
        [
            _PhysicalDiskMetadata(
                friendly_name="WDC WD10EZEX",
                serial_number="",
                media_type="HDD",
                bus_type="SATA",
                size_bytes=953 * 1024**3,
            )
        ],
    )

    assert disk.disk_type == "HDD"
    assert disk.bus_type == "SATA"
    assert disk.display_type == "HDD (SATA)"


def test_disk_info_matches_msft_physical_disk_by_size_tolerance() -> None:
    disk = _build_disk_info(
        WmiItem(Model="Generic Disk", Size=str(476 * 1024**3), InterfaceType="SCSI"),
        [
            _PhysicalDiskMetadata(
                friendly_name="Different Friendly Name",
                serial_number="",
                media_type="SSD",
                bus_type="SATA",
                size_bytes=(476 * 1024**3) + (2 * 1024**3),
            )
        ],
    )

    assert disk.display_type == "SSD (SATA)"
    assert disk.rated_size == "512GB"


def test_disk_rated_size_rounds_up_to_power_of_two() -> None:
    assert _format_rated_size(476 * 1024**3) == "512GB"
    assert _format_rated_size(953 * 1024**3) == "1TB"
    assert _format_rated_size(29 * 1024**3) == "32GB"


def test_wmi_reader_uses_msft_physical_disk_bus_and_media_data() -> None:
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_DiskDrive", None): [
                WmiItem(
                    Model="Samsung SSD 970 EVO Plus 500GB",
                    SerialNumber="S4EWNX0M123456",
                    Size=str(500 * 1024**3),
                    InterfaceType="SCSI",
                )
            ],
            ("MSFT_PhysicalDisk", r"root\Microsoft\Windows\Storage"): [
                WmiItem(
                    FriendlyName="Samsung SSD 970 EVO Plus 500GB",
                    SerialNumber="S4EWNX0M123456",
                    MediaType=4,
                    BusType=17,
                    Size=str(500 * 1024**3),
                )
            ],
        }
    )

    disk = reader.read().disks[0]

    assert disk.display_type == "SSD (NVMe)"
    assert disk.bus_type == "NVMe"
    assert disk.disk_type == "SSD"


def test_wmi_reader_falls_back_to_win32_diskdrive_when_msft_physical_disk_is_missing() -> None:
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_DiskDrive", None): [
                WmiItem(Model="ST1000DM010 SATA HDD", Size=str(953 * 1024**3), InterfaceType="SCSI")
            ],
        }
    )

    disk = reader.read().disks[0]

    assert disk.display_type == "HDD (SATA)"
    assert disk.rated_size == "1TB"


def test_os_caption_normalization_removes_vendor_and_trademark_noise() -> None:
    assert _normalize_os_caption("Microsoft Windows 11 Pro") == "Windows 11 Pro"
    assert _normalize_os_caption("Microsoft Windows(R) 10 Pro") == "Windows 10 Pro"
    assert _normalize_os_caption("Microsoft Windows™ 11 Education") == "Windows 11 Education"
    assert _normalize_os_caption("") == "알 수 없음(운영체제 캡션 없음)"
    assert _normalize_os_caption(None) == "알 수 없음(운영체제 캡션 없음)"


def test_gpu_candidate_selection_prefers_larger_dedicated_memory() -> None:
    selected = _select_representative_gpu(
        [
            _GpuCandidate("Intel UHD Graphics", adapter_memory_bytes=128 * 1024**2, is_integrated=True),
            _GpuCandidate("NVIDIA RTX", adapter_memory_bytes=8 * 1024**3),
        ]
    )

    assert selected is not None
    assert selected.name == "NVIDIA RTX"
    assert _format_gpu_memory(selected) == "8GB"
    assert _format_gpu_memory(_GpuCandidate("Intel UHD Graphics", is_integrated=True)) == "없음(내장그래픽)"


def test_dxgi_gpu_helpers_select_physical_gpu_and_format_memory() -> None:
    selected = select_representative_dxgi_gpu(
        [
            DxgiGpuInfo("VMware Virtual Display", 16 * 1024**2, is_virtual=True),
            DxgiGpuInfo("Intel UHD Graphics", 128 * 1024**2, shared_memory_bytes=8 * 1024**3, vendor_id=0x8086),
            DxgiGpuInfo("NVIDIA GeForce RTX 4070 SUPER", 12 * 1024**3),
            DxgiGpuInfo("NVIDIA GeForce RTX 3060", 8 * 1024**3),
        ]
    )

    assert selected is not None
    assert selected.name == "NVIDIA GeForce RTX 4070 SUPER"
    assert format_dxgi_gpu_memory(selected) == "12GB"
    assert is_virtual_display_adapter_name("VMware Virtual Display") is True
    assert is_basic_display_adapter_name("Microsoft Basic Display Adapter") is True
    assert is_integrated_dxgi_gpu(vendor_id=0x8086, dedicated_memory_bytes=128 * 1024**2, shared_memory_bytes=8 * 1024**3) is True
    assert format_dxgi_gpu_memory(DxgiGpuInfo("Intel UHD Graphics", 128 * 1024**2, is_integrated=True)) == "없음(내장그래픽)"


def test_wmi_gpu_fallback_does_not_trust_suspicious_dgpu_one_gb() -> None:
    assert _format_gpu_memory(_GpuCandidate("NVIDIA GeForce RTX 4070 SUPER", adapter_memory_bytes=1024**3)) == "알 수 없음"
    assert _format_gpu_memory(_GpuCandidate("Intel UHD Graphics", adapter_memory_bytes=128 * 1024**2, is_integrated=True)) == "없음(내장그래픽)"


def test_disk_helpers_exclude_usb_and_group_capacity_summaries() -> None:
    assert _is_usb_or_removable_disk(WmiItem(Model="USB Disk", InterfaceType="USB", PNPDeviceID="USBSTOR\\Disk")) is True
    assert _is_usb_or_removable_disk(WmiItem(Model="Samsung NVMe SSD", InterfaceType="SCSI")) is False

    summaries = _disk_type_summaries(
        [
            DiskInfo(model="NVMe 1", disk_type="SSD", bus_type="NVMe", display_type="SSD (NVMe)", rated_size="1TB"),
            DiskInfo(model="NVMe 2", disk_type="SSD", bus_type="NVMe", display_type="SSD (NVMe)", rated_size="512GB"),
            DiskInfo(model="SATA SSD", disk_type="SSD", bus_type="SATA", display_type="SSD (SATA)", rated_size="256GB"),
            DiskInfo(model="HDD", disk_type="HDD", bus_type="SATA", display_type="HDD (SATA)", rated_size="512GB"),
            DiskInfo(model="Unknown", disk_type="Unknown", display_type="알 수 없음", rated_size=None),
        ]
    )

    assert summaries["NVMe"] == "2개(1TB x1, 512GB x1)"
    assert summaries["SSD"] == "1개(256GB x1)"
    assert summaries["HDD"] == "1개(512GB x1)"
    assert summaries["Unknown"] == "1개(알 수 없음 x1)"


def test_disk_index_and_storage_wmi_type_map_helpers(monkeypatch) -> None:
    assert _resolve_disk_index(WmiItem(Index="1", DeviceID=r"\\.\PHYSICALDRIVE9")) == 1
    assert _resolve_disk_index(WmiItem(DeviceID=r"\\.\PHYSICALDRIVE2")) == 2

    type_map = _build_disk_type_by_index_from_storage_wmi(
        [
            WmiItem(Number=0, Model="NVMe Disk", FriendlyName="NVMe Disk", Size=str(512 * 1024**3), BusType=17),
            WmiItem(Number=1, Model="HDD Disk", FriendlyName="HDD Disk", Size=str(1024 * 1024**3), BusType=11),
            WmiItem(Number=2, Model="SSD Disk", FriendlyName="SSD Disk", Size=str(256 * 1024**3), BusType=11),
        ],
        [
            WmiItem(FriendlyName="HDD Disk", MediaType=3, BusType=11, Size=str(1024 * 1024**3)),
            WmiItem(FriendlyName="SSD Disk", MediaType=4, BusType=11, Size=str(256 * 1024**3)),
        ],
    )

    assert type_map == {0: "NVMe", 1: "HDD", 2: "SSD"}

    monkeypatch.setattr(wmi_pc_info_reader, "_query_physical_drive_bus_type", lambda index: 17)
    assert _detect_disk_type_from_physical_drive(0) == "NVMe"
    monkeypatch.setattr(wmi_pc_info_reader, "_query_physical_drive_bus_type", lambda index: None)
    monkeypatch.setattr(wmi_pc_info_reader, "_query_physical_drive_seek_penalty", lambda index: True)
    assert _detect_disk_type_from_physical_drive(0) == "HDD"
    monkeypatch.setattr(wmi_pc_info_reader, "_query_physical_drive_seek_penalty", lambda index: False)
    assert _detect_disk_type_from_physical_drive(0) == "SSD"


def test_network_candidate_selection_prefers_ethernet_gateway_and_low_metric() -> None:
    candidates = [
        _NetworkCandidate(
            adapter_name="Wi-Fi",
            adapter_type="Wi-Fi",
            ip_address="192.168.0.20",
            interface_metric=10,
        ),
        _NetworkCandidate(
            adapter_name="Ethernet",
            adapter_type="Ethernet",
            description="Realtek",
            ip_address="192.168.0.10",
            interface_metric=25,
        ),
        _NetworkCandidate(
            adapter_name="Ethernet 2",
            adapter_type="Ethernet",
            description="Realtek",
            ip_address="192.168.0.11",
            interface_metric=5,
        ),
    ]

    selected = _select_network_candidate(candidates)

    assert selected is not None
    assert selected.ip_address == "192.168.0.11"


def test_pc_info_network_selection_prefers_physical_ethernet_from_powershell() -> None:
    command_runner = FakeCommandRunner(
        json.dumps(
            [
                {
                    "Name": "VirtualBox Host-Only Network",
                    "InterfaceDescription": "VirtualBox Host-Only Ethernet Adapter",
                    "Status": "Up",
                    "MacAddress": "00-11-22-33-44-55",
                    "IpAddress": "192.168.56.1",
                    "Gateway": "192.168.56.254",
                    "InterfaceMetric": 1,
                    "RouteMetric": 1,
                },
                {
                    "Name": "VPN",
                    "InterfaceDescription": "WireGuard Tunnel",
                    "Status": "Up",
                    "MacAddress": "00-11-22-33-44-66",
                    "IpAddress": "10.0.0.2",
                    "Gateway": "10.0.0.1",
                    "InterfaceMetric": 1,
                    "RouteMetric": 1,
                },
                {
                    "Name": "Wi-Fi",
                    "InterfaceDescription": "Intel(R) Wi-Fi 6 AX201 802.11ax",
                    "Status": "Up",
                    "MacAddress": "AA:BB:CC:DD:EE:01",
                    "IpAddress": "192.168.0.20",
                    "Gateway": "192.168.0.1",
                    "InterfaceMetric": 5,
                    "RouteMetric": 5,
                },
                {
                    "Name": "이더넷",
                    "InterfaceDescription": "Realtek Gaming 2.5GbE Family Controller",
                    "Status": "Up",
                    "MacAddress": "AA:BB:CC:DD:EE:FF",
                    "IpAddress": "192.168.0.10",
                    "Gateway": "192.168.0.1",
                    "InterfaceMetric": 25,
                    "RouteMetric": 25,
                },
            ]
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.network_info == PcNetworkInfo(
        adapter_name="이더넷",
        adapter_type="Ethernet",
        ip_address="192.168.0.10",
        mac_address="AA-BB-CC-DD-EE-FF",
        description="Realtek Gaming 2.5GbE Family Controller",
    )
    assert pc_info.ipv4_address == "192.168.0.10"
    assert pc_info.mac_address == "AA-BB-CC-DD-EE-FF"


def test_pc_info_network_selection_uses_wifi_when_ethernet_has_no_gateway() -> None:
    command_runner = FakeCommandRunner(
        json.dumps(
            [
                {
                    "Name": "이더넷",
                    "InterfaceDescription": "Realtek PCIe GbE Family Controller",
                    "Status": "Up",
                    "MacAddress": "AA-BB-CC-DD-EE-10",
                    "IpAddress": "192.168.0.10",
                    "Gateway": "",
                    "InterfaceMetric": 1,
                    "RouteMetric": 1,
                },
                {
                    "Name": "Wi-Fi",
                    "InterfaceDescription": "Intel(R) Wi-Fi 6 AX201 802.11ax",
                    "Status": "Up",
                    "MacAddress": "AA-BB-CC-DD-EE-20",
                    "IpAddress": "192.168.0.20",
                    "Gateway": "192.168.0.1",
                    "InterfaceMetric": 30,
                    "RouteMetric": 30,
                },
            ]
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.network_info is not None
    assert pc_info.network_info.adapter_type == "Wi-Fi"
    assert pc_info.network_info.ip_address == "192.168.0.20"
    assert pc_info.network_info.mac_address == "AA-BB-CC-DD-EE-20"


def test_pc_info_network_selection_excludes_apipa_ipv4() -> None:
    command_runner = FakeCommandRunner(
        json.dumps(
            [
                {
                    "Name": "이더넷",
                    "InterfaceDescription": "Realtek PCIe GbE Family Controller",
                    "Status": "Up",
                    "MacAddress": "AA-BB-CC-DD-EE-10",
                    "IpAddress": "169.254.10.20",
                    "Gateway": "192.168.0.1",
                    "InterfaceMetric": 1,
                    "RouteMetric": 1,
                }
            ]
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.network_info is None
    assert pc_info.ipv4_address is None
    assert pc_info.mac_address is None


def test_pc_info_network_selection_returns_none_when_no_adapter_matches() -> None:
    command_runner = FakeCommandRunner(
        json.dumps(
            [
                {
                    "Name": "Docker Desktop",
                    "InterfaceDescription": "Docker Virtual Ethernet",
                    "Status": "Up",
                    "MacAddress": "AA-BB-CC-DD-EE-10",
                    "IpAddress": "192.168.65.1",
                    "Gateway": "192.168.65.254",
                    "InterfaceMetric": 1,
                    "RouteMetric": 1,
                }
            ]
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.network_info is None


def test_pc_info_network_selection_handles_single_powershell_json_object() -> None:
    command_runner = FakeCommandRunner(
        json.dumps(
            {
                "Name": "Ethernet",
                "InterfaceDescription": "Intel(R) Ethernet Connection I219-LM",
                "Status": "Up",
                "MacAddress": "001122334455",
                "IpAddress": "192.168.10.20",
                "Gateway": "192.168.10.1",
                "InterfaceMetric": 10,
                "RouteMetric": 10,
            }
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    pc_info = reader.read()

    assert pc_info.network_info is not None
    assert pc_info.network_info.adapter_name == "Ethernet"
    assert pc_info.network_info.ip_address == "192.168.10.20"
    assert pc_info.network_info.mac_address == "00-11-22-33-44-55"


def test_pc_info_network_selection_uses_low_level_info_without_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        wmi_pc_info_reader,
        "read_active_network_info",
        lambda: PcNetworkInfo(
            adapter_name="Ethernet",
            adapter_type="Ethernet",
            ip_address="192.168.10.20",
            mac_address="00-11-22-33-44-55",
            description="Intel Ethernet",
        ),
    )
    command_runner = FakeCommandRunner(
        json.dumps(
            {
                "Name": "Wi-Fi",
                "InterfaceDescription": "Intel Wi-Fi",
                "Status": "Up",
                "MacAddress": "AA-BB-CC-DD-EE-FF",
                "IpAddress": "192.168.10.30",
                "Gateway": "192.168.10.1",
                "InterfaceMetric": 1,
                "RouteMetric": 1,
            }
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    network_info = reader._get_active_network_info()

    assert network_info == PcNetworkInfo(
        adapter_name="Ethernet",
        adapter_type="Ethernet",
        ip_address="192.168.10.20",
        mac_address="00-11-22-33-44-55",
        description="Intel Ethernet",
    )
    assert command_runner.commands == []


def test_read_active_network_info_prefers_friendly_name_over_raw_adapter_guid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "이더넷",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                True,
                adapter_name="{A3452B1D-8B3A-4EF6-A936-5F147DBE811D}",
                description="Realtek Gaming 2.5GbE Family Controller",
                gateway="192.168.0.1",
            )
        ],
    )

    network_info = network_identity_reader.read_active_network_info()

    assert network_info is not None
    assert network_info.adapter_name == "이더넷"
    assert network_info.description == "Realtek Gaming 2.5GbE Family Controller"


def test_read_active_network_info_uses_description_when_friendly_name_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                True,
                adapter_name=r"\DEVICE\TCPIP_{A3452B1D-8B3A-4EF6-A936-5F147DBE811D}",
                description="Realtek Gaming 2.5GbE Family Controller",
                gateway="192.168.0.1",
            )
        ],
    )

    network_info = network_identity_reader.read_active_network_info()

    assert network_info is not None
    assert network_info.adapter_name == "Realtek Gaming 2.5GbE Family Controller"


def test_read_active_network_info_uses_adapter_type_before_raw_guid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                True,
                adapter_name="{A3452B1D-8B3A-4EF6-A936-5F147DBE811D}",
                gateway="192.168.0.1",
            )
        ],
    )

    network_info = network_identity_reader.read_active_network_info()

    assert network_info is not None
    assert network_info.adapter_name == "Ethernet"
    assert network_info.description == "Ethernet"


def test_pc_info_network_selection_falls_back_to_wmi_when_powershell_fails() -> None:
    command_runner = FakeCommandRunner("not json")
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_NetworkAdapterConfiguration", None): [
                WmiItem(
                    IPEnabled=True,
                    Index="7",
                    Description="Intel(R) Wi-Fi 6 AX201 802.11ax",
                    IPAddress=["192.168.30.40"],
                    DefaultIPGateway=["192.168.30.1"],
                    MACAddress="AA:BB:CC:DD:EE:77",
                    IPConnectionMetric="55",
                )
            ],
            ("Win32_NetworkAdapter", None): [
                WmiItem(
                    Index="7",
                    NetConnectionID="Wi-Fi",
                    Name="Wi-Fi",
                    Description="Intel(R) Wi-Fi 6 AX201 802.11ax",
                    NetConnectionStatus=2,
                )
            ],
        },
        command_runner=command_runner,
    )

    pc_info = reader.read()

    assert pc_info.network_info == PcNetworkInfo(
        adapter_name="Wi-Fi",
        adapter_type="Wi-Fi",
        ip_address="192.168.30.40",
        mac_address="AA-BB-CC-DD-EE-77",
        description="Intel(R) Wi-Fi 6 AX201 802.11ax",
    )


def test_pc_info_network_selection_falls_back_to_powershell_when_low_level_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_low_level() -> PcNetworkInfo | None:
        raise OSError("GetAdaptersAddresses failed")

    monkeypatch.setattr(wmi_pc_info_reader, "read_active_network_info", fail_low_level)
    command_runner = FakeCommandRunner(
        json.dumps(
            {
                "Name": "Ethernet",
                "InterfaceDescription": "Intel(R) Ethernet Connection I219-LM",
                "Status": "Up",
                "MacAddress": "001122334455",
                "IpAddress": "192.168.10.20",
                "Gateway": "192.168.10.1",
                "InterfaceMetric": 10,
                "RouteMetric": 10,
            }
        )
    )
    reader = ControlledWmiPcInfoReader({}, command_runner=command_runner)

    network_info = reader._get_active_network_info()

    assert network_info is not None
    assert network_info.ip_address == "192.168.10.20"
    assert command_runner.commands
    assert command_runner.commands[0][0] == "powershell"


def test_get_adapters_addresses_candidate_selection_prefers_ethernet_over_wifi() -> None:
    selected = select_network_identity_candidate(
        [
            NetworkIdentityCandidate("100.64.0.1", "00:11:22:33:44:55", "Tailscale", IF_TYPE_ETHERNET_CSMACD, True, True, 5),
            NetworkIdentityCandidate("192.168.0.30", "aa:bb:cc:dd:ee:ff", "Wi-Fi", IF_TYPE_IEEE80211, True, True, 1),
            NetworkIdentityCandidate("192.168.0.20", "11-22-33-44-55-66", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, True, False, 1),
            NetworkIdentityCandidate("192.168.0.10", "aa:bb:cc:dd:ee:ff", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, True, True, 25),
        ]
    )

    assert selected is not None
    assert selected.ip == "192.168.0.10"
    assert normalize_mac_address(selected.mac) == "AA-BB-CC-DD-EE-FF"


def test_get_adapters_addresses_candidate_selection_uses_wifi_when_ethernet_is_invalid() -> None:
    selected = select_network_identity_candidate(
        [
            NetworkIdentityCandidate("192.168.0.20", "11-22-33-44-55-66", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, False, True, 1),
            NetworkIdentityCandidate("192.168.0.30", "aa:bb:cc:dd:ee:ff", "Wi-Fi", IF_TYPE_IEEE80211, True, True, 20),
        ]
    )

    assert selected is not None
    assert selected.friendly_name == "Wi-Fi"


def test_get_adapters_addresses_candidate_selection_excludes_gatewayless_and_virtual_adapters() -> None:
    selected = select_network_identity_candidate(
        [
            NetworkIdentityCandidate("192.168.0.10", "00:11:22:33:44:10", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, True, False, 1),
            NetworkIdentityCandidate("192.168.65.1", "00:11:22:33:44:20", "vEthernet Docker", IF_TYPE_ETHERNET_CSMACD, True, True, 1),
            NetworkIdentityCandidate("10.0.0.2", "00:11:22:33:44:30", "WireGuard Tunnel", IF_TYPE_ETHERNET_CSMACD, True, True, 1),
            NetworkIdentityCandidate("192.168.0.30", "00:11:22:33:44:40", "Wi-Fi", IF_TYPE_IEEE80211, True, True, 20),
        ]
    )

    assert selected is not None
    assert selected.friendly_name == "Wi-Fi"


def test_get_adapters_addresses_candidate_selection_prefers_low_metric_within_same_type() -> None:
    selected = select_network_identity_candidate(
        [
            NetworkIdentityCandidate("192.168.0.10", "00:11:22:33:44:10", "Ethernet A", IF_TYPE_ETHERNET_CSMACD, True, True, 25),
            NetworkIdentityCandidate("192.168.0.11", "00:11:22:33:44:11", "Ethernet B", IF_TYPE_ETHERNET_CSMACD, True, True, 5),
        ]
    )

    assert selected is not None
    assert selected.ip == "192.168.0.11"


def test_get_adapters_addresses_fast_adapter_list_filters_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.30",
                "00:11:22:33:44:30",
                "Wi-Fi",
                IF_TYPE_IEEE80211,
                True,
                True,
                5,
                gateway="192.168.0.1",
            ),
            NetworkIdentityCandidate("192.168.65.1", "00:11:22:33:44:65", "vEthernet Docker", IF_TYPE_ETHERNET_CSMACD, True, True, 1),
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "Ethernet",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                True,
                25,
                gateway="192.168.0.1",
            ),
            NetworkIdentityCandidate("192.168.0.11", "00:11:22:33:44:11", "Ethernet 2", IF_TYPE_ETHERNET_CSMACD, False, False, 1),
        ],
    )

    adapters = read_network_adapters_fast()

    assert [adapter.name for adapter in adapters] == ["Ethernet", "Wi-Fi", "Ethernet 2"]
    assert adapters[0].is_enabled is True
    assert adapters[0].gateway == "192.168.0.1"
    assert adapters[0].is_dhcp_enabled is None


def test_get_adapters_addresses_flags_include_gateway_and_dns() -> None:
    assert network_identity_reader.GAA_FLAGS & network_identity_reader.GAA_FLAG_INCLUDE_GATEWAYS
    assert network_identity_reader.GAA_FLAGS & network_identity_reader.GAA_FLAG_INCLUDE_PREFIX
    assert not network_identity_reader.GAA_FLAGS & network_identity_reader.GAA_FLAG_SKIP_DNS_SERVER


def test_network_adapter_fast_path_uses_candidate_gateway_without_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "Ethernet",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                True,
                adapter_name="{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}",
                ip_addresses=("192.168.0.10",),
                gateway="192.168.0.1",
                dns_servers=("8.8.8.8",),
                prefix_length=24,
            )
        ],
    )
    monkeypatch.setattr(network_identity_reader, "_read_tcpip_interface_config", lambda adapter_name: network_identity_reader._TcpipInterfaceConfig())

    adapter = read_network_adapters_fast()[0]

    assert adapter.gateway == "192.168.0.1"
    assert adapter.subnet_mask == "255.255.255.0"
    assert adapter.dns_servers == ("8.8.8.8",)
    assert adapter.is_dhcp_enabled is None


def test_network_adapter_fast_path_enriches_dhcp_registry_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.10",
                "00:11:22:33:44:10",
                "Ethernet",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                False,
                adapter_name=r"\DEVICE\TCPIP_{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}",
                ip_addresses=("192.168.0.10",),
            )
        ],
    )
    monkeypatch.setattr(
        network_identity_reader,
        "_read_tcpip_interface_config",
        lambda adapter_name: network_identity_reader._TcpipInterfaceConfig(
            is_dhcp_enabled=True,
            gateway="192.168.0.1",
            subnet_mask="255.255.255.0",
            dns_servers=("8.8.8.8", "1.1.1.1"),
        ),
    )

    adapter = read_network_adapters_fast()[0]

    assert adapter.gateway == "192.168.0.1"
    assert adapter.subnet_mask == "255.255.255.0"
    assert adapter.dns_servers == ("8.8.8.8", "1.1.1.1")
    assert adapter.is_dhcp_enabled is True


def test_network_adapter_fast_path_enriches_static_registry_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.20",
                "00:11:22:33:44:20",
                "Ethernet",
                IF_TYPE_ETHERNET_CSMACD,
                True,
                False,
                adapter_name="{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}",
            )
        ],
    )
    monkeypatch.setattr(
        network_identity_reader,
        "_read_tcpip_interface_config",
        lambda adapter_name: network_identity_reader._TcpipInterfaceConfig(
            is_dhcp_enabled=False,
            ip_addresses=("192.168.0.20",),
            gateway="192.168.0.1",
            subnet_mask="255.255.255.0",
            dns_servers=("203.246.75.1",),
        ),
    )

    adapter = read_network_adapters_fast()[0]

    assert adapter.ip_addresses == ("192.168.0.20",)
    assert adapter.gateway == "192.168.0.1"
    assert adapter.subnet_mask == "255.255.255.0"
    assert adapter.dns_servers == ("203.246.75.1",)
    assert adapter.is_dhcp_enabled is False


def test_network_adapter_fast_path_does_not_fail_when_enrichment_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_identity_reader,
        "_get_adapters_addresses_candidates",
        lambda: [
            NetworkIdentityCandidate(
                "192.168.0.30",
                "00:11:22:33:44:30",
                "Wi-Fi",
                IF_TYPE_IEEE80211,
                True,
                False,
                adapter_name="not-a-guid",
                ip_addresses=("192.168.0.30",),
            )
        ],
    )

    adapter = read_network_adapters_fast()[0]

    assert adapter.name == "Wi-Fi"
    assert adapter.gateway is None
    assert adapter.is_dhcp_enabled is None


def test_registry_adapter_guid_and_ipv4_helpers() -> None:
    assert _extract_adapter_guid(r"\DEVICE\TCPIP_{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}") == "{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}"
    assert _extract_adapter_guid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") == "{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}"
    assert _first_ipv4_from_registry_value(["", "0.0.0.0", "192.168.0.1"]) == "192.168.0.1"
    assert _ipv4_tuple_from_registry_value("8.8.8.8, 1.1.1.1; :: 0.0.0.0") == ("8.8.8.8", "1.1.1.1")


def test_wmi_reader_uses_cpu_registry_fast_path_without_processor_wmi() -> None:
    registry = FakeRegistry()
    registry.set_value(
        "HKEY_LOCAL_MACHINE",
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        "ProcessorNameString",
        "Intel Core from Registry",
    )
    reader = ControlledWmiPcInfoReader({}, registry=registry)

    assert reader._get_cpu_name() == "Intel Core from Registry"
    assert reader.wmi_call_counts.get(("Win32_Processor", None), 0) == 0


def test_wmi_reader_falls_back_to_processor_wmi_when_cpu_registry_is_missing() -> None:
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_Processor", None): [WmiItem(Name="Intel Core from WMI")],
        },
        registry=FakeRegistry(),
    )

    assert reader._get_cpu_name() == "Intel Core from WMI"
    assert reader.wmi_call_counts.get(("Win32_Processor", None), 0) == 1


def test_wmi_reader_reads_msft_physical_disk_once_for_disks() -> None:
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_DiskDrive", None): [
                WmiItem(
                    Model="Samsung SSD 970 EVO Plus 500GB",
                    SerialNumber="S4EWNX0M123456",
                    Size=str(500 * 1024**3),
                    InterfaceType="SCSI",
                    Index="0",
                )
            ],
            ("MSFT_Disk", r"root\Microsoft\Windows\Storage"): [
                WmiItem(Number=0, Model="Samsung SSD 970 EVO Plus 500GB", Size=str(500 * 1024**3), BusType=17),
            ],
            ("MSFT_PhysicalDisk", r"root\Microsoft\Windows\Storage"): [
                WmiItem(
                    FriendlyName="Samsung SSD 970 EVO Plus 500GB",
                    SerialNumber="S4EWNX0M123456",
                    MediaType=4,
                    BusType=17,
                    Size=str(500 * 1024**3),
                )
            ],
        }
    )

    disks = reader._get_disks()

    assert disks[0].display_type == "SSD (NVMe)"
    assert reader.wmi_call_counts[("MSFT_PhysicalDisk", r"root\Microsoft\Windows\Storage")] == 1


def test_memory_type_mapping_includes_lpddr3_code_27() -> None:
    assert _memory_type_from_code(27) == "LPDDR3"
    assert _memory_type_from_code(29) == "LPDDR3"
