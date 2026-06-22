from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from skhu_pc_management.domain.settings.definitions import (
    DEFAULT_SETTING_DEFINITIONS_BY_ID,
    START_EXPLORER_COMMAND,
    STOP_EXPLORER_COMMAND,
    UPDATE_USER_PARAMETERS_COMMAND,
    SettingDefinition,
)
from skhu_pc_management.domain.settings.models import ApplyResult, ApplySettingsResult
from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class ApplySettings:
    registry: Registry
    command_runner: CommandRunner
    safety_guard: SafetyGuard = field(default_factory=SafetyGuard)
    system_settings_actions: Any | None = None
    apply_taskbar_layout_use_case: Any | None = None
    definitions_by_id: dict[str, SettingDefinition] = field(
        default_factory=lambda: dict(DEFAULT_SETTING_DEFINITIONS_BY_ID)
    )

    def execute(self, setting_ids: Iterable[str]) -> ApplySettingsResult:
        setting_ids = list(setting_ids)
        blocked_message = self.safety_guard.blocked_message("apply_settings")
        if blocked_message is not None:
            return ApplySettingsResult(
                results=[
                    ApplyResult(
                        setting_id=setting_id,
                        name=self.definitions_by_id.get(setting_id, setting_id).name
                        if setting_id in self.definitions_by_id
                        else setting_id,
                        success=False,
                        status="skipped",
                        message=blocked_message,
                    )
                    for setting_id in setting_ids
                ]
            )

        results: list[ApplyResult] = []
        should_update_user_parameters = False
        should_restart_explorer = False

        for setting_id in setting_ids:
            definition = self.definitions_by_id.get(setting_id)
            if definition is None:
                results.append(
                    ApplyResult(
                        setting_id=setting_id,
                        name=setting_id,
                        success=False,
                        status="failed",
                        message=f"Unknown setting id: {setting_id}",
                    )
                )
                continue

            result = self._apply_definition(definition)
            results.append(result)

            if definition.setting_id == "set_taskbar_icons":
                continue

            if result.success and definition.requires_user_parameter_update:
                should_update_user_parameters = True
            if result.success and definition.requires_explorer_restart:
                should_restart_explorer = True

        if any(result.success for result in results):
            self._run_post_commands(results, should_update_user_parameters, should_restart_explorer)

        return ApplySettingsResult(results=results)

    def _apply_definition(self, definition: SettingDefinition) -> ApplyResult:
        if definition.setting_id in {"set_default_wallpaper", "delete_edge_shortcut"}:
            if self.system_settings_actions is None:
                return ApplyResult(
                    setting_id=definition.setting_id,
                    name=definition.name,
                    success=False,
                    status="failed",
                    message="시스템 설정 작업 기능이 구성되지 않았습니다.",
                )
            return self.system_settings_actions.execute(definition.setting_id, definition.name)

        if definition.setting_id == "disable_password_expiration":
            if self.system_settings_actions is None:
                return ApplyResult(
                    setting_id=definition.setting_id,
                    name=definition.name,
                    success=False,
                    status="failed",
                    message="사용자 계정 암호 만료 비활성화 기능이 구성되지 않았습니다.",
                )
            return self.system_settings_actions.execute(definition.setting_id, definition.name)

        if definition.setting_id == "set_taskbar_icons":
            if self.apply_taskbar_layout_use_case is None:
                return ApplyResult(
                    setting_id=definition.setting_id,
                    name=definition.name,
                    success=False,
                    status="failed",
                    message="작업표시줄 설정 적용 기능이 구성되지 않았습니다.",
                )
            result = self.apply_taskbar_layout_use_case.execute(dry_run=False)
            return ApplyResult(
                setting_id=definition.setting_id,
                name=definition.name,
                success=result.success,
                status="applied" if result.success else "failed",
                message=result.message,
            )

        try:
            for registry_value in definition.registry_values:
                self.registry.write_value(
                    registry_value.root,
                    registry_value.path,
                    registry_value.value_name,
                    registry_value.expected_value,
                    registry_value.value_type,
                )

            for command in definition.post_commands:
                self.command_runner.run(command)
        except Exception as exc:
            return ApplyResult(
                setting_id=definition.setting_id,
                name=definition.name,
                success=False,
                status="failed",
                message=str(exc),
            )

        return ApplyResult(
            setting_id=definition.setting_id,
            name=definition.name,
            success=True,
            status="applied",
            message="Applied.",
        )

    def _run_post_commands(
        self,
        results: list[ApplyResult],
        should_update_user_parameters: bool,
        should_restart_explorer: bool,
    ) -> None:
        post_command_failures: list[str] = []

        if should_update_user_parameters:
            self._run_post_command(UPDATE_USER_PARAMETERS_COMMAND, post_command_failures)

        if should_restart_explorer:
            self._run_post_command(STOP_EXPLORER_COMMAND, post_command_failures)
            self._run_post_command(START_EXPLORER_COMMAND, post_command_failures)

        # Post commands only refresh Shell/UI state. Registry and file status
        # providers determine whether settings are actually configured, so
        # best-effort post command failures are intentionally not surfaced in
        # per-setting results.
        return

    def _run_post_command(self, command: tuple[str, ...], failures: list[str]) -> None:
        try:
            self.command_runner.run(command)
        except Exception as exc:
            failures.append(f"{command[0]}: {exc}")
