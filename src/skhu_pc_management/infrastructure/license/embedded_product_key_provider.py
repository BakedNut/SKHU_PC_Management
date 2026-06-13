from __future__ import annotations

from importlib import import_module


class EmbeddedProductKeyProvider:
    def get_windows_product_key(self) -> str:
        try:
            product_keys = import_module("secrets.product_keys")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing secrets/product_keys.py. Copy secrets/product_keys.example.py "
                "to secrets/product_keys.py locally and provide WINDOWS_PRODUCT_KEY."
            ) from exc

        product_key = getattr(product_keys, "WINDOWS_PRODUCT_KEY", None)
        if not product_key:
            raise RuntimeError("secrets/product_keys.py must define WINDOWS_PRODUCT_KEY.")
        return product_key
