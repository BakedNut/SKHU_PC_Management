from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.network.models import NetworkConfigResult
from skhu_pc_management.ports.network_configurator import NetworkConfigurator


@dataclass(frozen=True)
class SetDhcp:
    network_configurator: NetworkConfigurator
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, adapter_name: str) -> NetworkConfigResult:
        adapter_name = adapter_name.strip()
        if not adapter_name:
            return NetworkConfigResult(
                operation="set_dhcp",
                success=False,
                adapter_name="",
                message="adapter_name is required.",
            )

        blocked_message = self.safety_guard.blocked_message("set_dhcp")
        if blocked_message is not None:
            return NetworkConfigResult(
                operation="set_dhcp",
                success=False,
                adapter_name=adapter_name,
                message=blocked_message,
            )

        try:
            return self.network_configurator.set_dhcp(adapter_name)
        except Exception as exc:
            return NetworkConfigResult(
                operation="set_dhcp",
                success=False,
                adapter_name=adapter_name,
                message=str(exc),
            )


SetDhcpUseCase = SetDhcp
