from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.network.models import NetworkConfigResult, StaticIpConfig
from skhu_pc_management.ports.network_configurator import NetworkConfigurator


@dataclass(frozen=True)
class ApplyStaticIp:
    network_configurator: NetworkConfigurator
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, config: StaticIpConfig) -> NetworkConfigResult:
        blocked_message = self.safety_guard.blocked_message("apply_static_ip")
        if blocked_message is not None:
            return NetworkConfigResult(
                operation="apply_static_ip",
                success=False,
                adapter_name=config.adapter_name,
                message=blocked_message,
            )

        try:
            return self.network_configurator.apply_static_ip(config)
        except Exception as exc:
            return NetworkConfigResult(
                operation="apply_static_ip",
                success=False,
                adapter_name=config.adapter_name,
                message=str(exc),
            )


ApplyStaticIpUseCase = ApplyStaticIp
