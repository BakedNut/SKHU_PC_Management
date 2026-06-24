from skhu_pc_management.domain.checks.models import CheckResult
from skhu_pc_management.domain.network.models import NetworkAdapterInfo, StaticIpConfig
from skhu_pc_management.domain.pc.models import DiskInfo, PcInfo, PcNetworkInfo
from skhu_pc_management.domain.settings.definitions import RegistrySettingDefinition, SettingDefinition
from skhu_pc_management.domain.settings.models import ApplyResult, SettingStatus


def test_domain_models_can_be_created() -> None:
    disk = DiskInfo(name="C:", total_gb=512.0, free_gb=128.0)
    pc_info = PcInfo(
        computer_name="PC01",
        user_name="student",
        os_name="Windows",
        cpu_name="CPU",
        memory_gb=16.0,
        disks=[disk],
    )
    definition = RegistrySettingDefinition(
        setting_id="example",
        name="example",
        root="HKCU",
        path=r"Software\Example",
        value_name="Enabled",
        expected_value=1,
        value_type="REG_DWORD",
    )
    setting_definition = SettingDefinition(
        setting_id="example",
        name="Example setting",
        registry_values=(definition,),
    )
    static_ip = StaticIpConfig(
        adapter_name="Ethernet",
        ip_address="192.168.0.10",
        subnet_mask="255.255.255.0",
        gateway="192.168.0.1",
        dns_servers=("8.8.8.8",),
    )
    adapter = NetworkAdapterInfo(name="Ethernet", description="Adapter", is_enabled=True)
    apply_result = ApplyResult(name="example", success=True)
    status = SettingStatus(name="example", is_applied=True)
    check = CheckResult(name="example", passed=True)

    assert pc_info.disks == [disk]
    assert pc_info.network_info is None
    assert PcNetworkInfo(adapter_name="Ethernet", adapter_type="Ethernet").adapter_name == "Ethernet"
    assert definition.expected_value == 1
    assert setting_definition.registry_values == (definition,)
    assert static_ip.adapter_name == "Ethernet"
    assert adapter.is_enabled is True
    assert apply_result.success is True
    assert status.is_applied is True
    assert check.passed is True
