from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.settings.models import ApplyResult


@dataclass(frozen=True)
class RenamePc:
    def execute(self, new_name: str) -> ApplyResult:
        return ApplyResult(
            name="rename_pc",
            success=False,
            message=f"PC rename is not implemented yet: {new_name}",
        )
