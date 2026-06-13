from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.ports.clipboard import Clipboard
from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


DEFAULT_EXCEL_PATH = Path(r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE")


@dataclass(frozen=True)
class ActivateOffice:
    product_key_provider: ProductKeyProvider
    clipboard: Clipboard
    process_launcher: ProcessLauncher
    excel_path: Path = DEFAULT_EXCEL_PATH

    def execute(self, version: str | None = None) -> ActivationResult:
        try:
            product_key = self.product_key_provider.get_office_product_key(version)
        except Exception as exc:
            return _failure("office_activation", f"Office product key could not be loaded: {exc}", str(exc))

        if not product_key:
            return _failure("office_activation", "Office product key is not configured.")

        try:
            self.clipboard.set_text(product_key)
            self.process_launcher.launch(self.excel_path)
        except Exception as exc:
            return ActivationResult(
                success=False,
                action="office_activation",
                message=f"Office activation preparation failed: {exc}",
                launched_process=str(self.excel_path),
                copied_to_clipboard=True,
                error=str(exc),
            )

        return ActivationResult(
            success=True,
            action="office_activation",
            message="Office product key copied and Excel launched.",
            launched_process=str(self.excel_path),
            copied_to_clipboard=True,
        )


def _failure(action: str, message: str, error: str | None = None) -> ActivationResult:
    return ActivationResult(success=False, action=action, message=message, error=error)


ActivateOfficeUseCase = ActivateOffice
