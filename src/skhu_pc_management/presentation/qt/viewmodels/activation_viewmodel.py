from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ActivationViewModel:
    activate_windows_use_case: Any
    activate_office_use_case: Any
    status_message: str = "인증 준비 작업을 실행하지 않았습니다."
    is_busy: bool = False

    def prepare_windows_activation(self) -> None:
        self.is_busy = True
        self.status_message = "Windows 인증 준비 중입니다..."
        try:
            result = self.activate_windows_use_case.execute()
            self.status_message = result.message if result.success else f"Windows 인증 준비 실패: {result.message}"
        except Exception as exc:
            self.status_message = f"Windows 인증 준비 실패: {exc}"
        finally:
            self.is_busy = False

    def prepare_office_activation(self) -> None:
        self.is_busy = True
        self.status_message = "Office 인증 준비 중입니다..."
        try:
            result = self.activate_office_use_case.execute()
            self.status_message = result.message if result.success else f"Office 인증 준비 실패: {result.message}"
        except Exception as exc:
            self.status_message = f"Office 인증 준비 실패: {exc}"
        finally:
            self.is_busy = False
