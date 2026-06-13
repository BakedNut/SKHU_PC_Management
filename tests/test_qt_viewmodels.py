from __future__ import annotations

from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.domain.checks.models import CheckResult, CheckStatus
from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult
from skhu_pc_management.domain.pc.models import PcInfo
from skhu_pc_management.domain.settings.models import ApplyResult, ApplySettingsResult, SettingStatus
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


class FakeLoadPcInfo:
    def execute(self) -> PcInfo:
        return PcInfo(
            computer_name="PC01",
            user_name="student",
            os_name="Windows 11",
            windows_build="26100",
            cpu_name="CPU",
            memory_gb=16,
        )


class FakeCheckSettingsStatus:
    def execute(self, setting_ids: list[str]) -> list[SettingStatus]:
        return [
            SettingStatus(
                setting_id=setting_ids[0],
                label="설정",
                status_text="configured",
                actual_value=0,
                is_configured=True,
            )
        ]


class FakeApplySettings:
    def execute(self, setting_ids: list[str]) -> ApplySettingsResult:
        return ApplySettingsResult(
            [ApplyResult(setting_id=setting_ids[0], name="설정", success=True, status="applied", message="ok")]
        )


class FakeListAdapters:
    def execute(self) -> list[NetworkAdapterInfo]:
        return [NetworkAdapterInfo(name="Ethernet", description="Ethernet", is_enabled=True)]


class FakeApplyStaticIp:
    def execute(self, config) -> NetworkConfigResult:
        return NetworkConfigResult("apply_static_ip", True, config.adapter_name, "applied")


class FakeSetDhcp:
    def execute(self, adapter_name: str) -> NetworkConfigResult:
        return NetworkConfigResult("set_dhcp", True, adapter_name, "dhcp")


class FakeRunPcChecks:
    def execute(self) -> list[CheckResult]:
        return [CheckResult(check_id="check", label="점검", status=CheckStatus.OK, message="ok")]


class FakeActivation:
    def __init__(self, action: str) -> None:
        self.action = action

    def execute(self) -> ActivationResult:
        return ActivationResult(True, self.action, "prepared", "process", True)


def test_pc_info_viewmodel_refresh_updates_rows() -> None:
    view_model = PcInfoViewModel(FakeLoadPcInfo())

    view_model.refresh()

    assert view_model.status_message == "PC 정보를 불러왔습니다."
    assert ("PC 이름", "PC01") in view_model.rows


def test_settings_viewmodel_updates_status_and_apply_rows() -> None:
    view_model = SettingsViewModel(FakeCheckSettingsStatus(), FakeApplySettings())

    view_model.check_status(["hide_frequent_folders"])
    assert view_model.result_rows == [("설정", "configured", "0")]

    view_model.apply_selected(["hide_frequent_folders"])
    assert view_model.result_rows == [("설정", "applied", "ok")]


def test_network_viewmodel_calls_use_cases() -> None:
    view_model = NetworkViewModel(FakeListAdapters(), FakeApplyStaticIp(), FakeSetDhcp())

    view_model.load_adapters()
    assert view_model.adapters[0].name == "Ethernet"

    view_model.apply_static_ip("Ethernet", "192.168.0.10", "255.255.255.0", "192.168.0.1", "", "")
    assert view_model.status_message == "applied"

    view_model.set_dhcp("Ethernet")
    assert view_model.status_message == "dhcp"


def test_pc_check_viewmodel_updates_rows() -> None:
    view_model = PcCheckViewModel(FakeRunPcChecks())

    view_model.run_checks()

    assert view_model.result_rows == [("점검", "ok", "ok")]


def test_activation_viewmodel_does_not_expose_product_key() -> None:
    view_model = ActivationViewModel(FakeActivation("windows_activation"), FakeActivation("office_activation"))

    view_model.prepare_windows_activation()
    assert view_model.status_message == "prepared"

    view_model.prepare_office_activation()
    assert view_model.status_message == "prepared"
