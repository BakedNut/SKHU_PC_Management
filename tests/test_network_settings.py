from __future__ import annotations

from collections.abc import Sequence

import pytest

from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.list_network_adapters import ListNetworkAdapters
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult, StaticIpConfig
from skhu_pc_management.infrastructure.windows import netsh_network_configurator
from skhu_pc_management.infrastructure.windows.netsh_network_configurator import NetshNetworkConfigurator
from skhu_pc_management.infrastructure.windows.netsh_network_configurator import (
    _POWERSHELL_DETAILED_ADAPTER_SCRIPT,
    _parse_boolish,
    _prefix_length_to_subnet_mask,
)
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel


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


class FailingPowerShellCommandRunner(FakeCommandRunner):
    def run(self, command: Sequence[str]) -> str:
        command_tuple = tuple(command)
        self.commands.append(command_tuple)
        if command_tuple[:1] == ("powershell",):
            raise RuntimeError("powershell failed")
        return self.outputs.get(command_tuple, "")


POWERSHELL_ADAPTER_COMMAND = (
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress | ConvertTo-Json -Depth 3",
)
POWERSHELL_DETAILED_ADAPTER_COMMAND = (
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    _POWERSHELL_DETAILED_ADAPTER_SCRIPT,
)


@pytest.fixture(autouse=True)
def disable_network_adapter_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netsh_network_configurator, "read_network_adapters_fast", lambda: [])


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


def test_netsh_configurator_returns_clear_command_failure_message() -> None:
    class FailingRunner:
        def run(self, command: Sequence[str]) -> str:
            raise RuntimeError("관리자 권한이 필요합니다.")

    configurator = NetshNetworkConfigurator(FailingRunner())
    config = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
        dns1="8.8.8.8",
        dns2="1.1.1.1",
    )

    result = configurator.apply_static_ip(config)

    assert result.success is False
    assert "관리자 권한" in result.message
    assert "'NoneType' object has no attribute 'strip'" not in result.message


def test_netsh_configurator_uses_fallback_when_failure_message_is_empty() -> None:
    class EmptyMessageFailingRunner:
        def run(self, command: Sequence[str]) -> str:
            raise RuntimeError("")

    configurator = NetshNetworkConfigurator(EmptyMessageFailingRunner())
    config = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
    )

    result = configurator.apply_static_ip(config)

    assert result.success is False
    assert result.message == "명령 실행에 실패했습니다."


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


def test_network_configurator_reads_powershell_json_adapters() -> None:
    output = """
[
  {
    "Name": "이더넷",
    "InterfaceDescription": "Realtek Gaming 2.5GbE Family Controller",
    "Status": "Up",
    "MacAddress": "00-11-22-33-44-55"
  },
  {
    "Name": "Wi-Fi",
    "InterfaceDescription": "RZ616 Wi-Fi 6E 160MHz",
    "Status": "Disconnected",
    "MacAddress": "AA-BB-CC-DD-EE-FF"
  }
]
"""
    command_runner = FakeCommandRunner({POWERSHELL_ADAPTER_COMMAND: output})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert [adapter.name for adapter in adapters] == ["이더넷", "Wi-Fi"]
    assert adapters[0].description == "Realtek Gaming 2.5GbE Family Controller"
    assert adapters[0].is_enabled is True
    assert adapters[0].mac_address == "00-11-22-33-44-55"
    assert adapters[1].description == "RZ616 Wi-Fi 6E 160MHz"
    assert adapters[1].is_enabled is False


def test_network_configurator_filters_virtual_powershell_adapters() -> None:
    output = """
[
  {"Name": "VirtualBox Host-Only Network", "InterfaceDescription": "VirtualBox Adapter", "Status": "Up", "MacAddress": "00"},
  {"Name": "OpenVPN TAP", "InterfaceDescription": "TAP-Windows Adapter V9", "Status": "Up", "MacAddress": "11"},
  {"Name": "Tailscale", "InterfaceDescription": "Tailscale Tunnel", "Status": "Up", "MacAddress": "22"},
  {"Name": "Bluetooth Network Connection", "InterfaceDescription": "Bluetooth Device", "Status": "Disconnected", "MacAddress": "33"},
  {"Name": "Wi-Fi", "InterfaceDescription": "RZ616 Wi-Fi 6E 160MHz", "Status": "Disconnected", "MacAddress": "44"}
]
"""
    command_runner = FakeCommandRunner({POWERSHELL_ADAPTER_COMMAND: output})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert [adapter.name for adapter in adapters] == ["Wi-Fi"]


def test_network_configurator_handles_single_powershell_json_object() -> None:
    output = """
{
  "Name": "이더넷",
  "InterfaceDescription": "Realtek Gaming 2.5GbE Family Controller",
  "Status": "Up",
  "MacAddress": "00-11-22-33-44-55"
}
"""
    command_runner = FakeCommandRunner({POWERSHELL_ADAPTER_COMMAND: output})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert len(adapters) == 1
    assert adapters[0].name == "이더넷"


def test_network_configurator_falls_back_to_netsh_when_powershell_fails() -> None:
    show_interface = """
Admin State    State          Type             Interface Name
-------------------------------------------------------------------------
Enabled        Connected      Dedicated        Ethernet
"""
    command_runner = FailingPowerShellCommandRunner(
        {
            ("netsh", "interface", "show", "interface"): show_interface,
            ("netsh", "interface", "ip", "show", "config", "name=Ethernet"): "",
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert [adapter.name for adapter in adapters] == ["Ethernet"]
    assert command_runner.commands[0] == POWERSHELL_DETAILED_ADAPTER_COMMAND
    assert ("netsh", "interface", "show", "interface") in command_runner.commands


def test_netsh_configurator_lists_non_english_physical_adapter_names() -> None:
    show_interface = """
Admin State    State          Type             Interface Name
-------------------------------------------------------------------------
Enabled        Connected      Dedicated        회사 유선랜
Enabled        Connected      Dedicated        Teredo Tunneling Pseudo-Interface
"""
    command_runner = FakeCommandRunner(
        {
            ("netsh", "interface", "show", "interface"): show_interface,
            ("netsh", "interface", "ip", "show", "config", "name=회사 유선랜"): "",
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert [adapter.name for adapter in adapters] == ["회사 유선랜"]


def test_netsh_configurator_parses_korean_ip_config_output() -> None:
    show_interface = """
관리자 상태     상태            종류             인터페이스 이름
-------------------------------------------------------------------------
사용             연결됨          전용             이더넷
"""
    adapter_config = """
인터페이스 "이더넷"에 대한 구성
    DHCP 사용:                             아니요
    IP 주소:                               192.168.10.20
    서브넷 접두사:                         192.168.10.0/24(마스크 255.255.255.0)
    기본 게이트웨이:                       192.168.10.1
    DNS 서버:                              8.8.8.8
                                           1.1.1.1
"""
    command_runner = FakeCommandRunner(
        {
            ("netsh", "interface", "show", "interface"): show_interface,
            ("netsh", "interface", "ip", "show", "config", "name=이더넷"): adapter_config,
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert adapters[0].ip_addresses == ("192.168.10.20",)
    assert adapters[0].subnet_mask == "255.255.255.0"
    assert adapters[0].gateway == "192.168.10.1"
    assert adapters[0].dns_servers == ("8.8.8.8", "1.1.1.1")


def test_network_configurator_reads_detailed_powershell_json() -> None:
    output = """
{
  "Name": "이더넷",
  "InterfaceDescription": "Realtek Gaming 2.5GbE Family Controller",
  "Status": "Up",
  "MacAddress": "00-11-22-33-44-55",
  "IPv4Addresses": ["192.168.10.20"],
  "IPv4PrefixLength": [24],
  "IPv4DefaultGateway": ["192.168.10.1"],
  "DnsServers": ["8.8.8.8", "1.1.1.1"],
  "Dhcp": "Disabled"
}
"""
    command_runner = FakeCommandRunner({POWERSHELL_DETAILED_ADAPTER_COMMAND: output})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert len(adapters) == 1
    assert adapters[0].ip_addresses == ("192.168.10.20",)
    assert adapters[0].subnet_mask == "255.255.255.0"
    assert adapters[0].gateway == "192.168.10.1"
    assert adapters[0].dns_servers == ("8.8.8.8", "1.1.1.1")
    assert adapters[0].is_dhcp_enabled is False


def test_network_configurator_uses_fast_path_without_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        netsh_network_configurator,
        "read_network_adapters_fast",
        lambda: [
            NetworkAdapterInfo(
                name="Ethernet",
                description="Intel Ethernet",
                is_enabled=True,
                mac_address="00-11-22-33-44-55",
                ip_addresses=("192.168.0.10",),
                subnet_mask="255.255.255.0",
                gateway="192.168.0.1",
                is_dhcp_enabled=None,
            )
        ],
    )
    command_runner = FakeCommandRunner({POWERSHELL_DETAILED_ADAPTER_COMMAND: "[]"})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert [adapter.name for adapter in adapters] == ["Ethernet"]
    assert adapters[0].is_dhcp_enabled is None
    assert command_runner.commands == []


def test_network_configurator_uses_powershell_when_fast_path_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netsh_network_configurator, "read_network_adapters_fast", lambda: [])
    command_runner = FakeCommandRunner(
        {
            POWERSHELL_DETAILED_ADAPTER_COMMAND: """
{
  "Name": "Ethernet",
  "InterfaceDescription": "Intel Ethernet",
  "Status": "Up",
  "MacAddress": "00-11-22-33-44-55",
  "IPv4Addresses": ["192.168.0.10"],
  "IPv4PrefixLength": [24],
  "IPv4DefaultGateway": ["192.168.0.1"],
  "DnsServers": [],
  "Dhcp": "Enabled"
}
"""
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert adapters[0].name == "Ethernet"
    assert command_runner.commands[0] == POWERSHELL_DETAILED_ADAPTER_COMMAND


def test_network_configurator_uses_powershell_when_fast_path_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_fast_path() -> list[NetworkAdapterInfo]:
        raise OSError("GetAdaptersAddresses failed")

    monkeypatch.setattr(netsh_network_configurator, "read_network_adapters_fast", fail_fast_path)
    command_runner = FakeCommandRunner(
        {
            POWERSHELL_DETAILED_ADAPTER_COMMAND: """
{
  "Name": "Wi-Fi",
  "InterfaceDescription": "Intel Wi-Fi",
  "Status": "Up",
  "MacAddress": "00-11-22-33-44-55",
  "IPv4Addresses": ["192.168.0.20"],
  "IPv4PrefixLength": [24],
  "IPv4DefaultGateway": ["192.168.0.1"],
  "DnsServers": [],
  "Dhcp": null
}
"""
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert adapters[0].name == "Wi-Fi"
    assert command_runner.commands[0] == POWERSHELL_DETAILED_ADAPTER_COMMAND


def test_parse_boolish_handles_windows_and_common_tokens() -> None:
    assert _parse_boolish(True) is True
    assert _parse_boolish(False) is False
    assert _parse_boolish(1) is True
    assert _parse_boolish(0) is False
    assert _parse_boolish("Enabled") is True
    assert _parse_boolish("Disabled") is False
    assert _parse_boolish("on") is True
    assert _parse_boolish("off") is False
    assert _parse_boolish("사용함") is True
    assert _parse_boolish("사용 안 함") is False
    assert _parse_boolish(["Enabled"]) is True


def test_network_configurator_reads_enabled_dhcp_from_detailed_powershell_json() -> None:
    output = """
{
  "Name": "Wi-Fi",
  "InterfaceDescription": "RZ616 Wi-Fi 6E 160MHz",
  "Status": "Disconnected",
  "MacAddress": "00-11-22-33-44-55",
  "IPv4Addresses": [],
  "IPv4PrefixLength": [],
  "IPv4DefaultGateway": [],
  "DnsServers": [],
  "Dhcp": "Enabled"
}
"""
    command_runner = FakeCommandRunner({POWERSHELL_DETAILED_ADAPTER_COMMAND: output})

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert adapters[0].is_dhcp_enabled is True


def test_network_configurator_fills_only_missing_dhcp_from_netsh_when_powershell_ip_exists() -> None:
    detailed_output = """
{
  "Name": "이더넷",
  "InterfaceDescription": "Realtek Gaming 2.5GbE Family Controller",
  "Status": "Up",
  "MacAddress": "00-11-22-33-44-55",
  "IPv4Addresses": ["192.168.10.20"],
  "IPv4PrefixLength": [24],
  "IPv4DefaultGateway": ["192.168.10.1"],
  "DnsServers": ["8.8.8.8"],
  "Dhcp": null
}
"""
    netsh_output = """
Configuration for interface "이더넷"
    DHCP enabled:                         Yes
    IP Address:                           10.0.0.20
    Default Gateway:                      10.0.0.1
"""
    command_runner = FakeCommandRunner(
        {
            POWERSHELL_DETAILED_ADAPTER_COMMAND: detailed_output,
            ("netsh", "interface", "ip", "show", "config", "name=이더넷"): netsh_output,
        }
    )

    adapters = NetshNetworkConfigurator(command_runner).list_adapters()

    assert adapters[0].ip_addresses == ("192.168.10.20",)
    assert adapters[0].gateway == "192.168.10.1"
    assert adapters[0].dns_servers == ("8.8.8.8",)
    assert adapters[0].is_dhcp_enabled is True


def test_prefix_length_to_subnet_mask() -> None:
    assert _prefix_length_to_subnet_mask(24) == "255.255.255.0"
    assert _prefix_length_to_subnet_mask(16) == "255.255.0.0"


def test_network_viewmodel_reloads_adapters_after_static_ip_success() -> None:
    class ReloadingListAdapters:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self) -> list[NetworkAdapterInfo]:
            self.calls += 1
            ip = "192.168.0.10" if self.calls == 1 else "192.168.0.20"
            return [NetworkAdapterInfo("Ethernet", "Ethernet", True, ip_addresses=(ip,), subnet_mask="255.255.255.0")]

    list_adapters = ReloadingListAdapters()
    view_model = NetworkViewModel(
        list_adapters,
        ApplyStaticIp(FakeNetworkConfigurator()),
        SetDhcp(FakeNetworkConfigurator()),
        reload_sleep=lambda _: None,
    )
    view_model.load_adapters()

    view_model.apply_static_ip("Ethernet", "192.168.0.20", "255.255.255.0", "192.168.0.1", "", "")

    assert list_adapters.calls == 2
    assert view_model.selected_adapter is not None
    assert view_model.selected_adapter.ip_addresses == ("192.168.0.20",)


def test_network_viewmodel_reloads_adapters_after_dhcp_success() -> None:
    class ReloadingListAdapters:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self) -> list[NetworkAdapterInfo]:
            self.calls += 1
            return [NetworkAdapterInfo("Ethernet", "Ethernet", True, is_dhcp_enabled=self.calls > 1)]

    list_adapters = ReloadingListAdapters()
    view_model = NetworkViewModel(
        list_adapters,
        ApplyStaticIp(FakeNetworkConfigurator()),
        SetDhcp(FakeNetworkConfigurator()),
        reload_sleep=lambda _: None,
    )
    view_model.load_adapters()

    view_model.set_dhcp("Ethernet")

    assert list_adapters.calls == 2
    assert view_model.ip_status_text == "자동 IP(DHCP)"


def test_network_viewmodel_retries_adapter_reload_until_expected_static_ip_is_visible() -> None:
    class SlowlyUpdatingListAdapters:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self) -> list[NetworkAdapterInfo]:
            self.calls += 1
            ip = "192.168.0.10" if self.calls <= 2 else "192.168.0.20"
            return [NetworkAdapterInfo("Ethernet", "Ethernet", True, ip_addresses=(ip,), subnet_mask="255.255.255.0")]

    list_adapters = SlowlyUpdatingListAdapters()
    view_model = NetworkViewModel(
        list_adapters,
        ApplyStaticIp(FakeNetworkConfigurator()),
        SetDhcp(FakeNetworkConfigurator()),
        reload_sleep=lambda _: None,
    )
    view_model.load_adapters()

    view_model.apply_static_ip("Ethernet", "192.168.0.20", "255.255.255.0", "192.168.0.1", "", "")

    assert list_adapters.calls == 3
    assert view_model.selected_adapter is not None
    assert view_model.selected_adapter.ip_addresses == ("192.168.0.20",)


def test_network_viewmodel_keeps_message_when_reload_fails() -> None:
    class FailingReloadListAdapters:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self) -> list[NetworkAdapterInfo]:
            self.calls += 1
            if self.calls == 1:
                return [NetworkAdapterInfo("Ethernet", "Ethernet", True, ip_addresses=("192.168.0.10",))]
            raise RuntimeError("reload failed")

    list_adapters = FailingReloadListAdapters()
    view_model = NetworkViewModel(
        list_adapters,
        ApplyStaticIp(FakeNetworkConfigurator()),
        SetDhcp(FakeNetworkConfigurator()),
        reload_sleep=lambda _: None,
    )
    view_model.load_adapters()

    view_model.apply_static_ip("Ethernet", "192.168.0.20", "255.255.255.0", "192.168.0.1", "", "")

    assert "상태 재조회 실패: reload failed" in view_model.status_message


def test_network_viewmodel_displays_unknown_dhcp_as_check_unavailable() -> None:
    view_model = NetworkViewModel(FakeNetworkConfigurator(), FakeNetworkConfigurator(), FakeNetworkConfigurator())
    view_model.adapters = [NetworkAdapterInfo("Ethernet", "Ethernet", True, is_dhcp_enabled=None)]

    view_model.select_adapter_by_name("Ethernet")

    assert view_model.ip_status_text == "확인 불가"
    assert ("IP 할당 방식", "확인 불가") in view_model.current_network_info_rows


def test_network_viewmodel_rejects_incomplete_ip_prefix_with_korean_message() -> None:
    view_model = NetworkViewModel(FakeNetworkConfigurator(), FakeNetworkConfigurator(), FakeNetworkConfigurator())

    ok, message = view_model.validate_static_ip_fields("Ethernet", "192.168.", "255.255.255.0", "192.168.0.1", "", "")

    assert ok is False
    assert message == "IP 주소 형식이 올바르지 않습니다. IP 주소의 마지막 값을 입력하세요."
