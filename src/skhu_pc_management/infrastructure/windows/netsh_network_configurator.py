from __future__ import annotations

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, StaticIpConfig


class NetshNetworkConfigurator:
    def list_adapters(self) -> list[NetworkAdapterInfo]:
        raise NotImplementedError("Network adapter listing is not implemented yet.")

    def apply_static_ip(self, config: StaticIpConfig) -> None:
        raise NotImplementedError(f"Static IP configuration is not implemented yet: {config.adapter_name}")

    def set_dhcp(self, adapter_name: str) -> None:
        raise NotImplementedError(f"DHCP configuration is not implemented yet: {adapter_name}")
