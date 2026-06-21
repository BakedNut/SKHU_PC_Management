from __future__ import annotations

from pathlib import Path

import pytest

from skhu_pc_management.infrastructure.windows import auto_shutdown_cancel_shortcut as shortcut_module
from skhu_pc_management.infrastructure.windows.auto_shutdown_cancel_shortcut import (
    DESKTOP_MISSING_MESSAGE,
    MISMATCH_MESSAGE,
    SOURCE_MISSING_MESSAGE,
    WindowsAutoShutdownCancelShortcut,
)
from skhu_pc_management.ports.auto_shutdown_cancel_shortcut import AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME


class FakeResourceResolver:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, relative_path: str) -> Path:
        path = self.root / relative_path
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def resources_root(self) -> Path:
        return self.root


def test_auto_shutdown_cancel_shortcut_install_copies_resource_to_desktop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    desktop = tmp_path / "Desktop"
    resources.mkdir()
    source = resources / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME
    source.write_bytes(b"shortcut-bytes")
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: desktop)

    target = WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).install()

    assert target == desktop / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME
    assert target.read_bytes() == b"shortcut-bytes"


def test_auto_shutdown_cancel_shortcut_install_reports_missing_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: tmp_path / "Desktop")

    with pytest.raises(RuntimeError, match=SOURCE_MISSING_MESSAGE):
        WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).install()


def test_auto_shutdown_cancel_shortcut_check_reports_missing_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: tmp_path / "Desktop")

    status = WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).check()

    assert status.source_exists is False
    assert status.matches is False
    assert status.error == SOURCE_MISSING_MESSAGE


def test_auto_shutdown_cancel_shortcut_check_reports_missing_desktop_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    desktop = tmp_path / "Desktop"
    resources.mkdir()
    desktop.mkdir()
    (resources / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME).write_bytes(b"shortcut-bytes")
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: desktop)

    status = WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).check()

    assert status.source_exists is True
    assert status.desktop_exists is False
    assert status.matches is False
    assert status.error == DESKTOP_MISSING_MESSAGE


def test_auto_shutdown_cancel_shortcut_check_reports_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    desktop = tmp_path / "Desktop"
    resources.mkdir()
    desktop.mkdir()
    (resources / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME).write_bytes(b"source")
    (desktop / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME).write_bytes(b"target")
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: desktop)

    status = WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).check()

    assert status.source_exists is True
    assert status.desktop_exists is True
    assert status.matches is False
    assert status.error == MISMATCH_MESSAGE


def test_auto_shutdown_cancel_shortcut_check_reports_same_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    desktop = tmp_path / "Desktop"
    resources.mkdir()
    desktop.mkdir()
    (resources / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME).write_bytes(b"same")
    (desktop / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME).write_bytes(b"same")
    monkeypatch.setattr(shortcut_module, "_current_user_desktop_dir", lambda: desktop)

    status = WindowsAutoShutdownCancelShortcut(FakeResourceResolver(resources)).check()

    assert status.source_exists is True
    assert status.desktop_exists is True
    assert status.matches is True
    assert status.error is None
