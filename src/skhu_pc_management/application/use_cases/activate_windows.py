from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.ports.clipboard import Clipboard
from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


@dataclass(frozen=True)
class ActivateWindows:
    product_key_provider: ProductKeyProvider
    clipboard: Clipboard
    process_launcher: ProcessLauncher

    def execute(self, edition: str | None = None) -> ActivationResult:
        try:
            product_key = self.product_key_provider.get_windows_product_key(edition)
        except Exception as exc:
            return _failure("windows_activation", f"Windows product key could not be loaded: {exc}", str(exc))

        if not product_key:
            return _failure("windows_activation", "Windows product key is not configured.")

        try:
            self.clipboard.set_text(product_key)
            self.process_launcher.launch(Path("slui.exe"))
        except Exception as exc:
            return ActivationResult(
                success=False,
                action="windows_activation",
                message=f"Windows activation preparation failed: {exc}",
                launched_process="slui.exe",
                copied_to_clipboard=True,
                error=str(exc),
            )

        return ActivationResult(
            success=True,
            action="windows_activation",
            message="Windows product key copied and activation window launched.",
            launched_process="slui.exe",
            copied_to_clipboard=True,
        )


def _failure(action: str, message: str, error: str | None = None) -> ActivationResult:
    return ActivationResult(success=False, action=action, message=message, error=error)


ActivateWindowsUseCase = ActivateWindows
