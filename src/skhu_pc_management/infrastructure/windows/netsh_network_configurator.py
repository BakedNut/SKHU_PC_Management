from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult, StaticIpConfig
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class NetshNetworkConfigurator:
    command_runner: CommandRunner

    def list_adapters(self) -> list[NetworkAdapterInfo]:
        try:
            adapters = self._list_adapters_with_powershell()
        except Exception:
            adapters = []

        if adapters:
            return adapters

        return self._list_adapters_with_netsh()

    def _list_adapters_with_powershell(self) -> list[NetworkAdapterInfo]:
        detailed_output = self.command_runner.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _POWERSHELL_DETAILED_ADAPTER_SCRIPT,
            )
        )
        detailed_adapters = _parse_powershell_detailed_adapters(detailed_output)
        if detailed_adapters:
            return detailed_adapters

        output = self.command_runner.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress | ConvertTo-Json -Depth 3",
            )
        )
        adapters = _parse_powershell_adapters(output)
        return [self._enrich_adapter_details(adapter) for adapter in adapters]

    def _list_adapters_with_netsh(self) -> list[NetworkAdapterInfo]:
        output = self.command_runner.run(("netsh", "interface", "show", "interface"))
        adapters: list[NetworkAdapterInfo] = []

        for name, is_enabled in _parse_interface_names(output):
            details = self._read_adapter_details(name)
            adapters.append(
                NetworkAdapterInfo(
                    name=name,
                    description=name,
                    is_enabled=is_enabled,
                    ip_addresses=details["ip_addresses"],
                    subnet_mask=details["subnet_mask"],
                    gateway=details["gateway"],
                    dns_servers=details["dns_servers"],
                    is_dhcp_enabled=details["is_dhcp_enabled"],
                )
            )

        return sorted(adapters, key=lambda adapter: (not _is_preferred_adapter_name(adapter.name), adapter.name))

    def apply_static_ip(self, config: StaticIpConfig) -> NetworkConfigResult:
        commands: list[tuple[str, ...]] = [
            (
                "netsh",
                "interface",
                "ip",
                "set",
                "address",
                config.adapter_name,
                "static",
                config.ip_address,
                config.subnet_mask,
                config.gateway,
            )
        ]

        if config.dns1:
            commands.append(
                (
                    "netsh",
                    "interface",
                    "ip",
                    "set",
                    "dns",
                    config.adapter_name,
                    "static",
                    config.dns1,
                )
            )
            if config.dns2:
                commands.append(
                    (
                        "netsh",
                        "interface",
                        "ip",
                        "add",
                        "dns",
                        config.adapter_name,
                        config.dns2,
                        "index=2",
                    )
                )
        else:
            commands.append(
                (
                    "netsh",
                    "interface",
                    "ip",
                    "set",
                    "dns",
                    config.adapter_name,
                    "dhcp",
                )
            )

        return self._run_commands("apply_static_ip", config.adapter_name, commands)

    def set_dhcp(self, adapter_name: str) -> NetworkConfigResult:
        adapter_name = adapter_name.strip()
        if not adapter_name:
            return NetworkConfigResult(
                operation="set_dhcp",
                success=False,
                adapter_name="",
                message="adapter_name is required.",
            )

        commands = [
            ("netsh", "interface", "ip", "set", "address", adapter_name, "dhcp"),
            ("netsh", "interface", "ip", "set", "dns", adapter_name, "dhcp"),
        ]
        return self._run_commands("set_dhcp", adapter_name, commands)

    def _run_commands(
        self,
        operation: str,
        adapter_name: str,
        commands: list[tuple[str, ...]],
    ) -> NetworkConfigResult:
        executed: list[tuple[str, ...]] = []
        try:
            for command in commands:
                self.command_runner.run(command)
                executed.append(command)
        except Exception as exc:
            return NetworkConfigResult(
                operation=operation,
                success=False,
                adapter_name=adapter_name,
                message=str(exc),
                commands=tuple(executed),
            )

        return NetworkConfigResult(
            operation=operation,
            success=True,
            adapter_name=adapter_name,
            message="Applied.",
            commands=tuple(executed),
        )

    def _read_adapter_details(self, adapter_name: str) -> dict[str, object]:
        try:
            output = self.command_runner.run(
                ("netsh", "interface", "ip", "show", "config", f"name={adapter_name}")
            )
        except Exception:
            output = ""
        return _parse_ip_config(output)

    def _enrich_adapter_details(self, adapter: NetworkAdapterInfo) -> NetworkAdapterInfo:
        details = self._read_adapter_details(adapter.name)
        return NetworkAdapterInfo(
            name=adapter.name,
            description=adapter.description,
            is_enabled=adapter.is_enabled,
            mac_address=adapter.mac_address,
            ip_addresses=details["ip_addresses"],
            subnet_mask=details["subnet_mask"],
            gateway=details["gateway"],
            dns_servers=details["dns_servers"],
            is_dhcp_enabled=details["is_dhcp_enabled"],
        )


def _parse_interface_names(output: str) -> list[tuple[str, bool]]:
    adapters: list[tuple[str, bool]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("-") or "Admin State" in line or "관리자" in line:
            continue

        parts = line.split(None, 3)
        if len(parts) < 4:
            continue

        admin_state, _, _, name = parts
        if not _is_supported_adapter_name(name):
            continue

        is_enabled = admin_state.lower() in {"enabled", "사용", "활성", "활성화"}
        adapters.append((name.strip(), is_enabled))
    return adapters


def _parse_powershell_adapters(output: str) -> list[NetworkAdapterInfo]:
    if not output.strip():
        return []

    data = json.loads(output)
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return []

    adapters: list[NetworkAdapterInfo] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        adapter = _adapter_from_powershell_item(item)
        if adapter is not None:
            adapters.append(adapter)

    return sorted(adapters, key=lambda adapter: (_status_sort_key(adapter), adapter.name.lower()))


def _parse_powershell_detailed_adapters(output: str) -> list[NetworkAdapterInfo]:
    if not output.strip():
        return []
    data = json.loads(output)
    items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
    adapters: list[NetworkAdapterInfo] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        adapter = _detailed_adapter_from_powershell_item(item)
        if adapter is not None:
            adapters.append(adapter)
    return sorted(adapters, key=lambda adapter: (_status_sort_key(adapter), adapter.name.lower()))


def _adapter_from_powershell_item(item: dict[str, Any]) -> NetworkAdapterInfo | None:
    name = str(item.get("Name") or "").strip()
    description = str(item.get("InterfaceDescription") or name).strip()
    status = str(item.get("Status") or "").strip()
    mac_address = _empty_to_none(item.get("MacAddress"))

    if not name:
        return None
    if not _is_supported_adapter_name(f"{name} {description}"):
        return None

    return NetworkAdapterInfo(
        name=name,
        description=description,
        is_enabled=status.lower() == "up",
        mac_address=mac_address,
    )


def _detailed_adapter_from_powershell_item(item: dict[str, Any]) -> NetworkAdapterInfo | None:
    base = _adapter_from_powershell_item(item)
    if base is None:
        return None
    ip_addresses = tuple(value for value in _string_list(item.get("IPv4Addresses")) if _looks_like_ip(value))
    prefix_length = _first_int(item.get("IPv4PrefixLength"))
    subnet_mask = _prefix_length_to_subnet_mask(prefix_length) if prefix_length is not None else None
    gateways = _string_list(item.get("IPv4DefaultGateway"))
    dns_servers = tuple(value for value in _string_list(item.get("DnsServers")) if _looks_like_ip(value))
    dhcp_value = item.get("Dhcp")
    return NetworkAdapterInfo(
        name=base.name,
        description=base.description,
        is_enabled=base.is_enabled,
        mac_address=base.mac_address,
        ip_addresses=ip_addresses,
        subnet_mask=subnet_mask,
        gateway=gateways[0] if gateways else None,
        dns_servers=dns_servers,
        is_dhcp_enabled=_parse_boolish(dhcp_value),
    )


def _parse_ip_config(output: str) -> dict[str, object]:
    ip_addresses: list[str] = []
    subnet_mask: str | None = None
    gateway: str | None = None
    dns_servers: list[str] = []
    is_dhcp_enabled: bool | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        lower = line.lower()

        if "dhcp enabled" in lower or "dhcp 사용" in lower:
            is_dhcp_enabled = line.split(":", 1)[-1].strip().lower() in {"yes", "예", "true", "사용함"}
        elif "ip address" in lower or "ip 주소" in lower:
            value = _value_after_colon(line)
            ip_address = _first_ipv4(value or "")
            if ip_address:
                ip_addresses.append(ip_address)
        elif ("subnet prefix" in lower or "서브넷 접두사" in lower) and ("mask" in lower or "마스크" in lower):
            subnet_mask = _extract_mask(line)
        elif "default gateway" in lower or "기본 게이트웨이" in lower:
            gateway = _first_ipv4(_value_after_colon(line) or "") or gateway
        elif "dns servers" in lower or "dns 서버" in lower:
            value = _value_after_colon(line)
            dns_server = _first_ipv4(value or "")
            if dns_server:
                dns_servers.append(dns_server)
        elif dns_servers:
            dns_server = _first_ipv4(line)
            if dns_server:
                dns_servers.append(dns_server)

    return {
        "ip_addresses": tuple(ip_addresses),
        "subnet_mask": subnet_mask,
        "gateway": gateway,
        "dns_servers": tuple(dns_servers),
        "is_dhcp_enabled": is_dhcp_enabled,
    }


def _value_after_colon(line: str) -> str | None:
    if ":" not in line:
        return None
    value = line.split(":", 1)[1].strip()
    return value or None


def _empty_to_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _looks_like_ip(value: str) -> bool:
    return value.count(".") == 3 and all(part.isdigit() for part in value.split("."))


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _first_int(value: object) -> int | None:
    if isinstance(value, list):
        value = value[0] if value else None
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _parse_boolish(value: object) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "enabled", "yes", "예", "사용", "사용함"}:
        return True
    if text in {"false", "disabled", "no", "아니요", "사용 안 함"}:
        return False
    return None


def _prefix_length_to_subnet_mask(prefix_length: int) -> str:
    if not 0 <= prefix_length <= 32:
        raise ValueError(f"Invalid IPv4 prefix length: {prefix_length}")
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    return ".".join(str((mask >> shift) & 0xFF) for shift in (24, 16, 8, 0))


_IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _first_ipv4(value: str) -> str | None:
    match = _IPV4_PATTERN.search(value)
    return match.group(0) if match else None


def _extract_mask(line: str) -> str | None:
    for marker in ("mask", "마스크"):
        if marker in line.lower():
            return _first_ipv4(line.lower().rsplit(marker, 1)[-1])
        if marker in line:
            return _first_ipv4(line.rsplit(marker, 1)[-1])
    return None


def _is_supported_adapter_name(name: str) -> bool:
    lower = name.lower()
    excluded_tokens = (
        "bluetooth",
        "virtualbox",
        "vmware",
        "hyper-v",
        "vpn",
        "openvpn",
        "tailscale",
        "tunnel",
        "tap-windows",
        "loopback",
        "isatap",
        "teredo",
        "pseudo-interface",
    )
    return not any(token in lower for token in excluded_tokens)


def _is_preferred_adapter_name(name: str) -> bool:
    return name.lower() in {"ethernet", "이더넷"}


def _status_sort_key(adapter: NetworkAdapterInfo) -> int:
    return 0 if adapter.is_enabled else 1


_POWERSHELL_DETAILED_ADAPTER_SCRIPT = r"""
$adapters = Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress
$items = foreach ($adapter in $adapters) {
    $ipConfig = Get-NetIPConfiguration -InterfaceAlias $adapter.Name -ErrorAction SilentlyContinue
    $dns = Get-DnsClientServerAddress -InterfaceAlias $adapter.Name -AddressFamily IPv4 -ErrorAction SilentlyContinue
    $ipInterface = Get-NetIPInterface -InterfaceAlias $adapter.Name -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1
    [PSCustomObject]@{
        Name = $adapter.Name
        InterfaceDescription = $adapter.InterfaceDescription
        Status = $adapter.Status
        MacAddress = $adapter.MacAddress
        IPv4Addresses = @($ipConfig.IPv4Address.IPAddress)
        IPv4PrefixLength = @($ipConfig.IPv4Address.PrefixLength)
        IPv4DefaultGateway = @($ipConfig.IPv4DefaultGateway.NextHop)
        DnsServers = @($dns.ServerAddresses)
        Dhcp = $ipInterface.Dhcp
    }
}
$items | ConvertTo-Json -Depth 5
""".strip()
