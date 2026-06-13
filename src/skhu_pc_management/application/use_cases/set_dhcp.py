from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.settings.models import ApplyResult


@dataclass(frozen=True)
class SetDhcp:
    def execute(self, adapter_name: str) -> ApplyResult:
        return ApplyResult(
            name="set_dhcp",
            success=False,
            message=f"DHCP configuration is not implemented yet: {adapter_name}",
        )
