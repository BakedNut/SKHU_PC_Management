from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import ip_address


@dataclass(frozen=True)
class StaticIpConfig:
    adapter_name: str
    ip_address: str
    subnet_mask: str
    gateway: str
    dns1: str | None = None
    dns2: str | None = None
    dns_servers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        adapter_name = self.adapter_name.strip()
        if not adapter_name:
            raise ValueError("adapter_name is required.")

        object.__setattr__(self, "adapter_name", adapter_name)
        object.__setattr__(self, "ip_address", _validate_ip(self.ip_address, "ip_address"))
        object.__setattr__(self, "subnet_mask", _validate_ip(self.subnet_mask, "subnet_mask"))
        object.__setattr__(self, "gateway", _validate_ip(self.gateway, "gateway"))

        dns1 = _empty_to_none(self.dns1)
        dns2 = _empty_to_none(self.dns2)
        if self.dns_servers:
            if dns1 is None and len(self.dns_servers) >= 1:
                dns1 = self.dns_servers[0]
            if dns2 is None and len(self.dns_servers) >= 2:
                dns2 = self.dns_servers[1]
            if len(self.dns_servers) > 2:
                raise ValueError("Only primary and secondary DNS servers are supported.")

        if dns2 and not dns1:
            raise ValueError("dns1 is required when dns2 is provided.")

        if dns1:
            dns1 = _validate_ip(dns1, "dns1")
        if dns2:
            dns2 = _validate_ip(dns2, "dns2")

        object.__setattr__(self, "dns1", dns1)
        object.__setattr__(self, "dns2", dns2)
        object.__setattr__(self, "dns_servers", tuple(value for value in (dns1, dns2) if value))


@dataclass(frozen=True)
class NetworkAdapterInfo:
    name: str
    description: str
    is_enabled: bool
    mac_address: str | None = None
    ip_addresses: tuple[str, ...] = ()
    subnet_mask: str | None = None
    gateway: str | None = None
    dns_servers: tuple[str, ...] = ()
    is_dhcp_enabled: bool | None = None


@dataclass(frozen=True)
class NetworkConfigResult:
    operation: str
    success: bool
    adapter_name: str
    message: str = ""
    commands: tuple[tuple[str, ...], ...] = field(default_factory=tuple)


def _validate_ip(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    try:
        ip_address(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid IP address: {value}") from exc
    return text


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
