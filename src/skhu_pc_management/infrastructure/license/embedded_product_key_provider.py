from __future__ import annotations

from importlib import import_module
from types import ModuleType


class EmbeddedProductKeyProvider:
    def get_windows_product_key(self, edition: str | None = None) -> str:
        product_keys = _load_product_keys()
        key_names = _windows_key_names(edition)
        return _read_first_key(product_keys, key_names, "Windows")

    def get_office_product_key(self, version: str | None = None) -> str:
        product_keys = _load_product_keys()
        key_names = _office_key_names(version)
        return _read_first_key(product_keys, key_names, "Office")


def _load_product_keys() -> ModuleType:
    try:
        return import_module("secrets.product_keys")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing secrets/product_keys.py. Copy secrets/product_keys.example.py "
            "to secrets/product_keys.py locally and provide product key constants."
        ) from exc


def _windows_key_names(edition: str | None) -> tuple[str, ...]:
    if edition:
        normalized = edition.replace(" ", "_").replace("-", "_").upper()
        return (f"WINDOWS_{normalized}_PRODUCT_KEY", f"{normalized}_KEY", "WINDOWS_PRODUCT_KEY")
    return ("WINDOWS_PRODUCT_KEY", "WIN11_KEY", "WIN10_KEY")


def _office_key_names(version: str | None) -> tuple[str, ...]:
    if version:
        normalized = version.replace(" ", "_").replace("-", "_").upper()
        return (f"OFFICE_{normalized}_PRODUCT_KEY", f"OFFICE{normalized}_KEY", "OFFICE_PRODUCT_KEY")
    return ("OFFICE_PRODUCT_KEY", "OFFICE2024_KEY", "OFFICE2021_KEY")


def _read_first_key(product_keys: ModuleType, key_names: tuple[str, ...], label: str) -> str:
    for key_name in key_names:
        value = getattr(product_keys, key_name, None)
        if isinstance(value, str) and value.strip():
            return value
    raise RuntimeError(f"{label} product key is not configured in secrets/product_keys.py.")
