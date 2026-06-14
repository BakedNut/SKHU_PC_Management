from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.resources.models import ResourceValidationResult
from skhu_pc_management.ports.taskbar_configurator import TaskbarConfigurator


@dataclass(frozen=True)
class ValidateTaskbarResources:
    taskbar_configurator: TaskbarConfigurator

    def execute(self) -> ResourceValidationResult:
        return self.taskbar_configurator.validate_resources()


ValidateTaskbarResourcesUseCase = ValidateTaskbarResources
