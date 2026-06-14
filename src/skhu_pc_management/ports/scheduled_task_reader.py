from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import ScheduledTaskInfo


class ScheduledTaskReader(Protocol):
    def get_task(self, name: str) -> ScheduledTaskInfo:
        """Read a Windows scheduled task without modifying it."""
