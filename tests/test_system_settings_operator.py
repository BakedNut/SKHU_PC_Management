from __future__ import annotations

from collections.abc import Sequence

from skhu_pc_management.infrastructure.windows.windows_system_settings_operator import WindowsSystemSettingsOperator


class FakeRegistry:
    def read_value(self, root: str, path: str, name: str) -> object | None:
        return None

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        pass


class FakeCommandRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return ""


def test_disable_password_expiration_applies_computer_policy_and_all_enabled_users() -> None:
    runner = FakeCommandRunner()
    operator = WindowsSystemSettingsOperator(FakeRegistry(), runner)

    operator.disable_password_expiration_for_all_users()

    assert runner.commands[0] == ("net", "accounts", "/maxpwage:unlimited")
    powershell_command = runner.commands[1]
    assert powershell_command[:4] == ("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass")

    script = powershell_command[-1]
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "Get-LocalUser -ErrorAction Stop" in script
    assert "Where-Object { $_.Enabled -eq $true }" in script
    assert "Set-LocalUser -Name $user.Name -PasswordNeverExpires $true -ErrorAction Stop" in script
    assert "FailedUsers" in script
    assert "PasswordNeverExpires -ne $true" in script
    assert "$env:USERNAME" not in script
