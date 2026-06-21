from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo, LoadPcInfoUseCase
from skhu_pc_management.domain.pc.models import DiskInfo, MemoryModuleInfo, PcInfo
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
    NetworkIdentityCandidate,
    normalize_mac_address,
    select_network_identity_candidate,
)
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

    def _wmi_items(self, wmi_class: str, namespace: str | None = None) -> list[Any]:
        return self.wmi_items_by_class.get((wmi_class, namespace), [])

    def _read_dxgi_gpu_info(self) -> tuple[str, str, list[str]] | None:
        return None

    def _read_network_identity(self) -> tuple[str, str] | None:
        return None


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
                    Caption="Realtek Ethernet",
                    Description="Realtek Gaming 2.5GbE Family Controller",
                    IPAddress=["192.168.0.10"],
                    DefaultIPGateway=["192.168.0.1"],
                    MACAddress="AA-BB-CC-DD-EE-FF",
                    IPConnectionMetric="25",
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
    assert command_runner.commands == [("bcdedit", "/enum", "{current}")]


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
            name="Wi-Fi",
            description="Wi-Fi",
            ipv4_address="192.168.0.20",
            has_gateway=True,
            metric=10,
            is_ethernet=False,
        ),
        _NetworkCandidate(
            name="Ethernet",
            description="Realtek",
            ipv4_address="192.168.0.10",
            has_gateway=True,
            metric=25,
            is_ethernet=True,
        ),
        _NetworkCandidate(
            name="Ethernet 2",
            description="Realtek",
            ipv4_address="192.168.0.11",
            has_gateway=False,
            metric=5,
            is_ethernet=True,
        ),
    ]

    selected = _select_network_candidate(candidates)

    assert selected is not None
    assert selected.ipv4_address == "192.168.0.10"


def test_get_adapters_addresses_candidate_selection_and_mac_formatting() -> None:
    selected = select_network_identity_candidate(
        [
            NetworkIdentityCandidate("100.64.0.1", "00:11:22:33:44:55", "Tailscale", IF_TYPE_ETHERNET_CSMACD, True, True, 5),
            NetworkIdentityCandidate("192.168.0.30", "aa:bb:cc:dd:ee:ff", "Wi-Fi", 71, True, True, 1),
            NetworkIdentityCandidate("192.168.0.20", "11-22-33-44-55-66", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, True, False, 1),
            NetworkIdentityCandidate("192.168.0.10", "aa:bb:cc:dd:ee:ff", "Realtek Ethernet", IF_TYPE_ETHERNET_CSMACD, True, True, 25),
        ]
    )

    assert selected is not None
    assert selected.ip == "192.168.0.10"
    assert normalize_mac_address(selected.mac) == "AA-BB-CC-DD-EE-FF"


def test_memory_type_mapping_includes_lpddr3_code_27() -> None:
    assert _memory_type_from_code(27) == "LPDDR3"
    assert _memory_type_from_code(29) == "LPDDR3"
