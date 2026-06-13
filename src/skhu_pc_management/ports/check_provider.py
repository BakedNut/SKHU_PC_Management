from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import CheckResult


class CheckProvider(Protocol):
    def run(self) -> CheckResult:
        """Run one PC check."""
