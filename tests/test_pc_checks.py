from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from skhu_pc_management.application.use_cases.run_pc_checks import (
    BrowserHistoryCheck,
    InstalledProgramCheck,
    OfficeInstallCheck,
    PowerSettingsCheck,
    RecycleBinCheck,
    RunPcChecks,
)
from skhu_pc_management.domain.checks.models import (
    BrowserDataStatus,
    CheckCategory,
    CheckResult,
    CheckStatus,
    InstalledProgramInfo,
    PowerSettingsStatus,
    RecycleBinStatus,
)
from skhu_pc_management.infrastructure.windows.installed_program_reader import WindowsInstalledProgramReader
from skhu_pc_management.infrastructure.windows.power_settings_reader import WindowsPowerSettingsReader


class FakeInstalledProgramReader:
    def __init__(self) -> None:
        self.programs: dict[str, InstalledProgramInfo] = {}
        self.office_name: str | None = None
        self.program_reads: list[str] = []

    def get_program(self, program_id: str) -> InstalledProgramInfo | None:
        self.program_reads.append(program_id)
        return self.programs.get(program_id)

    def get_installed_office_name(self) -> str | None:
        return self.office_name


class FakeBrowserDataReader:
    def __init__(self) -> None:
        self.statuses: dict[str, BrowserDataStatus] = {}
        self.reads: list[str] = []

    def get_browser_data_status(self, browser_id: str) -> BrowserDataStatus:
        self.reads.append(browser_id)
        return self.statuses[browser_id]


class FakePowerSettingsReader:
    def __init__(self, status: PowerSettingsStatus) -> None:
        self.status = status
        self.read_count = 0

    def read_status(self) -> PowerSettingsStatus:
        self.read_count += 1
        return self.status


class FakeRecycleBinReader:
    def __init__(self, status: RecycleBinStatus) -> None:
        self.status = status

    def read_status(self) -> RecycleBinStatus:
        return self.status


class FakeCommandRunner:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        command_tuple = tuple(command)
        self.commands.append(command_tuple)
        return self.output


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], object] = {}
        self.subkeys: dict[tuple[str, str], list[str]] = {}

    def read_value(self, root: str, path: str, name: str) -> object | None:
        return self.values.get((root, path, name))

    def list_subkeys(self, root: str, path: str) -> list[str]:
        return self.subkeys.get((root, path), [])

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        raise AssertionError("PC checks must not write registry values")


class ExplodingCheck:
    def run(self) -> CheckResult:
        raise RuntimeError("check failed")


def test_run_pc_checks_returns_results_from_multiple_checks() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["chrome"] = InstalledProgramInfo("chrome", "Google Chrome", "1.2.3")
    browser_reader = FakeBrowserDataReader()
    browser_reader.statuses["chrome"] = BrowserDataStatus("chrome", size_bytes=100, path_exists=True)
    checks = [
        InstalledProgramCheck(program_reader, "chrome_install", "Chrome 설치/버전 확인", "chrome"),
        BrowserHistoryCheck(browser_reader, "chrome_history", "Chrome 기록 확인", "chrome"),
    ]

    results = RunPcChecks(checks).execute()

    assert [result.check_id for result in results] == ["chrome_install", "chrome_history"]
    assert all(result.status == CheckStatus.OK for result in results)


def test_run_pc_checks_keeps_running_when_one_check_fails() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["edge"] = InstalledProgramInfo("edge", "Microsoft Edge", "1.2.3")
    checks = [
        ExplodingCheck(),
        InstalledProgramCheck(program_reader, "edge_install", "Edge 설치/버전 확인", "edge"),
    ]

    results = RunPcChecks(checks).execute()

    assert results[0].status == CheckStatus.ERROR
    assert results[0].message == "check failed"
    assert results[1].status == CheckStatus.OK


def test_installed_program_check_reports_missing_as_warning() -> None:
    result = InstalledProgramCheck(
        FakeInstalledProgramReader(),
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
    ).run()

    assert result.status == CheckStatus.WARNING
    assert result.category == CheckCategory.PROGRAM


def test_office_check_reports_recommended_version_ok() -> None:
    reader = FakeInstalledProgramReader()
    reader.office_name = "Microsoft Office LTSC Professional Plus 2024"

    result = OfficeInstallCheck(reader).run()

    assert result.status == CheckStatus.OK
    assert result.detail == reader.office_name


def test_power_settings_check_reports_warning_when_timeout_is_enabled() -> None:
    reader = FakePowerSettingsReader(
        PowerSettingsStatus(
            monitor_timeout_ac="0x00000000",
            standby_timeout_ac="0x0000012c",
            hibernate_timeout_ac="0x00000000",
        )
    )

    result = PowerSettingsCheck(reader).run()

    assert result.status == CheckStatus.WARNING
    assert reader.read_count == 1


def test_recycle_bin_check_reports_non_empty_warning() -> None:
    result = RecycleBinCheck(FakeRecycleBinReader(RecycleBinStatus(item_count=2, size_bytes=2048))).run()

    assert result.status == CheckStatus.WARNING
    assert result.detail == "2 items"


def test_browser_history_check_reports_history_warning() -> None:
    reader = FakeBrowserDataReader()
    reader.statuses["edge"] = BrowserDataStatus("edge", size_bytes=6 * 1024 * 1024, path_exists=True)

    result = BrowserHistoryCheck(reader, "edge_history", "Edge 기록 확인", "edge").run()

    assert result.status == CheckStatus.WARNING
    assert reader.reads == ["edge"]


def test_power_settings_reader_builds_powercfg_commands() -> None:
    output = "Current AC Power Setting Index: 0x00000000"
    command_runner = FakeCommandRunner(output)
    reader = WindowsPowerSettingsReader(command_runner)

    status = reader.read_status()

    assert status.is_never is True
    assert command_runner.commands == [
        ("powercfg", "/q", "SCHEME_CURRENT", "SUB_VIDEO", "VIDEOIDLE"),
        ("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"),
        ("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "HIBERNATEIDLE"),
    ]


def test_installed_program_reader_uses_registry_port_for_office() -> None:
    registry = FakeRegistry()
    uninstall_root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry.subkeys[("HKEY_LOCAL_MACHINE", uninstall_root)] = ["office"]
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\office", "DisplayName")] = (
        "Microsoft Office LTSC Professional Plus 2021"
    )
    reader = WindowsInstalledProgramReader(registry)

    assert reader.get_installed_office_name() == "Microsoft Office LTSC Professional Plus 2021"


def test_installed_program_reader_uses_registry_path_for_potplayer(tmp_path: Path) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.path == str(exe)
