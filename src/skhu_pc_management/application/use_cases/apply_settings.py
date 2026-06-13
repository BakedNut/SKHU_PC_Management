from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from skhu_pc_management.domain.settings.definitions import (
    DEFAULT_SETTING_DEFINITIONS_BY_ID,
    START_EXPLORER_COMMAND,
    STOP_EXPLORER_COMMAND,
    UPDATE_USER_PARAMETERS_COMMAND,
    SettingDefinition,
)
from skhu_pc_management.domain.settings.models import ApplyResult, ApplySettingsResult
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class ApplySettings:
    registry: Registry
    command_runner: CommandRunner
    definitions_by_id: dict[str, SettingDefinition] = field(
        default_factory=lambda: dict(DEFAULT_SETTING_DEFINITIONS_BY_ID)
    )

    def execute(self, setting_ids: Iterable[str]) -> ApplySettingsResult:
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

            if result.success and definition.requires_user_parameter_update:
                should_update_user_parameters = True
            if result.success and definition.requires_explorer_restart:
                should_restart_explorer = True

        if any(result.success for result in results):
            self._run_post_commands(results, should_update_user_parameters, should_restart_explorer)

        return ApplySettingsResult(results=results)

    def _apply_definition(self, definition: SettingDefinition) -> ApplyResult:
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

        if not post_command_failures:
            return

        message = "Post command failed: " + "; ".join(post_command_failures)
        for index, result in enumerate(results):
            if result.success:
                results[index] = ApplyResult(
                    setting_id=result.setting_id,
                    name=result.name,
                    success=False,
                    status="failed",
                    message=message,
                )

    def _run_post_command(self, command: tuple[str, ...], failures: list[str]) -> None:
        try:
            self.command_runner.run(command)
        except Exception as exc:
            failures.append(f"{command[0]}: {exc}")
