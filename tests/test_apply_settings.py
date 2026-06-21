from __future__ import annotations

from collections.abc import Sequence

from skhu_pc_management.application.use_cases.apply_settings import ApplySettings
from skhu_pc_management.domain.settings.definitions import (
    DEFAULT_SETTING_DEFINITIONS,
    DEFAULT_SETTING_DEFINITIONS_BY_ID,
    HKCU,
    HKLM,
    REG_DWORD,
    START_EXPLORER_COMMAND,
    STOP_EXPLORER_COMMAND,
    UPDATE_USER_PARAMETERS_COMMAND,
)


class FakeRegistry:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, str, object, str]] = []

    def read_value(self, root: str, path: str, name: str) -> object | None:
        return None

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        self.writes.append((root, path, name, value, value_type))


class FakeCommandRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return ""


class FakeTaskbarLayoutUseCase:
    def __init__(self) -> None:
        self.dry_run_requests: list[bool] = []

    def execute(self, dry_run: bool = True):
        from skhu_pc_management.domain.resources.models import TaskbarApplyResult

        self.dry_run_requests.append(dry_run)
        return TaskbarApplyResult(
            success=True,
            message="작업표시줄 설정 dry-run이 완료되었습니다. 실제 변경은 수행하지 않았습니다.",
            dry_run=dry_run,
        )


class FakeSystemSettingsActions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def execute(self, setting_id: str, name: str):
        from skhu_pc_management.domain.settings.models import ApplyResult

        self.calls.append((setting_id, name))
        return ApplyResult(setting_id=setting_id, name=name, success=True, status="applied", message="special action")


def test_default_setting_definitions_are_loaded() -> None:
    setting_ids = {definition.setting_id for definition in DEFAULT_SETTING_DEFINITIONS}

    assert "hide_frequent_folders" in setting_ids
    assert "enable_passwordless_signin" in setting_ids
    assert "win11_hide_recommended_files" in setting_ids


def test_disable_password_expiration_label_and_id_are_kept() -> None:
    definition = DEFAULT_SETTING_DEFINITIONS_BY_ID["disable_password_expiration"]

    assert definition.setting_id == "disable_password_expiration"
    assert definition.name == "사용자 계정 암호 만료 비활성화"
    assert definition.post_commands == ()


def test_applies_only_selected_setting_ids() -> None:
    registry = FakeRegistry()
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(registry, command_runner)

    result = use_case.execute(["hide_frequent_folders"])

    assert result.success_count == 1
    assert len(registry.writes) == 1
    assert registry.writes[0] == (
        HKCU,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer",
        "ShowFrequent",
        0,
        REG_DWORD,
    )


def test_hklm_setting_is_written_through_registry_port() -> None:
    registry = FakeRegistry()
    use_case = ApplySettings(registry, FakeCommandRunner())

    result = use_case.execute(["enable_passwordless_signin"])

    assert result.is_success is True
    assert registry.writes == [
        (
            HKLM,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device",
            "DevicePasswordLessBuildVersion",
            0,
            REG_DWORD,
        )
    ]


def test_user_parameter_update_runs_through_command_runner() -> None:
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(FakeRegistry(), command_runner)

    use_case.execute(["show_file_extensions"])

    assert UPDATE_USER_PARAMETERS_COMMAND in command_runner.commands


def test_explorer_restart_runs_through_command_runner_when_required() -> None:
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(FakeRegistry(), command_runner)

    use_case.execute(["hide_task_view_button"])

    assert STOP_EXPLORER_COMMAND in command_runner.commands
    assert START_EXPLORER_COMMAND in command_runner.commands


def test_disable_password_expiration_without_system_settings_actions_fails_without_fallback_command() -> None:
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(FakeRegistry(), command_runner)

    result = use_case.execute(["disable_password_expiration"])

    assert result.is_success is False
    assert result.results[0].status == "failed"
    assert "구성되지 않았습니다" in result.results[0].message
    assert command_runner.commands == []


def test_disable_password_expiration_uses_system_settings_actions_when_configured() -> None:
    command_runner = FakeCommandRunner()
    system_settings_actions = FakeSystemSettingsActions()
    use_case = ApplySettings(
        FakeRegistry(),
        command_runner,
        system_settings_actions=system_settings_actions,
    )

    result = use_case.execute(["disable_password_expiration"])

    assert result.is_success is True
    assert system_settings_actions.calls == [("disable_password_expiration", "사용자 계정 암호 만료 비활성화")]
    assert command_runner.commands == []


def test_unknown_setting_id_returns_failure_result() -> None:
    registry = FakeRegistry()
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(registry, command_runner)

    result = use_case.execute(["unknown_setting"])

    assert result.is_success is False
    assert result.results[0].status == "failed"
    assert "Unknown setting id" in result.results[0].message
    assert registry.writes == []
    assert command_runner.commands == []


def test_taskbar_setting_uses_dry_run_only() -> None:
    taskbar_use_case = FakeTaskbarLayoutUseCase()
    registry = FakeRegistry()
    command_runner = FakeCommandRunner()
    use_case = ApplySettings(
        registry,
        command_runner,
        apply_taskbar_layout_use_case=taskbar_use_case,
    )

    result = use_case.execute(["set_taskbar_icons"])

    assert result.is_success is True
    assert taskbar_use_case.dry_run_requests == [True]
    assert "dry-run" in result.results[0].message
    assert "실제 변경" in result.results[0].message
    assert registry.writes == []
    assert command_runner.commands == []
