from __future__ import annotations

import sys
from pathlib import Path

import pytest

from skhu_pc_management.infrastructure.windows.pyinstaller_resource_resolver import PyInstallerResourceResolver


def test_resolver_finds_development_resources_from_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    expected = resources / "TaskBar.reg"
    expected.write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    resolver = PyInstallerResourceResolver()

    assert resolver.resources_root() == resources
    assert resolver.resolve("TaskBar.reg") == expected


def test_resolver_finds_pyinstaller_meipass_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    meipass = tmp_path / "_MEI"
    resources = meipass / "resources"
    resources.mkdir(parents=True)
    expected = resources / "TaskBar.reg"
    expected.write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    resolver = PyInstallerResourceResolver()

    assert resolver.resources_root() == resources
    assert resolver.resolve("TaskBar.reg") == expected


def test_resolver_raises_clear_error_for_missing_resource(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    resolver = PyInstallerResourceResolver()

    with pytest.raises(FileNotFoundError, match="Resource not found"):
        resolver.resolve("missing.txt")
