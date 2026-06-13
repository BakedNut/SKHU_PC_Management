from __future__ import annotations


class NullProductKeyProvider:
    def get_windows_product_key(self, edition: str | None = None) -> str | None:
        return None

    def get_office_product_key(self, version: str | None = None) -> str | None:
        return None
