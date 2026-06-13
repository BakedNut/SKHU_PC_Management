from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.network.models import NetworkAdapterInfo
from skhu_pc_management.ports.network_configurator import NetworkConfigurator


@dataclass(frozen=True)
class ListNetworkAdapters:
    network_configurator: NetworkConfigurator

    def execute(self) -> list[NetworkAdapterInfo]:
        return self.network_configurator.list_adapters()


ListNetworkAdaptersUseCase = ListNetworkAdapters
