from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StaticIpConfig:
    adapter_name: str
    ip_address: str
    subnet_mask: str
    gateway: str
    dns_servers: tuple[str, ...] = ()


@dataclass(frozen=True)
class NetworkAdapterInfo:
    name: str
    description: str
    is_enabled: bool
    mac_address: str | None = None
    ip_addresses: tuple[str, ...] = ()
