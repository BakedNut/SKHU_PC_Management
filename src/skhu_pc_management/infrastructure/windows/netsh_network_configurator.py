from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult, StaticIpConfig
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class NetshNetworkConfigurator:
    command_runner: CommandRunner

    def list_adapters(self) -> list[NetworkAdapterInfo]:
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
            is_dhcp_enabled = line.split(":", 1)[-1].strip().lower() in {"yes", "예", "true"}
        elif "ip address" in lower or "ip 주소" in lower:
            value = _value_after_colon(line)
            if value:
                ip_addresses.append(value)
        elif "subnet prefix" in lower and "mask" in lower:
            subnet_mask = line.rsplit("mask", 1)[-1].strip(" )")
        elif "default gateway" in lower or "기본 게이트웨이" in lower:
            gateway = _value_after_colon(line) or gateway
        elif "dns servers" in lower or "dns 서버" in lower:
            value = _value_after_colon(line)
            if value and _looks_like_ip(value):
                dns_servers.append(value)
        elif dns_servers and _looks_like_ip(line):
            dns_servers.append(line)

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


def _looks_like_ip(value: str) -> bool:
    return value.count(".") == 3 and all(part.isdigit() for part in value.split("."))


def _is_supported_adapter_name(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in ("ethernet", "이더넷", "wi-fi", "wifi"))


def _is_preferred_adapter_name(name: str) -> bool:
    return name.lower() in {"ethernet", "이더넷"}
