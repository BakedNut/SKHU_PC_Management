from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from skhu_pc_management.domain.checks.models import (
    CheckCategory,
    CheckResult,
    CheckStatus,
)
from skhu_pc_management.ports.browser_data_reader import BrowserDataReader
from skhu_pc_management.ports.check_provider import CheckProvider
from skhu_pc_management.ports.installed_program_reader import InstalledProgramReader
from skhu_pc_management.ports.latest_version_provider import LatestVersionProvider
from skhu_pc_management.ports.power_settings_reader import PowerSettingsReader
from skhu_pc_management.ports.recycle_bin_reader import RecycleBinReader
from skhu_pc_management.ports.scheduled_task_reader import ScheduledTaskReader


@dataclass(frozen=True)
class RunPcChecks:
    checks: Iterable[CheckProvider]

    def execute(self) -> list[CheckResult]:
        results: list[CheckResult] = []
        for check in self.checks:
            try:
                results.append(check.run())
            except Exception as exc:
                label = check.__class__.__name__
                results.append(
                    CheckResult(
                        check_id=label,
                        label=label,
                        category=CheckCategory.PROGRAM,
                        status=CheckStatus.ERROR,
                        message=f"점검 실행 중 오류가 발생했습니다: {exc}",
                    )
                )
        return results


@dataclass(frozen=True)
class InstalledProgramCheck:
    program_reader: InstalledProgramReader
    check_id: str
    label: str
    program_id: str

    def run(self) -> CheckResult:
        program = self.program_reader.get_program(self.program_id)
        if program is None:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.PROGRAM,
                status=CheckStatus.WARNING,
                message=f"{self.label} 항목이 설치되어 있지 않습니다.",
            )

        return CheckResult(
            check_id=self.check_id,
            label=self.label,
            category=CheckCategory.PROGRAM,
            status=CheckStatus.OK,
            message="설치되어 있습니다.",
            detail=program.version or "버전 정보 없음",
            raw_value=program,
        )


@dataclass(frozen=True)
class ProgramVersionCheck:
    program_reader: InstalledProgramReader
    latest_version_provider: LatestVersionProvider
    check_id: str
    label: str
    program_id: str
    display_name: str

    def run(self) -> CheckResult:
        program = self.program_reader.get_program(self.program_id)
        if program is None:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.PROGRAM,
                status=CheckStatus.WARNING,
                message=f"{self.display_name}이 설치되지 않았습니다.",
            )

        current_version = _normalize_local_version(self.program_id, program.version)
        if current_version is None:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.PROGRAM,
                status=CheckStatus.UNKNOWN,
                message="로컬 버전을 확인할 수 없습니다.",
                raw_value=program,
            )

        latest_version = self.latest_version_provider.get_latest_version(self.program_id)
        if not latest_version:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.PROGRAM,
                status=CheckStatus.UNKNOWN,
                message=f"{self.display_name} 최신 버전을 확인할 수 없습니다. 현재: {current_version} / 최신: 미확인",
                detail=f"현재: {current_version} / 최신: 미확인",
                raw_value=program,
            )

        comparison = _compare_program_versions(self.program_id, current_version, latest_version)
        if comparison is None:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.PROGRAM,
                status=CheckStatus.UNKNOWN,
                message=f"{self.display_name} 버전 정보를 비교할 수 없습니다. 현재: {current_version} / 최신: {latest_version}",
                detail=f"현재: {current_version} / 최신: {latest_version}",
                raw_value=program,
            )

        is_latest = comparison >= 0
        return CheckResult(
            check_id=self.check_id,
            label=self.label,
            category=CheckCategory.PROGRAM,
            status=CheckStatus.OK if is_latest else CheckStatus.WARNING,
            message=(
                f"{self.display_name}이 최신 버전입니다. 현재: {current_version} / 최신: {latest_version}"
                if is_latest
                else f"{self.display_name} 업데이트가 필요합니다. 현재: {current_version} / 최신: {latest_version}"
            ),
            detail=f"현재: {current_version} / 최신: {latest_version}",
            raw_value=program,
        )


@dataclass(frozen=True)
class OfficeInstallCheck:
    program_reader: InstalledProgramReader

    def run(self) -> CheckResult:
        office_name = self.program_reader.get_installed_office_name()
        if not office_name:
            return CheckResult(
                check_id="office_install",
                label="Office 설치 확인",
                category=CheckCategory.OFFICE,
                status=CheckStatus.WARNING,
                message="Office 2021 또는 2024가 설치되어 있지 않습니다.",
            )

        office_kind = _classify_office_version(office_name)
        display_name = _display_office_name(office_name)
        is_supported = office_kind in {"2021", "2024", "365"}
        if is_supported:
            message = f"{display_name}{_subject_particle(display_name)} 설치되어 있습니다."
        else:
            message = f"권장하지 않는 Office 버전이 설치되어 있습니다: {display_name}"
        return CheckResult(
            check_id="office_install",
            label="Office 설치 확인",
            category=CheckCategory.OFFICE,
            status=CheckStatus.OK if is_supported else CheckStatus.WARNING,
            message=message,
            detail=display_name,
            raw_value=office_name,
        )


@dataclass(frozen=True)
class PowerSettingsCheck:
    power_settings_reader: PowerSettingsReader

    def run(self) -> CheckResult:
        status = self.power_settings_reader.read_status()
        detail = status.detail_text
        if status.is_never is None or detail is None:
            return CheckResult(
                check_id="power_settings",
                label="전원 설정",
                category=CheckCategory.POWER,
                status=CheckStatus.UNKNOWN,
                message="전원 옵션 상태를 확인할 수 없습니다.",
                raw_value=status,
            )

        return CheckResult(
            check_id="power_settings",
            label="전원 설정",
            category=CheckCategory.POWER,
            status=CheckStatus.OK if status.is_never else CheckStatus.WARNING,
            message=(
                f"전원 옵션이 올바르게 설정되어 있습니다. {detail}"
                if status.is_never
                else f"전원 옵션 확인이 필요합니다. {detail}"
            ),
            detail=detail,
            raw_value=status,
        )


@dataclass(frozen=True)
class AutoShutdownScheduleCheck:
    scheduled_task_reader: ScheduledTaskReader
    task_name: str = "23시 자동 종료"

    def run(self) -> CheckResult:
        task = self.scheduled_task_reader.get_task(self.task_name)
        if task.error:
            return CheckResult(
                check_id="auto_shutdown_schedule",
                label="23시 자동종료 스케줄 점검",
                category=CheckCategory.SCHEDULED_TASK,
                status=CheckStatus.UNKNOWN,
                message="자동종료 스케줄 상태를 확인할 수 없습니다.",
                detail=task.error,
                raw_value=task,
            )

        if not task.exists:
            return CheckResult(
                check_id="auto_shutdown_schedule",
                label="23시 자동종료 스케줄 점검",
                category=CheckCategory.SCHEDULED_TASK,
                status=CheckStatus.WARNING,
                message="23시 자동종료 스케줄이 등록되어 있지 않습니다.",
                raw_value=task,
            )

        reasons = _auto_shutdown_schedule_mismatch_reasons(
            trigger_time=task.trigger_time,
            executable=task.executable,
            arguments=task.arguments,
        )
        if reasons:
            return CheckResult(
                check_id="auto_shutdown_schedule",
                label="23시 자동종료 스케줄 점검",
                category=CheckCategory.SCHEDULED_TASK,
                status=CheckStatus.WARNING,
                message="23시 자동종료 스케줄 설정이 올바르지 않습니다.",
                detail=", ".join(reasons),
                raw_value=task,
            )

        return CheckResult(
            check_id="auto_shutdown_schedule",
            label="23시 자동종료 스케줄 점검",
            category=CheckCategory.SCHEDULED_TASK,
            status=CheckStatus.OK,
            message="23시 자동종료 스케줄이 정상 등록되어 있습니다.",
            raw_value=task,
        )


@dataclass(frozen=True)
class RecycleBinCheck:
    recycle_bin_reader: RecycleBinReader

    def run(self) -> CheckResult:
        status = self.recycle_bin_reader.read_status()
        if status.is_empty is None:
            return CheckResult(
                check_id="recycle_bin",
                label="휴지통 상태",
                category=CheckCategory.RECYCLE_BIN,
                status=CheckStatus.UNKNOWN,
                message="휴지통 상태를 읽을 수 없습니다.",
                raw_value=status,
            )

        return CheckResult(
            check_id="recycle_bin",
            label="휴지통 상태",
            category=CheckCategory.RECYCLE_BIN,
            status=CheckStatus.OK if status.is_empty else CheckStatus.WARNING,
            message="휴지통이 비어 있습니다." if status.is_empty else "휴지통에 항목이 있습니다.",
            detail=None if status.item_count is None else f"{status.item_count}개 항목",
            raw_value=status,
        )


@dataclass(frozen=True)
class BrowserHistoryCheck:
    browser_data_reader: BrowserDataReader
    check_id: str
    label: str
    browser_id: str

    def run(self) -> CheckResult:
        status = self.browser_data_reader.get_browser_data_status(self.browser_id)
        if status.has_history is None:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.BROWSER_HISTORY,
                status=CheckStatus.UNKNOWN,
                message="브라우저 사용자 데이터 경로를 확인할 수 없습니다.",
                raw_value=status,
            )

        if not status.path_exists:
            return CheckResult(
                check_id=self.check_id,
                label=self.label,
                category=CheckCategory.BROWSER_HISTORY,
                status=CheckStatus.OK,
                message="사용자 데이터 폴더를 찾지 못해 기록 없음으로 처리했습니다.",
                detail=_browser_history_detail(status),
                raw_value=status,
            )

        return CheckResult(
            check_id=self.check_id,
            label=self.label,
            category=CheckCategory.BROWSER_HISTORY,
            status=CheckStatus.WARNING if status.has_history else CheckStatus.OK,
            message="브라우저 사용 기록이 존재합니다." if status.has_history else "기록 없음/양호",
            detail=_browser_history_detail(status),
            raw_value=status,
        )


RunPcChecksUseCase = RunPcChecks


def _browser_history_detail(status: object) -> str:
    size_bytes = getattr(status, "size_bytes", None)
    additional_profiles = getattr(status, "additional_profiles", ())
    skipped_count = getattr(status, "skipped_inaccessible_count", 0)

    details: list[str] = []
    if size_bytes is not None:
        details.append(f"{size_bytes} bytes")
    if additional_profiles:
        details.append("추가 프로필: " + ", ".join(additional_profiles))
    if skipped_count:
        details.append("일부 파일은 접근할 수 없어 건너뛰었습니다.")
    return " / ".join(details)


def _auto_shutdown_schedule_mismatch_reasons(
    trigger_time: str | None,
    executable: str | None,
    arguments: str | None,
) -> list[str]:
    reasons: list[str] = []
    if trigger_time != "22:55":
        reasons.append(f"시간={trigger_time or '없음'}")

    if not executable or not executable.strip():
        reasons.append("작업은 존재하지만 실행 명령을 읽을 수 없습니다.")
        executable_name = ""
    else:
        executable_name = executable.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if executable_name not in {"shutdown", "shutdown.exe"}:
        if executable_name:
            reasons.append(f"명령={executable}")

    if not arguments or not arguments.strip():
        reasons.append("작업은 존재하지만 실행 옵션을 읽을 수 없습니다.")
    else:
        argument_text = arguments.lower()
        if re.search(r"(^|\s)-s(\s|$)", argument_text) is None:
            reasons.append("옵션=-s 없음")
        if re.search(r"(^|\s)-t\s+300(\s|$)", argument_text) is None:
            reasons.append("옵션=-t 300 없음")

    return reasons


def compare_versions(current: str, latest: str) -> int | None:
    current_parts = _parse_version_parts(current)
    latest_parts = _parse_version_parts(latest)
    if current_parts is None or latest_parts is None:
        return None

    max_length = max(len(current_parts), len(latest_parts))
    current_parts = current_parts + (0,) * (max_length - len(current_parts))
    latest_parts = latest_parts + (0,) * (max_length - len(latest_parts))
    if current_parts == latest_parts:
        return 0
    return 1 if current_parts > latest_parts else -1


def _compare_program_versions(program_id: str, current: str, latest: str) -> int | None:
    if program_id == "potplayer" and (_is_date_version(current) != _is_date_version(latest)):
        return None
    return compare_versions(current, latest)


def _is_date_version(version: str) -> bool:
    return re.fullmatch(r"\d{6}", version.strip()) is not None


def _parse_version_parts(version: str | None) -> tuple[int, ...] | None:
    if not version:
        return None
    numbers = [int(match) for match in re.findall(r"\d+", version)]
    if not numbers:
        return None
    return tuple(numbers)


def _normalize_local_version(program_id: str, version: str | None) -> str | None:
    if not version:
        return None
    text = version.strip()
    if not text:
        return None
    if program_id == "potplayer":
        digits = "".join(re.findall(r"\d+", text))
        if not digits or digits in {"0", "000000", "00000000", "000000000"}:
            return None
        date_match = re.fullmatch(r"\d{6}", text) or re.search(r"(?<!\d)(\d{6})(?!\d)", text)
        if date_match:
            return date_match.group(0) if date_match.lastindex is None else date_match.group(1)
        return text
    if program_id == "bandizip":
        if text in {"0.0", "0.0.0.0"}:
            return None
        match = re.search(r"\d+(?:\.\d+)+", text)
        return match.group(0) if match else None
    if text in {"0.0", "0.0.0.0"} or "0, 0, 0, 0" in text:
        return None
    return text


def _classify_office_version(office_name: str) -> str:
    text = office_name.lower()
    if "2024" in text:
        return "2024"
    if "2021" in text:
        return "2021"
    if "365" in text or "microsoft 365" in text or "office 365" in text:
        return "365"
    return "other"


def _display_office_name(office_name: str) -> str:
    office_kind = _classify_office_version(office_name)
    if office_kind == "2024":
        return "Office 2024"
    if office_kind == "2021":
        return "Office 2021"
    if office_kind == "365":
        return "Office 365"
    return office_name.strip() or "Office"


def _subject_particle(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "가"
    last = stripped[-1]
    if last.isdigit():
        return "이" if last in {"0", "1", "3", "6", "7", "8"} else "가"
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return "이" if (code - 0xAC00) % 28 else "가"
    return "가"
