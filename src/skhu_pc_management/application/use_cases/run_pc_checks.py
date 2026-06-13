from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.checks.models import CheckResult


@dataclass(frozen=True)
class RunPcChecks:
    def execute(self) -> list[CheckResult]:
        return [
            CheckResult(
                name="placeholder",
                passed=False,
                message="PC checks are not implemented yet.",
            )
        ]
