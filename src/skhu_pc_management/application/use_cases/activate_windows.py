from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.ports.clipboard import Clipboard
from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


CLIPBOARD_AFTER_FAILURE_NOTICE = "제품키는 이미 클립보드에 복사되었을 수 있습니다. 사용 후 다른 값을 복사해 클립보드를 덮어쓰세요."


@dataclass(frozen=True)
class ActivateWindows:
    product_key_provider: ProductKeyProvider
    clipboard: Clipboard
    process_launcher: ProcessLauncher
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, edition: str | None = None) -> ActivationResult:
        display_edition = _display_windows_edition(edition)
        blocked_message = self.safety_guard.blocked_message("windows_activation")
        if blocked_message is not None:
            return _failure("windows_activation", blocked_message)

        try:
            product_key = self.product_key_provider.get_windows_product_key(edition)
        except Exception as exc:
            return _failure("windows_activation", f"Windows 제품키를 불러올 수 없습니다: {exc}", str(exc))

        if not product_key:
            return _failure("windows_activation", "Windows 제품키가 설정되어 있지 않습니다.")

        try:
            self.clipboard.set_text(product_key)
        except Exception as exc:
            return ActivationResult(
                success=False,
                action="windows_activation",
                message=f"Windows 인증 준비 실패: {exc}",
                launched_process="slui.exe",
                copied_to_clipboard=False,
                error=str(exc),
            )

        try:
            self.process_launcher.launch(Path("slui.exe"))
        except Exception as exc:
            return ActivationResult(
                success=False,
                action="windows_activation",
                message=f"Windows 인증 준비 실패: {exc} {CLIPBOARD_AFTER_FAILURE_NOTICE}",
                launched_process="slui.exe",
                copied_to_clipboard=True,
                error=str(exc),
            )

        return ActivationResult(
            success=True,
            action="windows_activation",
            message=f"{display_edition} 제품키를 클립보드에 복사하고 인증 창을 실행했습니다.",
            launched_process="slui.exe",
            copied_to_clipboard=True,
        )


def _failure(action: str, message: str, error: str | None = None) -> ActivationResult:
    return ActivationResult(success=False, action=action, message=message, error=error)


def _display_windows_edition(edition: str | None) -> str:
    normalized = (edition or "").replace("_", " ").replace("-", " ").strip().lower()
    if "10" in normalized:
        return "Windows 10"
    return "Windows 11"


ActivateWindowsUseCase = ActivateWindows
