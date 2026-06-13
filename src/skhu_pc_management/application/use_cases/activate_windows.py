from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


@dataclass(frozen=True)
class ActivateWindows:
    product_key_provider: ProductKeyProvider

    def execute(self) -> ApplyResult:
        product_key = self.product_key_provider.get_windows_product_key()
        if not product_key:
            return ApplyResult(
                name="activate_windows",
                success=False,
                message="Windows product key is not configured.",
            )
        return ApplyResult(
            name="activate_windows",
            success=False,
            message="Windows activation is not implemented yet.",
        )
