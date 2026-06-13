from __future__ import annotations

from collections.abc import Sequence

import pytest

from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.list_network_adapters import ListNetworkAdapters
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult, StaticIpConfig
from skhu_pc_management.infrastructure.windows.netsh_network_configurator import NetshNetworkConfigurator


class FakeNetworkConfigurator:
    def __init__(self) -> None:
        self.static_configs: list[StaticIpConfig] = []
        self.dhcp_adapter_names: list[str] = []
        self.adapters = [
            NetworkAdapterInfo(
                name="Ethernet",
                description="Ethernet",
                is_enabled=True,
                ip_addresses=("192.168.0.10",),
                subnet_mask="255.255.255.0",
                gateway="192.168.0.1",
                dns_servers=("8.8.8.8",),
                is_dhcp_enabled=False,
            )
        ]

    def list_adapters(self) -> list[NetworkAdapterInfo]:
        return self.adapters

    def apply_static_ip(self, config: StaticIpConfig) -> NetworkConfigResult:
        self.static_configs.append(config)
        return NetworkConfigResult(
            operation="apply_static_ip",
            success=True,
            adapter_name=config.adapter_name,
            message="ok",
        )

    def set_dhcp(self, adapter_name: str) -> NetworkConfigResult:
        self.dhcp_adapter_names.append(adapter_name)
        return NetworkConfigResult(
            operation="set_dhcp",
            success=True,
            adapter_name=adapter_name,
            message="ok",
        )


class FakeCommandRunner:
    def __init__(self, outputs: dict[tuple[str, ...], str] | None = None) -> None:
        self.outputs = outputs or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        command_tuple = tuple(command)
        self.commands.append(command_tuple)
        return self.outputs.get(command_tuple, "")


def test_valid_static_ip_config_can_be_created() -> None:
    config = StaticIpConfig(
        adapter_name=" Ethernet ",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
        dns1="8.8.8.8",
        dns2="1.1.1.1",
    )

    assert config.adapter_name == "Ethernet"
    assert config.dns_servers == ("8.8.8.8", "1.1.1.1")


def test_invalid_ip_address_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="ip_address"):
        StaticIpConfig(
            adapter_name="Ethernet",
            ip_address="not-an-ip",
            subnet_mask="255.255.255.0",
            gateway="192.168.0.1",
        )


def test_missing_adapter_name_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="adapter_name"):
        StaticIpConfig(
            adapter_name=" ",
            ip_address="192.168.0.10",
            subnet_mask="255.255.255.0",
            gateway="192.168.0.1",
        )


def test_dns2_without_dns1_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="dns1"):
        StaticIpConfig(
            adapter_name="Ethernet",
            ip_address="192.168.0.10",
            subnet_mask="255.255.255.0",
            gateway="192.168.0.1",
            dns2="1.1.1.1",
        )


def test_apply_static_ip_use_case_calls_network_configurator_port() -> None:
    configurator = FakeNetworkConfigurator()
    use_case = ApplyStaticIp(configurator)
    config = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
    )

    result = use_case.execute(config)

    assert result.success is True
    assert configurator.static_configs == [config]


def test_set_dhcp_use_case_calls_network_configurator_port() -> None:
    configurator = FakeNetworkConfigurator()
    use_case = SetDhcp(configurator)

    result = use_case.execute(" Ethernet ")

    assert result.success is True
    assert configurator.dhcp_adapter_names == ["Ethernet"]


def test_set_dhcp_use_case_rejects_missing_adapter_name() -> None:
    configurator = FakeNetworkConfigurator()
    use_case = SetDhcp(configurator)

    result = use_case.execute(" ")

    assert result.success is False
    assert "adapter_name" in result.message
    assert configurator.dhcp_adapter_names == []


def test_list_network_adapters_use_case_calls_port() -> None:
    configurator = FakeNetworkConfigurator()

    adapters = ListNetworkAdapters(configurator).execute()

    assert adapters == configurator.adapters


def test_netsh_configurator_builds_static_ip_commands_with_dns() -> None:
    command_runner = FakeCommandRunner()
    configurator = NetshNetworkConfigurator(command_runner)
    config = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
        dns1="8.8.8.8",
        dns2="1.1.1.1",
    )

    result = configurator.apply_static_ip(config)

    assert result.success is True
    assert command_runner.commands == [
        (
            "netsh",
            "interface",
            "ip",
            "set",
            "address",
            "Ethernet",
            "static",
            "192.168.0.10",
            "255.255.255.0",
            "192.168.0.1",
        ),
        ("netsh", "interface", "ip", "set", "dns", "Ethernet", "static", "8.8.8.8"),
        ("netsh", "interface", "ip", "add", "dns", "Ethernet", "1.1.1.1", "index=2"),
    ]
    assert result.commands == tuple(command_runner.commands)


def test_netsh_configurator_sets_dns_to_dhcp_when_dns1_is_missing() -> None:
    command_runner = FakeCommandRunner()
    configurator = NetshNetworkConfigurator(command_runner)
    config = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
    )

    configurator.apply_static_ip(config)

    assert ("netsh", "interface", "ip", "set", "dns", "Ethernet", "dhcp") in command_runner.commands


def test_netsh_configurator_builds_dhcp_commands() -> None:
    command_runner = FakeCommandRunner()
    configurator = NetshNetworkConfigurator(command_runner)

    result = configurator.set_dhcp("Ethernet")

    assert result.success is True
    assert command_runner.commands == [
        ("netsh", "interface", "ip", "set", "address", "Ethernet", "dhcp"),
        ("netsh", "interface", "ip", "set", "dns", "Ethernet", "dhcp"),
    ]


def test_netsh_configurator_lists_adapters_from_command_output() -> None:
    show_interface = """
Admin State    State          Type             Interface Name
-------------------------------------------------------------------------
Enabled        Connected      Dedicated        Ethernet
Disabled       Disconnected   Dedicated        Wi-Fi
"""
    ethernet_config = """
Configuration for interface "Ethernet"
    DHCP enabled:                         No
    IP Address:                           192.168.0.10
    Subnet Prefix:                        192.168.0.0/24 (mask 255.255.255.0)
    Default Gateway:                      192.168.0.1
    DNS servers configured through DHCP:  8.8.8.8
                                           1.1.1.1
"""
    command_runner = FakeCommandRunner(
        {
            ("netsh", "interface", "show", "interface"): show_interface,
            ("netsh", "interface", "ip", "show", "config", "name=Ethernet"): ethernet_config,
            ("netsh", "interface", "ip", "show", "config", "name=Wi-Fi"): "",
        }
    )
    configurator = NetshNetworkConfigurator(command_runner)

    adapters = configurator.list_adapters()

    assert adapters[0].name == "Ethernet"
    assert adapters[0].is_enabled is True
    assert adapters[0].ip_addresses == ("192.168.0.10",)
    assert adapters[0].subnet_mask == "255.255.255.0"
    assert adapters[0].gateway == "192.168.0.1"
    assert adapters[0].dns_servers == ("8.8.8.8", "1.1.1.1")
    assert adapters[0].is_dhcp_enabled is False
