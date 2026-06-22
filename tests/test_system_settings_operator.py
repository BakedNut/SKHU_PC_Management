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


def test_disable_password_expiration_applies_policy_and_best_effort_user_flags() -> None:
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
    assert "Guest" in script
    assert "DefaultAccount" in script
    assert "WDAGUtilityAccount" in script
    assert "SetFailures" in script
    assert "RemainingUsers" in script
    assert "ConvertTo-Json" in script
    assert "PasswordNeverExpires -ne $true" in script
    assert "암호 만료 비활성화 적용 실패 사용자" not in script
    assert "$failedUsers.Count -gt 0" not in script
    assert "$env:USERNAME" not in script
