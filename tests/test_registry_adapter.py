from __future__ import annotations

import pytest

from skhu_pc_management.infrastructure.windows import winreg_registry
from skhu_pc_management.infrastructure.windows.winreg_registry import WinregRegistry


class FakeKey:
    def __enter__(self) -> object:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def test_winreg_registry_returns_none_when_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_open_key(root: int, path: str) -> FakeKey:
        raise FileNotFoundError(path)

    monkeypatch.setattr(winreg_registry.winreg, "OpenKey", missing_open_key)

    assert WinregRegistry().read_value("HKCU", "missing", "Value") is None


def test_winreg_registry_returns_none_when_value_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(winreg_registry.winreg, "OpenKey", lambda root, path: FakeKey())

    def missing_query_value(key: object, name: str) -> tuple[object, int]:
        raise OSError(name)

    monkeypatch.setattr(winreg_registry.winreg, "QueryValueEx", missing_query_value)

    assert WinregRegistry().read_value("HKCU", "path", "missing") is None


def test_winreg_registry_keeps_permission_errors_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied_open_key(root: int, path: str) -> FakeKey:
        raise PermissionError(path)

    monkeypatch.setattr(winreg_registry.winreg, "OpenKey", denied_open_key)

    with pytest.raises(PermissionError):
        WinregRegistry().read_value("HKLM", "protected", "Value")
