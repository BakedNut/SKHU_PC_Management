from __future__ import annotations

from typing import Protocol


class ProductKeyProvider(Protocol):
    def get_windows_product_key(self) -> str | None:
        """Return the Windows product key, if configured."""
