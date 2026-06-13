from __future__ import annotations

from typing import Protocol


class ProductKeyProvider(Protocol):
    def get_windows_product_key(self, edition: str | None = None) -> str | None:
        """Return the Windows product key, if configured."""

    def get_office_product_key(self, version: str | None = None) -> str | None:
        """Return the Office product key, if configured."""
