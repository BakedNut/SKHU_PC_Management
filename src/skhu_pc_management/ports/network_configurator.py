from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult, StaticIpConfig


class NetworkConfigurator(Protocol):
    def list_adapters(self) -> list[NetworkAdapterInfo]:
        """Return available network adapters."""

    def apply_static_ip(self, config: StaticIpConfig) -> NetworkConfigResult:
        """Apply static IP configuration."""

    def set_dhcp(self, adapter_name: str) -> NetworkConfigResult:
        """Enable DHCP for an adapter."""
