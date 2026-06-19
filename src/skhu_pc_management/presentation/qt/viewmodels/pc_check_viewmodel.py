from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PcCheckViewModel:
    run_pc_checks_use_case: Any
    status_message: str = "PC 점검을 실행하지 않았습니다."
    result_rows: list[tuple[str, str, str]] = field(default_factory=list)
    installed_office_status_text: str = "미확인"
    power_option_status_text: str = "미확인"
    auto_shutdown_status_text: str = "미확인"
    is_busy: bool = False

    def run_checks(self) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "PC 점검 실행 중입니다..."
        try:
            results = self.run_pc_checks_use_case.execute()
            self.result_rows = [
                (result.label or result.name, _display_status(result.status), _display_message(result.message))
                for result in results
            ]
            self._update_summary_statuses(results)
            self.status_message = f"PC 점검 완료: {len(results)}개 항목"
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"PC 점검 실패: {exc}"
        finally:
            self.is_busy = False

    def _update_summary_statuses(self, results: list[Any]) -> None:
        for result in results:
            message = _display_message(result.message)
            status = _display_status(result.status)
            summary = message or status
            if result.check_id == "office_install":
                self.installed_office_status_text = summary
            elif result.check_id == "power_settings":
                self.power_option_status_text = summary
            elif result.check_id == "auto_shutdown_schedule":
                self.auto_shutdown_status_text = summary


_STATUS_LABELS = {
    "ok": "정상",
    "warning": "주의",
    "error": "오류",
    "unknown": "알 수 없음",
}

_MESSAGE_LABELS = {
    "Installed.": "설치됨",
    "Not installed.": "설치되지 않음",
    "Office 2021 or 2024 is not installed.": "Office 2021 또는 2024가 설치되어 있지 않음",
    "Recommended Office version installed.": "권장 Office 버전이 설치됨",
    "Unsupported Office version installed.": "권장하지 않는 Office 버전이 설치됨",
    "Power settings could not be read.": "전원 설정을 읽을 수 없음",
    "All AC power timeouts are disabled.": "AC 전원 시간 제한이 모두 비활성화됨",
    "One or more AC power timeouts are enabled.": "일부 AC 전원 시간 제한이 활성화됨",
    "Recycle bin status could not be read.": "휴지통 상태를 읽을 수 없음",
    "Recycle bin is empty.": "휴지통이 비어 있음",
    "Recycle bin contains items.": "휴지통에 항목이 있음",
    "Browser data path was not found.": "브라우저 데이터 경로를 찾을 수 없음",
    "Browser history data exists.": "브라우저 기록 데이터가 존재함",
    "Browser history data is small or absent.": "브라우저 기록이 없거나 크기가 작음",
}


def _display_status(status: object) -> str:
    value = getattr(status, "value", status)
    return _STATUS_LABELS.get(str(value), str(value))


def _display_message(message: str) -> str:
    return _MESSAGE_LABELS.get(message, message)
