from __future__ import annotations

import base64
import threading
from collections.abc import Sequence
from pathlib import Path

from skhu_pc_management.application.use_cases.run_pc_checks import (
    AutoShutdownScheduleCheck,
    BrowserHistoryCheck,
    InstalledProgramCheck,
    OfficeInstallCheck,
    PowerSettingsCheck,
    ProgramVersionCheck,
    RecycleBinCheck,
    RunPcChecks,
    _classify_office_version,
    _display_office_name,
    _normalize_local_version,
    compare_versions,
)
from skhu_pc_management.domain.checks.models import (
    BrowserDataStatus,
    CheckCategory,
    CheckResult,
    CheckStatus,
    InstalledProgramInfo,
    PowerSettingsStatus,
    RecycleBinStatus,
    ScheduledTaskInfo,
    ac_timeout_display,
)
from skhu_pc_management.ports.auto_shutdown_cancel_shortcut import AutoShutdownCancelShortcutStatus
from skhu_pc_management.infrastructure.windows import installed_program_reader
from skhu_pc_management.infrastructure.windows.installed_program_reader import WindowsInstalledProgramReader
from skhu_pc_management.infrastructure.windows.installed_program_reader import (
    _extract_bandizip_version,
    _extract_potplayer_date_version,
    _get_potplayer_registry_version,
    _is_office_display_name,
    _parse_potplayer_history_version,
)
from skhu_pc_management.infrastructure.windows.latest_version_provider import (
    parse_latest_bandizip_version,
    parse_latest_chrome_version,
    parse_latest_edge_version,
    parse_latest_potplayer_version,
)
from skhu_pc_management.infrastructure.windows.power_settings_reader import WindowsPowerSettingsReader
from skhu_pc_management.infrastructure.windows.windows_scheduled_task_reader import (
    WindowsScheduledTaskReader,
    parse_scheduled_task_json,
)


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


class FakeLatestVersionProvider:
    def __init__(self) -> None:
        self.versions: dict[str, str | None] = {}
        self.reads: list[str] = []

    def get_latest_version(self, program_id: str) -> str | None:
        self.reads.append(program_id)
        return self.versions.get(program_id)


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


class FakeScheduledTaskReader:
    def __init__(self, task: ScheduledTaskInfo) -> None:
        self.task = task
        self.reads: list[str] = []

    def get_task(self, name: str) -> ScheduledTaskInfo:
        self.reads.append(name)
        return self.task


class FakeAutoShutdownCancelShortcut:
    def __init__(self, status: AutoShutdownCancelShortcutStatus) -> None:
        self.status = status
        self.check_count = 0

    def install(self) -> Path:
        return self.status.desktop_path

    def check(self) -> AutoShutdownCancelShortcutStatus:
        self.check_count += 1
        return self.status


class FakeCommandRunner:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        command_tuple = tuple(command)
        self.commands.append(command_tuple)
        return self.output


class FailingCommandRunner:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        raise self.error


def _decode_encoded_powershell_command(command: tuple[str, ...]) -> str:
    encoded = command[command.index("-EncodedCommand") + 1]
    return base64.b64decode(encoded).decode("utf-16le")


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


class MissingValueRegistry(FakeRegistry):
    def read_value(self, root: str, path: str, name: str) -> object | None:
        raise FileNotFoundError(name)


class ExplodingCheck:
    def run(self) -> CheckResult:
        raise RuntimeError("check failed")


class BarrierCheck:
    def __init__(self, check_id: str, barrier: threading.Barrier) -> None:
        self.check_id = check_id
        self.barrier = barrier

    def run(self) -> CheckResult:
        self.barrier.wait(timeout=3)
        return CheckResult(
            check_id=self.check_id,
            label=self.check_id,
            category=CheckCategory.PROGRAM,
            status=CheckStatus.OK,
            message="ok",
        )


def test_run_pc_checks_returns_results_from_multiple_checks() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["chrome"] = InstalledProgramInfo("chrome", "Google Chrome", "1.2.3")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["chrome"] = "1.2.3"
    browser_reader = FakeBrowserDataReader()
    browser_reader.statuses["chrome"] = BrowserDataStatus("chrome", size_bytes=100, path_exists=True)
    checks = [
        ProgramVersionCheck(program_reader, latest_provider, "chrome_install", "Chrome 설치/버전 확인", "chrome", "Chrome"),
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
    assert results[0].message == "점검 실행 중 오류가 발생했습니다: check failed"
    assert results[1].status == CheckStatus.OK


def test_run_pc_checks_executes_checks_in_parallel() -> None:
    barrier = threading.Barrier(2)
    checks = [
        BarrierCheck("first", barrier),
        BarrierCheck("second", barrier),
    ]

    results = RunPcChecks(checks).execute()

    assert [result.check_id for result in results] == ["first", "second"]
    assert [result.status for result in results] == [CheckStatus.OK, CheckStatus.OK]


def test_installed_program_check_reports_missing_as_warning() -> None:
    result = InstalledProgramCheck(
        FakeInstalledProgramReader(),
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
    ).run()

    assert result.status == CheckStatus.WARNING
    assert result.category == CheckCategory.PROGRAM


def test_program_version_check_reports_missing_program() -> None:
    result = ProgramVersionCheck(
        FakeInstalledProgramReader(),
        FakeLatestVersionProvider(),
        "chrome_install",
        "Chrome 설치/버전 확인",
        "chrome",
        "Chrome",
    ).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "Chrome이 설치되지 않았습니다."


def test_program_version_check_reports_latest_version_ok() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["chrome"] = InstalledProgramInfo("chrome", "Google Chrome", "1.2.10")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["chrome"] = "1.2.10"

    result = ProgramVersionCheck(program_reader, latest_provider, "chrome_install", "Chrome 설치/버전 확인", "chrome", "Chrome").run()

    assert result.status == CheckStatus.OK
    assert result.message == "Chrome이 최신 버전입니다. 현재: 1.2.10 / 최신: 1.2.10"


def test_program_version_check_reports_update_needed() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["edge"] = InstalledProgramInfo("edge", "Microsoft Edge", "1.2.9")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["edge"] = "1.2.10"

    result = ProgramVersionCheck(program_reader, latest_provider, "edge_install", "Edge 설치/버전 확인", "edge", "Edge").run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "Edge 업데이트가 필요합니다. 현재: 1.2.9 / 최신: 1.2.10"


def test_program_version_check_reports_latest_lookup_failure() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["chrome"] = InstalledProgramInfo("chrome", "Google Chrome", "120.0.1")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["chrome"] = None

    result = ProgramVersionCheck(program_reader, latest_provider, "chrome_install", "Chrome 설치/버전 확인", "chrome", "Chrome").run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "Chrome 최신 버전을 확인할 수 없습니다. 현재: 120.0.1 / 최신: 미확인"


def test_program_version_check_reports_local_version_failure() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["bandizip"] = InstalledProgramInfo("bandizip", "Bandizip", "0.0")

    result = ProgramVersionCheck(
        program_reader,
        FakeLatestVersionProvider(),
        "bandizip_install",
        "Bandizip 설치/버전 확인",
        "bandizip",
        "Bandizip",
    ).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "로컬 버전을 확인할 수 없습니다."


def test_compare_versions_uses_numeric_parts() -> None:
    assert compare_versions("1.2.10", "1.2.9") == 1
    assert compare_versions("1.2.9", "1.2.10") == -1
    assert compare_versions("1.2", "1.2.0") == 0


def test_program_version_check_compares_potplayer_date_versions() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["potplayer"] = InstalledProgramInfo("potplayer", "PotPlayer", "250101")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["potplayer"] = "250100"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
        "PotPlayer",
    ).run()

    assert result.status == CheckStatus.OK
    assert result.message == "PotPlayer이 최신 버전입니다. 현재: 250101 / 최신: 250100"


def test_program_version_check_rejects_potplayer_raw_file_version() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["potplayer"] = InstalledProgramInfo("potplayer", "PotPlayer", "0.0.0.0")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["potplayer"] = "250617"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
        "PotPlayer",
    ).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "로컬 버전을 확인할 수 없습니다."
    assert result.detail is None
    assert "0.0.0.0" not in result.message


def test_program_version_check_rejects_potplayer_zero_date_version() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["potplayer"] = InstalledProgramInfo("potplayer", "PotPlayer", "000000")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["potplayer"] = "260401"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
        "PotPlayer",
    ).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "로컬 버전을 확인할 수 없습니다."


def test_program_version_check_reports_potplayer_latest_with_valid_date() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["potplayer"] = InstalledProgramInfo("potplayer", "PotPlayer", "260401")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["potplayer"] = "260401"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
        "PotPlayer",
    ).run()

    assert result.status == CheckStatus.OK
    assert result.message == "PotPlayer이 최신 버전입니다. 현재: 260401 / 최신: 260401"


def test_program_version_check_reports_potplayer_update_needed_with_valid_date() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["potplayer"] = InstalledProgramInfo("potplayer", "PotPlayer", "260101")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["potplayer"] = "260401"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "potplayer_install",
        "PotPlayer 설치/버전 확인",
        "potplayer",
        "PotPlayer",
    ).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "PotPlayer 업데이트가 필요합니다. 현재: 260101 / 최신: 260401"


def test_latest_version_provider_parsers_do_not_require_network() -> None:
    assert parse_latest_chrome_version('[{"version":"126.0.1"}]') == "126.0.1"
    assert parse_latest_edge_version('[{"Product":"Stable","Releases":[{"ProductVersion":"126.0.2"}]}]') == "126.0.2"
    assert parse_latest_potplayer_version("release [250101]") == "250101"
    assert parse_latest_bandizip_version("<h1>Bandizip Version History</h1><td>v7.36</td>") == "7.36"


def test_local_version_parsers_for_potplayer_and_bandizip() -> None:
    assert _parse_potplayer_history_version("변경 사항 [250101]") == "250101"
    assert _parse_potplayer_history_version(b"\xef\xbb\xbf\xbf\xfe [260401]") == "260401"
    assert _extract_potplayer_date_version("260401") == "260401"
    assert _extract_potplayer_date_version("[260401]") == "260401"
    assert _extract_potplayer_date_version("26.04.01") == "260401"
    assert _extract_potplayer_date_version("1.7.260401.0") == "260401"
    assert _extract_potplayer_date_version("build [250617]") == "250617"
    assert _extract_potplayer_date_version("1.7.22260.0") is None
    assert _extract_potplayer_date_version("0.0.0.0") is None
    assert _extract_potplayer_date_version("0, 0, 0, 0") is None
    assert _extract_potplayer_date_version("000000") is None
    assert _extract_potplayer_date_version("0000") is None
    assert _extract_potplayer_date_version("0") is None
    assert _extract_potplayer_date_version("722260") is None
    assert _normalize_local_version("potplayer", "250617") == "250617"
    assert _normalize_local_version("potplayer", "1.7.22260.0") is None
    assert _normalize_local_version("potplayer", "0.0.0.0") is None
    assert _normalize_local_version("potplayer", "000000") is None
    assert _normalize_local_version("potplayer", "26.04.01") == "260401"
    assert _normalize_local_version("potplayer", "1.7.260401.0") == "260401"
    assert _extract_bandizip_version("7.36.0.1") == "7.36"
    assert _extract_bandizip_version("7.44") == "7.44"


def test_latest_bandizip_parser_ignores_asset_versions_before_history() -> None:
    payload = """
    <script src="/assets/app-v12.4.js"></script>
    <h1>Bandizip Version History</h1>
    <table><tr><td>v7.44</td><td>June 9, 2026</td></tr></table>
    """

    assert parse_latest_bandizip_version(payload) == "7.44"


def test_latest_bandizip_parser_reads_plain_text_history() -> None:
    payload = """
    Bandizip Version History

    Version

    Date

    Modifications

    v7.44

    June 9, 2026
    """

    assert parse_latest_bandizip_version(payload) == "7.44"


def test_latest_bandizip_parser_reads_html_history_cell() -> None:
    payload = '<h1>Bandizip Version History</h1><table><tr><td>v7.44</td></tr></table>'

    assert parse_latest_bandizip_version(payload) == "7.44"


def test_latest_bandizip_parser_returns_none_without_history_entry() -> None:
    payload = '<script src="/assets/app-v12.4.js"></script><h1>Bandizip Version History</h1><p>No entries</p>'

    assert parse_latest_bandizip_version(payload) is None


def test_bandizip_version_check_reports_latest_when_versions_match() -> None:
    program_reader = FakeInstalledProgramReader()
    program_reader.programs["bandizip"] = InstalledProgramInfo("bandizip", "Bandizip", "7.44")
    latest_provider = FakeLatestVersionProvider()
    latest_provider.versions["bandizip"] = "7.44"

    result = ProgramVersionCheck(
        program_reader,
        latest_provider,
        "bandizip_install",
        "Bandizip 설치/버전 확인",
        "bandizip",
        "Bandizip",
    ).run()

    assert result.status == CheckStatus.OK
    assert result.message == "Bandizip이 최신 버전입니다. 현재: 7.44 / 최신: 7.44"


def test_office_check_reports_recommended_version_ok() -> None:
    reader = FakeInstalledProgramReader()
    reader.office_name = "Microsoft Office LTSC Professional Plus 2024"

    result = OfficeInstallCheck(reader).run()

    assert result.status == CheckStatus.OK
    assert result.detail == "Office 2024"
    assert result.raw_value == reader.office_name
    assert result.message == "Office 2024가 설치되어 있습니다."


def test_office_check_reports_2021_display_name() -> None:
    reader = FakeInstalledProgramReader()
    reader.office_name = "Microsoft Office Professional Plus 2021"

    result = OfficeInstallCheck(reader).run()

    assert result.status == CheckStatus.OK
    assert result.detail == "Office 2021"
    assert result.message == "Office 2021이 설치되어 있습니다."


def test_office_check_reports_microsoft_365_display_name() -> None:
    reader = FakeInstalledProgramReader()
    reader.office_name = "Microsoft 365 Apps for enterprise"

    result = OfficeInstallCheck(reader).run()

    assert result.status == CheckStatus.OK
    assert result.detail == "Office 365"
    assert result.raw_value == "Microsoft 365 Apps for enterprise"
    assert result.message == "Office 365가 설치되어 있습니다."


def test_office_check_reports_unknown_office_as_warning() -> None:
    reader = FakeInstalledProgramReader()
    reader.office_name = "Microsoft Office Home and Student 2019"

    result = OfficeInstallCheck(reader).run()

    assert result.status == CheckStatus.WARNING
    assert result.detail == "Microsoft Office Home and Student 2019"
    assert result.message == "권장하지 않는 Office 버전이 설치되어 있습니다: Microsoft Office Home and Student 2019"


def test_office_display_helpers_classify_common_names() -> None:
    assert _classify_office_version("Microsoft Office LTSC Professional Plus 2024") == "2024"
    assert _classify_office_version("Microsoft Office Professional Plus 2021") == "2021"
    assert _classify_office_version("Microsoft 365 Apps for business") == "365"
    assert _display_office_name("Microsoft Office 365 ProPlus") == "Office 365"


def test_office_check_reports_missing_in_korean() -> None:
    result = OfficeInstallCheck(FakeInstalledProgramReader()).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "Office 2021 또는 2024가 설치되어 있지 않습니다."


def test_office_display_name_detection_includes_365_without_false_positives() -> None:
    assert _is_office_display_name("Microsoft 365 Apps for enterprise") is True
    assert _is_office_display_name("Microsoft 365 Apps for business") is True
    assert _is_office_display_name("Microsoft Office 365 ProPlus") is True
    assert _is_office_display_name("Microsoft Office LTSC Professional Plus 2024") is True
    assert _is_office_display_name("Microsoft Office Professional Plus 2021") is True
    assert _is_office_display_name("Microsoft Teams") is False
    assert _is_office_display_name("Microsoft Edge") is False


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
    assert result.message == "전원 옵션 확인이 필요합니다. 화면 끄기: 안 함, 절전: 5분, 최대 절전: 안 함"
    assert result.detail == "화면 끄기: 안 함, 절전: 5분, 최대 절전: 안 함"
    assert reader.read_count == 1


def test_powercfg_timeout_display_converts_zero_to_never() -> None:
    assert ac_timeout_display("0x00000000") == "안 함"


def test_powercfg_timeout_display_converts_seconds_to_minutes() -> None:
    assert ac_timeout_display("0x00000258") == "10분"


def test_power_settings_check_reports_ok_when_all_values_are_zero() -> None:
    reader = FakePowerSettingsReader(
        PowerSettingsStatus(
            monitor_timeout_ac="0x00000000",
            standby_timeout_ac="0x00000000",
            hibernate_timeout_ac="0x00000000",
        )
    )

    result = PowerSettingsCheck(reader).run()

    assert result.status == CheckStatus.OK
    assert result.message == "전원 옵션이 올바르게 설정되어 있습니다. 화면 끄기: 안 함, 절전: 안 함, 최대 절전: 안 함"


def test_power_settings_check_reports_unknown_when_value_is_missing_or_invalid() -> None:
    reader = FakePowerSettingsReader(
        PowerSettingsStatus(
            monitor_timeout_ac="0x00000000",
            standby_timeout_ac=None,
            hibernate_timeout_ac="not-a-hex-value",
        )
    )

    result = PowerSettingsCheck(reader).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "전원 옵션 상태를 확인할 수 없습니다."


def test_auto_shutdown_schedule_check_reports_ok_for_matching_task() -> None:
    task = ScheduledTaskInfo(
        name="23시 자동 종료",
        exists=True,
        trigger_time="22:55",
        executable=r"C:\Windows\System32\shutdown.exe",
        arguments='-s -t 300 -c "원치 않는 경우 바탕화면의 종료 취소를 실행해주세요"',
    )
    reader = FakeScheduledTaskReader(task)
    shortcut = FakeAutoShutdownCancelShortcut(
        AutoShutdownCancelShortcutStatus(
            source_path=Path("resources/23시 자동종료 취소.lnk"),
            desktop_path=Path("Desktop/23시 자동종료 취소.lnk"),
            source_exists=True,
            desktop_exists=True,
            matches=True,
        )
    )

    result = AutoShutdownScheduleCheck(reader, shortcut).run()

    assert result.status == CheckStatus.OK
    assert result.message == "23시 자동종료 스케줄과 취소 바로가기가 정상입니다."
    assert reader.reads == ["23시 자동 종료"]
    assert shortcut.check_count == 1


def test_auto_shutdown_schedule_check_reports_warning_when_shortcut_is_missing() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="shutdown.exe", arguments="-s -t 300")
    shortcut = FakeAutoShutdownCancelShortcut(
        AutoShutdownCancelShortcutStatus(
            source_path=Path("resources/23시 자동종료 취소.lnk"),
            desktop_path=Path("Desktop/23시 자동종료 취소.lnk"),
            source_exists=True,
            desktop_exists=False,
            matches=False,
            error="바탕화면에 23시 자동종료 취소.lnk가 없습니다.",
        )
    )

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task), shortcut).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "바탕화면에 23시 자동종료 취소.lnk가 없습니다."


def test_auto_shutdown_schedule_check_reports_warning_when_shortcut_source_is_missing() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="shutdown.exe", arguments="-s -t 300")
    shortcut = FakeAutoShutdownCancelShortcut(
        AutoShutdownCancelShortcutStatus(
            source_path=Path("resources/23시 자동종료 취소.lnk"),
            desktop_path=Path("Desktop/23시 자동종료 취소.lnk"),
            source_exists=False,
            desktop_exists=False,
            matches=False,
            error="자동종료 취소 바로가기 리소스를 찾을 수 없습니다.",
        )
    )

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task), shortcut).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "자동종료 취소 바로가기 리소스를 찾을 수 없습니다."


def test_auto_shutdown_schedule_check_reports_warning_when_shortcut_differs() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="shutdown.exe", arguments="-s -t 300")
    shortcut = FakeAutoShutdownCancelShortcut(
        AutoShutdownCancelShortcutStatus(
            source_path=Path("resources/23시 자동종료 취소.lnk"),
            desktop_path=Path("Desktop/23시 자동종료 취소.lnk"),
            source_exists=True,
            desktop_exists=True,
            matches=False,
            error="바탕화면의 23시 자동종료 취소.lnk가 리소스 원본과 다릅니다.",
        )
    )

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task), shortcut).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "바탕화면의 23시 자동종료 취소.lnk가 리소스 원본과 다릅니다."


def test_auto_shutdown_schedule_check_reports_warning_when_task_is_missing() -> None:
    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(ScheduledTaskInfo("23시 자동 종료", exists=False))).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "23시 자동종료 스케줄이 등록되어 있지 않습니다."


def test_auto_shutdown_schedule_check_reports_warning_for_wrong_trigger_time() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="23:00", executable="shutdown.exe", arguments="-s -t 300")

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.WARNING
    assert "시간=23:00" in (result.detail or "")


def test_auto_shutdown_schedule_check_reports_warning_for_wrong_executable() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="notepad.exe", arguments="-s -t 300")

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.WARNING
    assert "명령=notepad.exe" in (result.detail or "")


def test_auto_shutdown_schedule_check_reports_warning_for_missing_shutdown_arguments() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="shutdown.exe", arguments="-t 300")

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.WARNING
    assert "옵션=-s 없음" in (result.detail or "")


def test_auto_shutdown_schedule_check_reports_clear_detail_when_action_is_missing() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable=None, arguments="-s -t 300")

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.WARNING
    assert "작업은 존재하지만 실행 명령을 읽을 수 없습니다." in (result.detail or "")


def test_auto_shutdown_schedule_check_reports_clear_detail_when_arguments_are_missing() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=True, trigger_time="22:55", executable="shutdown.exe", arguments=None)

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.WARNING
    assert "작업은 존재하지만 실행 옵션을 읽을 수 없습니다." in (result.detail or "")


def test_auto_shutdown_schedule_check_reports_unknown_when_reader_fails() -> None:
    task = ScheduledTaskInfo("23시 자동 종료", exists=False, error="PowerShell failed")

    result = AutoShutdownScheduleCheck(FakeScheduledTaskReader(task)).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "자동종료 스케줄 상태를 확인할 수 없습니다."


def test_parse_scheduled_task_json_handles_exists_false() -> None:
    task = parse_scheduled_task_json("23시 자동 종료", '{"Exists": false, "TaskName": "23시 자동 종료"}')

    assert task.exists is False
    assert task.error is None
    assert task.raw == {"Exists": False, "TaskName": "23시 자동 종료"}


def test_windows_scheduled_task_reader_returns_missing_task_without_error() -> None:
    runner = FakeCommandRunner('{"Exists": false, "TaskName": "23시 자동 종료"}')

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is False
    assert task.error is None


def test_windows_scheduled_task_reader_script_emits_exists_false_for_missing_task() -> None:
    runner = FakeCommandRunner('{"Exists": false, "TaskName": "23시 자동 종료"}')

    WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    script = _decode_encoded_powershell_command(runner.commands[0])
    assert "Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue" in script
    assert "Exists = $false" in script
    assert "Exists = $true" in script


def test_windows_scheduled_task_reader_fallback_maps_task_not_found_error_to_missing() -> None:
    runner = FailingCommandRunner(RuntimeError("No MSFT_ScheduledTask objects found with property 'TaskName'"))

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is False
    assert task.error is None


def test_parse_scheduled_task_json_failure_remains_error() -> None:
    task = parse_scheduled_task_json("23시 자동 종료", "{bad json")

    assert task.exists is False
    assert task.error is not None
    assert "ScheduledTasks JSON parse failed" in task.error


def test_parse_scheduled_task_json_empty_output_remains_missing_without_error() -> None:
    task = parse_scheduled_task_json("23시 자동 종료", "")

    assert task.exists is False
    assert task.error is None


def test_recycle_bin_check_reports_non_empty_warning() -> None:
    result = RecycleBinCheck(FakeRecycleBinReader(RecycleBinStatus(item_count=2, size_bytes=2048))).run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "휴지통에 항목이 있습니다."
    assert result.detail == "2개 항목"


def test_recycle_bin_check_reports_unknown_in_korean() -> None:
    result = RecycleBinCheck(FakeRecycleBinReader(RecycleBinStatus(item_count=None))).run()

    assert result.status == CheckStatus.UNKNOWN
    assert result.message == "휴지통 상태를 읽을 수 없습니다."


def test_browser_history_check_reports_history_warning() -> None:
    reader = FakeBrowserDataReader()
    reader.statuses["edge"] = BrowserDataStatus("edge", size_bytes=6 * 1024 * 1024, path_exists=True)

    result = BrowserHistoryCheck(reader, "edge_history", "Edge 기록 확인", "edge").run()

    assert result.status == CheckStatus.WARNING
    assert result.message == "브라우저 사용 기록이 존재합니다."
    assert reader.reads == ["edge"]


def test_browser_history_check_reports_missing_user_data_as_ok() -> None:
    reader = FakeBrowserDataReader()
    reader.statuses["chrome"] = BrowserDataStatus("chrome", size_bytes=0, path_exists=False)

    result = BrowserHistoryCheck(reader, "chrome_history", "Chrome 기록 확인", "chrome").run()

    assert result.status == CheckStatus.OK
    assert result.message == "사용자 데이터 폴더를 찾지 못해 기록 없음으로 처리했습니다."


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


def test_power_settings_reader_parses_korean_powercfg_prefix() -> None:
    output = "현재 AC 전원 설정 색인: 0x00000258"
    command_runner = FakeCommandRunner(output)
    reader = WindowsPowerSettingsReader(command_runner)

    status = reader.read_status()

    assert status.monitor_timeout_ac == "0x00000258"
    assert status.standby_timeout_ac == "0x00000258"
    assert status.hibernate_timeout_ac == "0x00000258"
    assert status.detail_text == "화면 끄기: 10분, 절전: 10분, 최대 절전: 10분"


def test_power_settings_reader_returns_unknown_when_output_cannot_be_parsed() -> None:
    command_runner = FakeCommandRunner("no power setting index")
    reader = WindowsPowerSettingsReader(command_runner)

    status = reader.read_status()

    assert status.monitor_timeout_ac is None
    assert PowerSettingsCheck(FakePowerSettingsReader(status)).run().status == CheckStatus.UNKNOWN


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


def test_installed_program_reader_resolves_potplayer_exe_from_registry_directory(tmp_path: Path) -> None:
    install_dir = tmp_path / "PotPlayer"
    install_dir.mkdir()
    exe = install_dir / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    history_dir = install_dir / "History"
    history_dir.mkdir()
    (history_dir / "Korean.txt").write_text("changes [260401]", encoding="ascii")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(install_dir)
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.path == str(exe)
    assert program.version == "260401"


def test_installed_program_reader_skips_potplayer_registry_directory_without_exe_and_uses_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "RegistryPotPlayer"
    registry_dir.mkdir()
    fallback_dir = tmp_path / "FallbackPotPlayer"
    fallback_dir.mkdir()
    fallback_exe = fallback_dir / "PotPlayerMini.exe"
    fallback_exe.write_text("fake exe", encoding="utf-8")
    history_dir = fallback_dir / "History"
    history_dir.mkdir()
    (history_dir / "Korean.txt").write_text("changes [250617]", encoding="ascii")
    monkeypatch.setitem(installed_program_reader._PROGRAM_PATHS, "potplayer", (str(fallback_exe),))
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(registry_dir)
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.path == str(fallback_exe)
    assert program.version == "250617"


def test_installed_program_reader_uses_potplayer_registry_version(tmp_path: Path) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "Version")] = "260401"
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version == "260401"


def test_installed_program_reader_uses_potplayer_uninstall_version_fallback(tmp_path: Path) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    uninstall_root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry.subkeys[("HKEY_LOCAL_MACHINE", uninstall_root)] = ["potplayer"]
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\potplayer", "DisplayName")] = "PotPlayer-64 bit"
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\potplayer", "DisplayVersion")] = "260401"
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version == "260401"


def test_installed_program_reader_ignores_invalid_potplayer_registry_version(tmp_path: Path) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "DisplayVersion")] = "0.0.0.0"
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version is None


def test_installed_program_reader_ignores_invalid_potplayer_uninstall_version(monkeypatch) -> None:
    monkeypatch.setitem(installed_program_reader._PROGRAM_PATHS, "potplayer", ())
    registry = FakeRegistry()
    uninstall_root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry.subkeys[("HKEY_LOCAL_MACHINE", uninstall_root)] = ["potplayer"]
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\potplayer", "DisplayName")] = "PotPlayer-64 bit"
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\potplayer", "DisplayVersion")] = "1.7.22260.0"
    reader = WindowsInstalledProgramReader(registry)

    assert reader.get_program("potplayer") is None


def test_potplayer_registry_version_helper_prefers_direct_version() -> None:
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "Version")] = "260401"

    assert _get_potplayer_registry_version(registry) == "260401"


def test_installed_program_reader_uses_potplayer_history_before_registry(tmp_path: Path) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    history_dir = tmp_path / "History"
    history_dir.mkdir()
    (history_dir / "Korean.txt").write_text("changes [250701]", encoding="ascii")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "Version")] = "250617"
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version == "250701"


def test_installed_program_reader_does_not_use_file_version_text_when_potplayer_date_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    monkeypatch.setattr(installed_program_reader, "_get_file_version", lambda path: "1.7.22260.0")
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version is None


def test_installed_program_reader_extracts_potplayer_date_from_embedded_file_version(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    monkeypatch.setattr(installed_program_reader, "_get_file_version", lambda path: "1.7.260401.0")
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version == "260401"


def test_installed_program_reader_prefers_potplayer_file_date_before_registry_version(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "PotPlayerMini64.exe"
    exe.write_text("fake exe", encoding="utf-8")
    registry = FakeRegistry()
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "ProgramPath")] = str(exe)
    registry.values[("HKEY_LOCAL_MACHINE", r"SOFTWARE\DAUM\PotPlayer64", "Version")] = "250617"
    monkeypatch.setattr(installed_program_reader, "_get_file_version", lambda path: "1.7.260401.0")
    reader = WindowsInstalledProgramReader(registry)

    program = reader.get_program("potplayer")

    assert program is not None
    assert program.version == "260401"


def test_installed_program_reader_treats_missing_program_registry_keys_as_not_installed(monkeypatch) -> None:
    monkeypatch.setitem(installed_program_reader._PROGRAM_PATHS, "potplayer", ())
    reader = WindowsInstalledProgramReader(MissingValueRegistry())

    assert reader.get_program("potplayer") is None


def test_installed_program_reader_skips_unreadable_office_display_names() -> None:
    class PartiallyFailingRegistry(FakeRegistry):
        def read_value(self, root: str, path: str, name: str) -> object | None:
            if path.endswith(r"\bad"):
                raise OSError("missing DisplayName")
            return self.values.get((root, path, name))

    registry = PartiallyFailingRegistry()
    uninstall_root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry.subkeys[("HKEY_LOCAL_MACHINE", uninstall_root)] = ["bad", "office"]
    registry.values[("HKEY_LOCAL_MACHINE", rf"{uninstall_root}\office", "DisplayName")] = (
        "Microsoft Office LTSC Professional Plus 2024"
    )
    reader = WindowsInstalledProgramReader(registry)

    assert reader.get_installed_office_name() == "Microsoft Office LTSC Professional Plus 2024"
