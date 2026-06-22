from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from skhu_pc_management.domain.settings.definitions import HKCU, HKLM
from skhu_pc_management.infrastructure.windows.windows_setting_status_providers import (
    DefaultWallpaperStatusProvider,
    EdgeShortcutStatusProvider,
    PasswordExpirationStatusProvider,
    TaskbarLayoutStatusProvider,
    _is_max_password_age_unlimited,
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
    def __init__(self, output: str | list[str]) -> None:
        self.outputs = [output] if isinstance(output, str) else list(output)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        if not self.outputs:
            raise AssertionError("unexpected command")
        return self.outputs.pop(0)


class FailingCommandRunner:
    def run(self, command: Sequence[str]) -> str:
        raise RuntimeError("command failed")


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


def test_password_expiration_status_provider_reports_general_remaining_user_as_detail_only() -> None:
    user_output = """
[
  {"Name": "AS", "Enabled": true, "PasswordNeverExpires": false},
  {"Name": "Teacher", "Enabled": true, "PasswordNeverExpires": true},
  {"Name": "disabled", "Enabled": false, "PasswordNeverExpires": false}
]
"""
    runner = FakeCommandRunner([user_output, "Maximum password age (days): Unlimited"])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.is_configured is True
    assert status.is_applied is True
    assert status.severity == "ok"
    assert status.status_text == "configured"
    assert "개별 플래그 미반영 사용자: AS" in status.detail
    assert runner.commands[1] == ("net", "accounts")


def test_password_expiration_status_provider_excludes_builtin_guest_from_failure() -> None:
    user_output = """
[
  {"Name": "Teacher", "Enabled": true, "PasswordNeverExpires": true},
  {"Name": "Guest", "Enabled": true, "PasswordNeverExpires": false}
]
"""
    runner = FakeCommandRunner([user_output, "Maximum password age (days): Unlimited"])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.is_configured is True
    assert status.is_applied is True
    assert status.severity == "ok"
    assert "최대 암호 사용 기간: 무제한" in status.detail
    assert "개별 플래그 미반영 사용자: 없음" in status.detail
    assert "제외된 내장 계정: Guest" in status.detail


def test_password_expiration_status_provider_reports_configured_when_policy_and_users_match() -> None:
    user_output = """
[
  {"Name": "student", "Enabled": "True", "PasswordNeverExpires": "True"}
]
"""
    runner = FakeCommandRunner([user_output, "최대 암호 사용 기간(일): 무제한"])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.is_configured is True
    assert status.status_text == "configured"
    assert "최대 암호 사용 기간: 무제한" in status.detail
    assert "개별 플래그 미반영 사용자: 없음" in status.detail


def test_password_expiration_status_provider_warns_when_max_password_age_is_numeric() -> None:
    user_output = """
[
  {"Name": "student", "Enabled": true, "PasswordNeverExpires": true}
]
"""
    runner = FakeCommandRunner([user_output, "Maximum password age (days): 90"])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.is_configured is False
    assert status.severity == "warning"
    assert "최대 암호 사용 기간: 90일" in status.detail


def test_password_expiration_status_provider_reports_unknown_when_max_age_cannot_be_parsed() -> None:
    user_output = """
[
  {"Name": "student", "Enabled": true, "PasswordNeverExpires": true}
]
"""
    runner = FakeCommandRunner([user_output, "The command completed successfully."])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.severity == "unknown"
    assert "최대 암호 사용 기간" in status.detail


def test_password_expiration_status_provider_reports_unknown_when_enabled_users_are_empty() -> None:
    runner = FakeCommandRunner(["[]", "Maximum password age (days): Unlimited"])

    status = PasswordExpirationStatusProvider(runner).check("disable_password_expiration")

    assert status.severity == "unknown"
    assert "활성화된 로컬 사용자" in status.detail


def test_password_expiration_status_provider_reports_unknown_when_command_fails() -> None:
    status = PasswordExpirationStatusProvider(FailingCommandRunner()).check("disable_password_expiration")

    assert status.severity == "unknown"
    assert "사용자 계정 암호 만료 상태를 확인할 수 없습니다" in status.detail


def test_max_password_age_parser_handles_english_and_korean_outputs() -> None:
    assert _is_max_password_age_unlimited("Maximum password age (days): Unlimited") is True
    assert _is_max_password_age_unlimited("Maximum password age (days): 90") is False
    assert _is_max_password_age_unlimited("최대 암호 사용 기간(일): 제한 없음") is True
    assert _is_max_password_age_unlimited("최대 암호 사용 기간(일): 무제한") is True
    assert _is_max_password_age_unlimited("최대 암호 사용 기간(일): 90") is False
    assert _is_max_password_age_unlimited("The command completed successfully.") is None
