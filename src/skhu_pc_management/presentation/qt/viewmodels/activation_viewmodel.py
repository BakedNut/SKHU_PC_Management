from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ActivationViewModel:
    activate_windows_use_case: Any
    activate_office_use_case: Any
    status_message: str = "인증 준비 작업을 실행하지 않았습니다."
    selected_windows_version: str = "windows_11"
    selected_office_version: str = "2024"
    recommended_office_version: str | None = None
    is_busy: bool = False

    def prepare_windows_activation(self, windows_version: str | None = None) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        if windows_version is not None:
            self.selected_windows_version = windows_version
        self.is_busy = True
        self.status_message = "Windows 인증 준비 중입니다..."
        try:
            result = self.activate_windows_use_case.execute(self.selected_windows_version)
            self.status_message = _display_message(result.message) if result.success else f"Windows 인증 준비 실패: {_display_message(result.message)}"
        except Exception as exc:
            self.status_message = f"Windows 인증 준비 실패: {exc}"
        finally:
            self.is_busy = False

    def prepare_office_activation(self, office_version: str | None = None) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        if office_version is not None:
            self.selected_office_version = office_version
        self.is_busy = True
        self.status_message = "Office 인증 준비 중입니다..."
        try:
            result = self.activate_office_use_case.execute(self.selected_office_version)
            self.status_message = _display_message(result.message) if result.success else f"Office 인증 준비 실패: {_display_message(result.message)}"
        except Exception as exc:
            self.status_message = f"Office 인증 준비 실패: {exc}"
        finally:
            self.is_busy = False

    def apply_recommended_office_version(self, version: str | None) -> None:
        if version not in {"2021", "2024"}:
            return
        self.recommended_office_version = version
        self.selected_office_version = version


_MESSAGE_LABELS = {
    "Windows product key copied and activation window launched.": "Windows 제품키를 클립보드에 복사하고 인증 창을 열었습니다.",
    "Office product key copied and Excel launched.": "Office 제품키를 클립보드에 복사하고 Excel을 실행했습니다.",
    "Windows product key is not configured.": "Windows 제품키가 설정되어 있지 않습니다.",
    "Office product key is not configured.": "Office 제품키가 설정되어 있지 않습니다.",
}


def _display_message(message: str) -> str:
    return _MESSAGE_LABELS.get(message, message)
