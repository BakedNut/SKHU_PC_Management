from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from skhu_pc_management.domain.settings.definitions import HKCU, HKLM
from skhu_pc_management.infrastructure.windows.windows_setting_status_providers import (
    DefaultWallpaperStatusProvider,
    EdgeShortcutStatusProvider,
    PasswordExpirationStatusProvider,
    TaskbarLayoutStatusProvider,
)


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], object] = {}

    def read_value(self, root: str, path: str, name: str) -> object | None:
        return self.values.get((root, path, name))

    def list_subkeys(self, root: str, path: str) -> list[str]:
        return []

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        raise AssertionError("status provider tests must not write registry")


class FakeResourceResolver:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, relative_path: str) -> Path:
        return self.root / relative_path

    def resources_root(self) -> Path:
        return self.root


class FakeCommandRunner:
    def __init__(self, output: str) -> None:
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return self.output


def test_default_wallpaper_status_provider_reports_configured(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WINDIR", str(tmp_path / "Windows"))
    expected = tmp_path / "Windows" / "Web" / "Wallpaper" / "Windows" / "img0.jpg"
    registry = FakeRegistry()
    registry.values[(HKCU, r"Control Panel\Desktop", "Wallpaper")] = str(expected)

    status = DefaultWallpaperStatusProvider(registry).check("set_default_wallpaper")

    assert status.is_configured is True
    assert status.status_text == "configured"


def test_edge_shortcut_status_provider_reports_warning_when_shortcut_remains(monkeypatch, tmp_path) -> None:
    public = tmp_path / "Public"
    shortcut = public / "Desktop" / "Microsoft Edge.lnk"
    shortcut.parent.mkdir(parents=True)
    shortcut.write_text("shortcut", encoding="utf-8")
    monkeypatch.setenv("PUBLIC", str(public))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "User"))
    registry = FakeRegistry()
    registry.values[(HKLM, r"SOFTWARE\Policies\Microsoft\EdgeUpdate", "CreateDesktopShortcutDefault")] = 0

    status = EdgeShortcutStatusProvider(registry).check("delete_edge_shortcut")

    assert status.is_configured is False
    assert status.status_text == "not_configured"
    assert "Microsoft Edge.lnk" in status.detail


def test_taskbar_layout_status_provider_compares_source_and_target(monkeypatch, tmp_path) -> None:
    resources = tmp_path / "resources"
    source = resources / "TaskBar"
    source.mkdir(parents=True)
    (source / "Chrome.lnk").write_text("shortcut", encoding="utf-8")
    appdata = tmp_path / "AppData"
    target = appdata / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
    target.mkdir(parents=True)
    (target / "Chrome.lnk").write_text("shortcut", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(appdata))

    status = TaskbarLayoutStatusProvider(FakeResourceResolver(resources)).check("set_taskbar_icons")

    assert status.is_configured is True
    assert "실제 pin 상태" in status.detail


def test_password_expiration_status_provider_reports_expiring_user() -> None:
    output = """
[
  {"Name": "student", "Enabled": true, "PasswordNeverExpires": false},
  {"Name": "disabled", "Enabled": false, "PasswordNeverExpires": false}
]
"""
    runner = FakeCommandRunner(output)

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.is_configured is False
    assert status.status_text == "not_configured"
    assert "student" in status.detail
    assert runner.commands
