from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo, LoadPcInfoUseCase
from skhu_pc_management.domain.pc.models import DiskInfo, MemoryModuleInfo, PcInfo
from skhu_pc_management.infrastructure.windows.wmi_pc_info_reader import WmiPcInfoReader


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
    Model: str | None = None
    Size: str | None = None
    MediaRotationRate: str | None = None
    SpecVersion: str | None = None


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
    reader = ControlledWmiPcInfoReader(
        {
            ("Win32_OperatingSystem", None): [
                WmiItem(Caption="Microsoft Windows 11 Pro", BuildNumber="26100", OSArchitecture="64-bit")
            ],
            ("Win32_Processor", None): [WmiItem(Name="Intel Core")],
            ("Win32_PhysicalMemory", None): [
                WmiItem(Capacity=str(16 * 1024**3), Speed="3200", SMBIOSMemoryType="26")
            ],
            ("Win32_VideoController", None): [WmiItem(Name="NVIDIA RTX", AdapterCompatibility="NVIDIA")],
            ("Win32_DiskDrive", None): [
                WmiItem(Model="Samsung NVMe SSD", Size=str(512 * 1024**3), MediaRotationRate="0")
            ],
            ("Win32_Tpm", r"root\CIMV2\Security\MicrosoftTpm"): [WmiItem(SpecVersion="2.0, 1.3")],
        },
        registry=registry,
    )

    pc_info = reader.read()

    assert pc_info.os_name == "Microsoft Windows 11 Pro"
    assert pc_info.windows_build == "26100"
    assert pc_info.windows_release == "24H2"
    assert pc_info.cpu_name == "Intel Core"
    assert pc_info.memory_gb == 16.0
    assert pc_info.memory_modules[0].memory_type == "DDR4"
    assert pc_info.gpu_names == ["NVIDIA RTX"]
    assert pc_info.disks == [DiskInfo(model="Samsung NVMe SSD", size_gb=512.0, disk_type="SSD")]
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

    assert pc_info.os_name == "Unknown"
    assert pc_info.cpu_name == "Unknown"
    assert pc_info.memory_gb is None
    assert pc_info.gpu_names == []
    assert pc_info.disks == []
    assert pc_info.tpm_installed is None
    assert pc_info.secure_boot_status == "Unknown"
    assert pc_info.boot_mode == "Unknown"
