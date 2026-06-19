from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.resources.models import TaskbarApplyResult
from skhu_pc_management.ports.taskbar_configurator import TaskbarConfigurator


@dataclass(frozen=True)
class ApplyTaskbarLayout:
    taskbar_configurator: TaskbarConfigurator
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, dry_run: bool = True) -> TaskbarApplyResult:
        blocked_message = self.safety_guard.blocked_taskbar_apply_message(dry_run)
        if blocked_message is not None:
            return TaskbarApplyResult(success=False, message=blocked_message, dry_run=dry_run)
        return self.taskbar_configurator.apply_taskbar_layout(dry_run=dry_run)


ApplyTaskbarLayoutUseCase = ApplyTaskbarLayout
