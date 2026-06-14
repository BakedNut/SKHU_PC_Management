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
        return import_module("skhu_pc_management.infrastructure.license.local_product_keys")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "제품키 파일이 없습니다. local_product_keys.example.py를 "
            "local_product_keys.py로 복사한 뒤 제품키를 입력하세요."
        ) from exc


def _windows_key_names(edition: str | None) -> tuple[str, ...]:
    if edition:
        normalized = _normalize_key_part(edition)
        if normalized.startswith("WINDOWS_"):
            normalized = normalized.removeprefix("WINDOWS_")
        return (f"WINDOWS_{normalized}_PRODUCT_KEY", f"WIN{normalized.replace('_', '')}_KEY", "WINDOWS_PRODUCT_KEY")
    return ("WINDOWS_PRODUCT_KEY", "WIN11_KEY", "WIN10_KEY")


def _office_key_names(version: str | None) -> tuple[str, ...]:
    if version:
        normalized = _normalize_key_part(version)
        if normalized.startswith("OFFICE_"):
            normalized = normalized.removeprefix("OFFICE_")
        return (f"OFFICE_{normalized}_PRODUCT_KEY", f"OFFICE{normalized.replace('_', '')}_KEY", "OFFICE_PRODUCT_KEY")
    return ("OFFICE_PRODUCT_KEY", "OFFICE2024_KEY", "OFFICE2021_KEY")


def _read_first_key(product_keys: ModuleType, key_names: tuple[str, ...], label: str) -> str:
    for key_name in key_names:
        value = getattr(product_keys, key_name, None)
        if isinstance(value, str) and value.strip():
            return value
    raise RuntimeError(f"{label} 제품키가 local_product_keys.py에 설정되어 있지 않습니다.")


def _normalize_key_part(value: str) -> str:
    return value.replace(" ", "_").replace("-", "_").upper()
