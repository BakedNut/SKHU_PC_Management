from __future__ import annotations


class NullProductKeyProvider:
    def get_windows_product_key(self) -> str | None:
        return None
