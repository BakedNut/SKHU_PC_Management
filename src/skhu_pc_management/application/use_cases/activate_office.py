from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.ports.clipboard import Clipboard
from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


DEFAULT_EXCEL_PATH = Path("excel.exe")


@dataclass(frozen=True)
class ActivateOffice:
    product_key_provider: ProductKeyProvider
    clipboard: Clipboard
    process_launcher: ProcessLauncher
    excel_path: Path = DEFAULT_EXCEL_PATH
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, version: str | None = None) -> ActivationResult:
        display_version = _display_office_version(version)
        blocked_message = self.safety_guard.blocked_message("office_activation")
        if blocked_message is not None:
            return _failure("office_activation", blocked_message)

        try:
            product_key = self.product_key_provider.get_office_product_key(version)
        except Exception as exc:
            return _failure("office_activation", f"Office 제품키를 불러올 수 없습니다: {exc}", str(exc))

        if not product_key:
            return _failure("office_activation", "Office 제품키가 설정되어 있지 않습니다.")

        try:
            self.clipboard.set_text(product_key)
            self.process_launcher.launch(self.excel_path)
        except FileNotFoundError as exc:
            return ActivationResult(
                success=False,
                action="office_activation",
                message="Excel 실행 파일을 찾지 못했습니다.",
                launched_process=str(self.excel_path),
                copied_to_clipboard=True,
                error=str(exc),
            )
        except Exception as exc:
            return ActivationResult(
                success=False,
                action="office_activation",
                message=f"Office 인증 준비 실패: {exc}",
                launched_process=str(self.excel_path),
                copied_to_clipboard=True,
                error=str(exc),
            )

        return ActivationResult(
            success=True,
            action="office_activation",
            message=f"{display_version} 제품키를 클립보드에 복사하고 Excel을 실행했습니다.",
            launched_process=str(self.excel_path),
            copied_to_clipboard=True,
        )


def _failure(action: str, message: str, error: str | None = None) -> ActivationResult:
    return ActivationResult(success=False, action=action, message=message, error=error)


def _display_office_version(version: str | None) -> str:
    normalized = (version or "").replace("_", " ").replace("-", " ").strip().lower()
    if "2021" in normalized:
        return "Office 2021"
    return "Office 2024"


ActivateOfficeUseCase = ActivateOffice
