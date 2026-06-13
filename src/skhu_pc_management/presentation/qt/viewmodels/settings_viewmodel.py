from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skhu_pc_management.domain.settings.definitions import DEFAULT_SETTING_DEFINITIONS, SettingDefinition


@dataclass
class SettingsViewModel:
    check_settings_status_use_case: Any
    apply_settings_use_case: Any
    definitions: tuple[SettingDefinition, ...] = DEFAULT_SETTING_DEFINITIONS
    status_message: str = "설정 상태를 확인하지 않았습니다."
    result_rows: list[tuple[str, str, str]] = field(default_factory=list)
    is_busy: bool = False

    def check_status(self, setting_ids: list[str]) -> None:
        self.is_busy = True
        self.status_message = "설정 상태 확인 중입니다..."
        try:
            statuses = self.check_settings_status_use_case.execute(setting_ids)
            self.result_rows = [
                (status.label or status.name, status.status_text, _format_value(status.actual_value))
                for status in statuses
            ]
            self.status_message = "설정 상태 확인이 완료되었습니다."
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"설정 상태 확인 실패: {exc}"
        finally:
            self.is_busy = False

    def apply_selected(self, setting_ids: list[str]) -> None:
        self.is_busy = True
        self.status_message = "선택한 설정을 적용하는 중입니다..."
        try:
            result = self.apply_settings_use_case.execute(setting_ids)
            self.result_rows = [
                (item.name, item.status, item.message)
                for item in result.results
            ]
            self.status_message = (
                f"설정 적용 완료: 성공 {result.success_count}, 실패 {result.failure_count}, 스킵 {result.skipped_count}"
            )
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"설정 적용 실패: {exc}"
        finally:
            self.is_busy = False


def _format_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value)
    return str(value)
