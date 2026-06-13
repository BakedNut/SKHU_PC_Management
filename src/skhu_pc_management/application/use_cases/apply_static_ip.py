from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.network.models import StaticIpConfig
from skhu_pc_management.domain.settings.models import ApplyResult


@dataclass(frozen=True)
class ApplyStaticIp:
    def execute(self, config: StaticIpConfig) -> ApplyResult:
        return ApplyResult(
            name="apply_static_ip",
            success=False,
            message=f"Static IP application is not implemented yet: {config.adapter_name}",
        )
