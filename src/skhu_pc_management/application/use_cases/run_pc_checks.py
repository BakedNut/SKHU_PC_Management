from __future__ import annotations

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
from skhu_pc_management.ports.power_settings_reader import PowerSettingsReader
from skhu_pc_management.ports.recycle_bin_reader import RecycleBinReader


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
                        message=str(exc),
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
                message="Not installed.",
            )

        return CheckResult(
            check_id=self.check_id,
            label=self.label,
            category=CheckCategory.PROGRAM,
            status=CheckStatus.OK,
            message="Installed.",
            detail=program.version,
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
                message="Office 2021 or 2024 is not installed.",
            )

        is_recommended = "2021" in office_name or "2024" in office_name
        return CheckResult(
            check_id="office_install",
            label="Office 설치 확인",
            category=CheckCategory.OFFICE,
            status=CheckStatus.OK if is_recommended else CheckStatus.WARNING,
            message="Recommended Office version installed." if is_recommended else "Unsupported Office version installed.",
            detail=office_name,
            raw_value=office_name,
        )


@dataclass(frozen=True)
class PowerSettingsCheck:
    power_settings_reader: PowerSettingsReader

    def run(self) -> CheckResult:
        status = self.power_settings_reader.read_status()
        if status.is_never is None:
            return CheckResult(
                check_id="power_settings",
                label="전원 설정",
                category=CheckCategory.POWER,
                status=CheckStatus.UNKNOWN,
                message="Power settings could not be read.",
                raw_value=status,
            )

        return CheckResult(
            check_id="power_settings",
            label="전원 설정",
            category=CheckCategory.POWER,
            status=CheckStatus.OK if status.is_never else CheckStatus.WARNING,
            message="All AC power timeouts are disabled." if status.is_never else "One or more AC power timeouts are enabled.",
            raw_value=status,
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
                message="Recycle bin status could not be read.",
                raw_value=status,
            )

        return CheckResult(
            check_id="recycle_bin",
            label="휴지통 상태",
            category=CheckCategory.RECYCLE_BIN,
            status=CheckStatus.OK if status.is_empty else CheckStatus.WARNING,
            message="Recycle bin is empty." if status.is_empty else "Recycle bin contains items.",
            detail=None if status.item_count is None else f"{status.item_count} items",
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
                message="Browser data path was not found.",
                raw_value=status,
            )

        return CheckResult(
            check_id=self.check_id,
            label=self.label,
            category=CheckCategory.BROWSER_HISTORY,
            status=CheckStatus.WARNING if status.has_history else CheckStatus.OK,
            message="Browser history data exists." if status.has_history else "Browser history data is small or absent.",
            detail=f"{status.size_bytes} bytes",
            raw_value=status,
        )


RunPcChecksUseCase = RunPcChecks
