from __future__ import annotations

from pathlib import Path
from typing import Sequence

from skhu_pc_management.application.safety import SafetyGuard, TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.application.use_cases.apply_settings import ApplySettings
from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.apply_taskbar_layout import ApplyTaskbarLayout
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
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


class RecordingTaskbarConfigurator:
    def __init__(self) -> None:
        self.apply_requests: list[bool] = []

    def validate_resources(self):
        raise AssertionError("not used")

    def apply_taskbar_layout(self, dry_run: bool = True) -> TaskbarApplyResult:
        self.apply_requests.append(dry_run)
        return TaskbarApplyResult(True, "dry-run", dry_run=dry_run, planned_actions=("plan",))


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
    guard = SafetyGuard(test_mode=True)

    windows_result = ActivateWindows(provider, clipboard, launcher, safety_guard=guard).execute("windows_11")
    office_result = ActivateOffice(provider, clipboard, launcher, safety_guard=guard).execute("2024")

    assert windows_result.success is False
    assert windows_result.message == TEST_MODE_DISABLED_MESSAGE
    assert office_result.success is False
    assert office_result.message == TEST_MODE_DISABLED_MESSAGE
    assert provider.windows_requests == []
    assert provider.office_requests == []
    assert clipboard.texts == []
    assert launcher.launches == []


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
