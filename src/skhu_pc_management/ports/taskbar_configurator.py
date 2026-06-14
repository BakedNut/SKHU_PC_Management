from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.resources.models import ResourceValidationResult, TaskbarApplyResult


class TaskbarConfigurator(Protocol):
    def validate_resources(self) -> ResourceValidationResult:
        """Validate taskbar layout resources without changing the system."""

    def apply_taskbar_layout(self, dry_run: bool = True) -> TaskbarApplyResult:
        """Apply or plan taskbar layout changes."""
