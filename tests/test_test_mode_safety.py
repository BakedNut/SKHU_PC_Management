from __future__ import annotations

from pathlib import Path
from typing import Sequence

from skhu_pc_management.application.safety import SafetyGuard, TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.application.use_cases.apply_settings import ApplySettings
from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.apply_taskbar_layout import ApplyTaskbarLayout
from skhu_pc_management.application.use_cases.launch_program import LaunchProgram
from skhu_pc_management.application.use_cases.rename_pc import RenamePc
from skhu_pc_management.application.use_cases.run_pc_maintenance import RunPcMaintenance
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
from skhu_pc_management.application.use_cases.system_settings_actions import SystemSettingsActions
from skhu_pc_management.domain.network.models import NetworkConfigResult, StaticIpConfig
from skhu_pc_management.domain.resources.models import TaskbarApplyResult


class RecordingRegistry:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, str, object, str]] = []

    def read_value(self, root: str, path: str, name: str) -> object | None:
        return None

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        self.writes.append((root, path, name, value, value_type))


class RecordingCommandRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return ""


class RecordingNetworkConfigurator:
    def __init__(self) -> None:
        self.static_requests: list[StaticIpConfig] = []
        self.dhcp_requests: list[str] = []

    def list_adapters(self):
        return []

    def apply_static_ip(self, config: StaticIpConfig) -> NetworkConfigResult:
        self.static_requests.append(config)
        return NetworkConfigResult("apply_static_ip", True, config.adapter_name, "applied")

    def set_dhcp(self, adapter_name: str) -> NetworkConfigResult:
        self.dhcp_requests.append(adapter_name)
        return NetworkConfigResult("set_dhcp", True, adapter_name, "dhcp")


class RecordingProductKeyProvider:
    def __init__(self) -> None:
        self.windows_requests: list[str | None] = []
        self.office_requests: list[str | None] = []

    def get_windows_product_key(self, edition: str | None = None) -> str | None:
        self.windows_requests.append(edition)
        return "windows-secret"

    def get_office_product_key(self, version: str | None = None) -> str | None:
        self.office_requests.append(version)
        return "office-secret"


class RecordingClipboard:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def set_text(self, text: str) -> None:
        self.texts.append(text)


class RecordingProcessLauncher:
    def __init__(self) -> None:
        self.launches: list[tuple[Path, tuple[str, ...]]] = []

    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        self.launches.append((executable, tuple(args)))


class RecordingOfficeLauncher:
    def __init__(self) -> None:
        self.calls = 0

    def launch_excel(self) -> str:
        self.calls += 1
        return "excel.exe"


class RecordingTaskbarConfigurator:
    def __init__(self) -> None:
        self.apply_requests: list[bool] = []

    def validate_resources(self):
        raise AssertionError("not used")

    def apply_taskbar_layout(self, dry_run: bool = True) -> TaskbarApplyResult:
        self.apply_requests.append(dry_run)
        return TaskbarApplyResult(True, "dry-run", dry_run=dry_run, planned_actions=("plan",))


class RecordingPcRenamer:
    def __init__(self) -> None:
        self.names: list[str] = []

    def rename(self, new_name: str) -> None:
        self.names.append(new_name)


class RecordingProgramLauncher:
    def __init__(self) -> None:
        self.program_ids: list[str] = []

    def launch_program(self, program_id: str) -> bool:
        self.program_ids.append(program_id)
        return True


class RecordingSystemMaintenance:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def empty_recycle_bin(self) -> int:
        self.calls.append(("empty_recycle_bin", None))
        return 0

    def delete_browser_history(self, browser_id: str) -> bool:
        self.calls.append(("delete_browser_history", browser_id))
        return True

    def set_power_never(self) -> None:
        self.calls.append(("set_power_never", None))

    def set_auto_shutdown_at_23(self) -> None:
        self.calls.append(("set_auto_shutdown_at_23", None))


class RecordingSystemSettingsOperator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def set_default_wallpaper(self) -> None:
        self.calls.append("set_default_wallpaper")

    def delete_edge_shortcuts(self) -> None:
        self.calls.append("delete_edge_shortcuts")

    def disable_password_expiration_for_all_users(self) -> None:
        self.calls.append("disable_password_expiration_for_all_users")


def test_test_mode_blocks_apply_settings_without_registry_or_commands() -> None:
    registry = RecordingRegistry()
    command_runner = RecordingCommandRunner()
    use_case = ApplySettings(registry, command_runner, safety_guard=SafetyGuard(test_mode=True))

    result = use_case.execute(["show_file_extensions"])

    assert result.results[0].status == "skipped"
    assert result.results[0].message == TEST_MODE_DISABLED_MESSAGE
    assert registry.writes == []
    assert command_runner.commands == []


def test_test_mode_blocks_network_changes_without_configurator_calls() -> None:
    configurator = RecordingNetworkConfigurator()
    guard = SafetyGuard(test_mode=True)
    config = StaticIpConfig("Ethernet", "192.168.0.10", "255.255.255.0", "192.168.0.1")

    static_result = ApplyStaticIp(configurator, safety_guard=guard).execute(config)
    dhcp_result = SetDhcp(configurator, safety_guard=guard).execute("Ethernet")

    assert static_result.success is False
    assert static_result.message == TEST_MODE_DISABLED_MESSAGE
    assert dhcp_result.success is False
    assert dhcp_result.message == TEST_MODE_DISABLED_MESSAGE
    assert configurator.static_requests == []
    assert configurator.dhcp_requests == []


def test_test_mode_blocks_activation_without_key_clipboard_or_process_calls() -> None:
    provider = RecordingProductKeyProvider()
    clipboard = RecordingClipboard()
    launcher = RecordingProcessLauncher()
    office_launcher = RecordingOfficeLauncher()
    guard = SafetyGuard(test_mode=True)

    windows_result = ActivateWindows(provider, clipboard, launcher, safety_guard=guard).execute("windows_11")
    office_result = ActivateOffice(provider, clipboard, office_launcher, safety_guard=guard).execute("2024")

    assert windows_result.success is False
    assert windows_result.message == TEST_MODE_DISABLED_MESSAGE
    assert office_result.success is False
    assert office_result.message == TEST_MODE_DISABLED_MESSAGE
    assert provider.windows_requests == []
    assert provider.office_requests == []
    assert clipboard.texts == []
    assert launcher.launches == []
    assert office_launcher.calls == 0


def test_test_mode_allows_taskbar_dry_run_but_blocks_real_apply() -> None:
    configurator = RecordingTaskbarConfigurator()
    use_case = ApplyTaskbarLayout(configurator, safety_guard=SafetyGuard(test_mode=True))

    dry_run = use_case.execute(dry_run=True)
    blocked = use_case.execute(dry_run=False)

    assert dry_run.success is True
    assert configurator.apply_requests == [True]
    assert blocked.success is False
    assert blocked.message == TEST_MODE_DISABLED_MESSAGE
    assert configurator.apply_requests == [True]


def test_test_mode_blocks_pc_rename_program_launch_and_maintenance_calls() -> None:
    guard = SafetyGuard(test_mode=True)
    renamer = RecordingPcRenamer()
    launcher = RecordingProgramLauncher()
    maintenance = RecordingSystemMaintenance()

    rename_result = RenamePc(renamer, safety_guard=guard).execute("PC-101")
    launch_result = LaunchProgram(launcher, safety_guard=guard).execute("chrome")
    recycle_result = RunPcMaintenance(maintenance, safety_guard=guard).empty_recycle_bin()
    browser_result = RunPcMaintenance(maintenance, safety_guard=guard).delete_browser_history("chrome")
    power_result = RunPcMaintenance(maintenance, safety_guard=guard).set_power_never()
    shutdown_result = RunPcMaintenance(maintenance, safety_guard=guard).set_auto_shutdown_at_23()

    assert rename_result.message == TEST_MODE_DISABLED_MESSAGE
    assert launch_result.message == TEST_MODE_DISABLED_MESSAGE
    assert recycle_result.message == TEST_MODE_DISABLED_MESSAGE
    assert browser_result.message == TEST_MODE_DISABLED_MESSAGE
    assert power_result.message == TEST_MODE_DISABLED_MESSAGE
    assert shutdown_result.message == TEST_MODE_DISABLED_MESSAGE
    assert renamer.names == []
    assert launcher.program_ids == []
    assert maintenance.calls == []


def test_test_mode_blocks_special_system_settings_actions() -> None:
    operator = RecordingSystemSettingsOperator()
    use_case = SystemSettingsActions(operator, safety_guard=SafetyGuard(test_mode=True))

    wallpaper = use_case.execute("set_default_wallpaper", "기본 배경화면 설정")
    edge = use_case.execute("delete_edge_shortcut", "바탕화면 Edge 바로가기 삭제")
    password = use_case.execute("disable_password_expiration", "사용자 계정 암호 만료 비활성화")

    assert wallpaper.message == TEST_MODE_DISABLED_MESSAGE
    assert edge.message == TEST_MODE_DISABLED_MESSAGE
    assert password.message == TEST_MODE_DISABLED_MESSAGE
    assert operator.calls == []
