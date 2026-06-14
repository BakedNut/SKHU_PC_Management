from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard, TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.domain.resources.models import TaskbarApplyResult
from skhu_pc_management.ports.taskbar_configurator import TaskbarConfigurator


@dataclass(frozen=True)
class ApplyTaskbarLayout:
    taskbar_configurator: TaskbarConfigurator
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, dry_run: bool = True) -> TaskbarApplyResult:
        blocked_message = self.safety_guard.blocked_message("apply_taskbar_layout")
        if blocked_message is not None and not dry_run:
            return TaskbarApplyResult(success=False, message=TEST_MODE_DISABLED_MESSAGE, dry_run=dry_run)
        return self.taskbar_configurator.apply_taskbar_layout(dry_run=dry_run)


ApplyTaskbarLayoutUseCase = ApplyTaskbarLayout
