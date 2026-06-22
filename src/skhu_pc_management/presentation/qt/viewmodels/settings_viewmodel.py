from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skhu_pc_management.domain.settings.definitions import DEFAULT_SETTING_DEFINITIONS, SettingDefinition


@dataclass
class SettingsViewModel:
    check_settings_status_use_case: Any
    apply_settings_use_case: Any
    validate_taskbar_resources_use_case: Any | None = None
    apply_taskbar_layout_use_case: Any | None = None
    definitions: tuple[SettingDefinition, ...] = DEFAULT_SETTING_DEFINITIONS
    status_message: str = "설정 상태를 확인하지 않았습니다."
    result_rows: list[tuple[str, str, str, str]] = field(default_factory=list)
    is_busy: bool = False

    @property
    def warning_count(self) -> int:
        return sum(1 for row in self.result_rows if len(row) > 2 and row[2] in {"미설정", "값 없음", "확인 불가", "상태 확인 미구현", "확인 실패"})

    @property
    def summary_text(self) -> str:
        if not self.result_rows:
            return "상태 확인 필요"
        if self.warning_count:
            return f"확인 필요 {self.warning_count}개"
        return "모든 항목 정상"

    def all_setting_ids(self) -> list[str]:
        return [definition.setting_id for definition in self.definitions]

    def check_status(self, setting_ids: list[str]) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "설정 상태 확인 중입니다..."
        try:
            statuses = self.check_settings_status_use_case.execute(setting_ids)
            self.result_rows = [
                (
                    status.label or status.name,
                    "-",
                    _display_status(status.status_text),
                    _status_detail(status),
                )
                for status in statuses
            ]
            self.status_message = "설정 상태 확인이 완료되었습니다."
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"설정 상태 확인 실패: {exc}"
        finally:
            self.is_busy = False

    def apply_selected(self, setting_ids: list[str], display_setting_ids: list[str] | None = None) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        if not setting_ids:
            self.result_rows = []
            self.status_message = "적용할 설정을 선택하세요."
            return

        self.is_busy = True
        self.status_message = "선택한 설정을 적용하는 중입니다..."
        try:
            selected_ids = list(setting_ids)
            display_ids = list(display_setting_ids) if display_setting_ids is not None else self.all_setting_ids()
            result = self.apply_settings_use_case.execute(selected_ids)
            statuses_by_id = {}
            try:
                statuses = self.check_settings_status_use_case.execute(display_ids)
                statuses_by_id = {status.setting_id: status for status in statuses}
            except Exception as exc:
                self.status_message = f"설정 적용 후 상태 재확인 실패: {exc}"

            self.result_rows = []
            apply_results_by_id = {item.setting_id: item for item in result.results}
            definitions_by_id = {definition.setting_id: definition for definition in self.definitions}
            for setting_id in display_ids:
                item = apply_results_by_id.get(setting_id)
                current_status = statuses_by_id.get(setting_id)
                definition = definitions_by_id.get(setting_id)
                name = (
                    (current_status.label or current_status.name)
                    if current_status is not None
                    else item.name
                    if item is not None
                    else definition.name
                    if definition is not None
                    else setting_id
                )
                detail_parts = []
                if item is not None:
                    detail_parts.append(_display_message(item.message))
                if current_status is not None:
                    status_detail = _status_detail(current_status)
                    if status_detail:
                        detail_parts.append(status_detail)
                self.result_rows.append(
                    (
                        name,
                        _display_status(item.status) if item is not None else "-",
                        _display_status(current_status.status_text) if current_status else "확인 불가",
                        " / ".join(part for part in detail_parts if part),
                    )
                )
            self.status_message = (
                f"설정 적용 완료: 성공 {result.success_count}, 실패 {result.failure_count}, 스킵 {result.skipped_count}"
            )
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"설정 적용 실패: {exc}"
        finally:
            self.is_busy = False

    def validate_taskbar_resources(self) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        if self.validate_taskbar_resources_use_case is None:
            self.status_message = "작업표시줄 리소스 확인 기능이 구성되지 않았습니다."
            return

        self.is_busy = True
        self.status_message = "작업표시줄 리소스를 확인하는 중입니다..."
        try:
            result = self.validate_taskbar_resources_use_case.execute()
            self.result_rows = _taskbar_validation_rows(result)
            self.status_message = result.message
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"작업표시줄 리소스 확인 실패: {exc}"
        finally:
            self.is_busy = False

    def apply_taskbar_layout(self, dry_run: bool = True) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        if self.apply_taskbar_layout_use_case is None:
            self.status_message = "작업표시줄 설정 적용 기능이 구성되지 않았습니다."
            return

        self.is_busy = True
        self.status_message = "작업표시줄 설정 적용 계획을 확인하는 중입니다..."
        try:
            result = self.apply_taskbar_layout_use_case.execute(dry_run=dry_run)
            self.result_rows = [(action, "예정", "-", "") for action in result.planned_actions]
            if result.reg_file is not None:
                self.result_rows.append(("TaskBar.reg", "확인", "-", str(result.reg_file)))
            self.status_message = result.message
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"작업표시줄 설정 확인 실패: {exc}"
        finally:
            self.is_busy = False


def _format_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value)
    return str(value)


_STATUS_LABELS = {
    "configured": "설정됨",
    "missing": "값 없음",
    "not_configured": "미설정",
    "unknown": "확인 불가",
    "read_failed": "확인 실패",
    "status_provider_missing": "상태 확인 미구현",
    "applied": "적용됨",
    "failed": "실패",
    "skipped": "건너뜀",
    "Unknown": "알 수 없음",
}

_MESSAGE_LABELS = {
    "Applied.": "적용됨",
}


def _display_status(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


def _display_message(message: str) -> str:
    return _MESSAGE_LABELS.get(message, message)


def _status_detail(status: Any) -> str:
    detail = getattr(status, "detail", "")
    if detail:
        return detail
    value = getattr(status, "actual_value", None)
    return _format_value(value)


def _taskbar_validation_rows(result: Any) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    rows.append(("Resources", "확인" if result.resources_root else "없음", "-", "" if result.resources_root is None else str(result.resources_root)))
    rows.append(("TaskBar.reg", "확인" if result.reg_file and result.reg_file.exists() else "없음", "-", "" if result.reg_file is None else str(result.reg_file)))
    rows.append(("TaskBar 바로가기", f"{len(result.shortcut_files)}개", "-", ", ".join(path.name for path in result.shortcut_files)))
    for warning in result.warnings:
        rows.append(("경고", "주의", "-", warning))
    return rows
