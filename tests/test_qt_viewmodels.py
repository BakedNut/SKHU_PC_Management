from __future__ import annotations

from skhu_pc_management.domain.activation.models import ActivationResult
from skhu_pc_management.domain.checks.models import CheckResult, CheckStatus
from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult
from skhu_pc_management.domain.pc.models import PcInfo
from skhu_pc_management.domain.settings.models import ApplyResult, ApplySettingsResult, SettingStatus
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel, _format_windows_detail
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


class FakeLoadPcInfo:
    def execute(self) -> PcInfo:
        return PcInfo(
            computer_name="PC01",
            user_name="student",
            os_name="Windows 11",
            windows_build="26100",
            windows_ubr="3323",
            windows_architecture="64-bit",
            cpu_name="CPU",
            memory_gb=16,
        )


class FakeUnknownPcInfo:
    def execute(self) -> PcInfo:
        return PcInfo(
            computer_name="PC01",
            user_name="student",
            os_name="",
            cpu_name="Unknown",
            secure_boot_status="Unknown",
            boot_mode="Unknown",
        )


class FakeCheckSettingsStatus:
    def __init__(self) -> None:
        self.requests: list[list[str]] = []

    def execute(self, setting_ids: list[str]) -> list[SettingStatus]:
        self.requests.append(setting_ids)
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
    def __init__(self) -> None:
        self.requests: list[list[str]] = []

    def execute(self, setting_ids: list[str]) -> ApplySettingsResult:
        self.requests.append(setting_ids)
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
        return [CheckResult(check_id="check", label="점검", status=CheckStatus.OK, message="Installed.")]


class FakeActivation:
    def __init__(self, action: str) -> None:
        self.action = action
        self.requests: list[str | None] = []

    def execute(self, version: str | None = None) -> ActivationResult:
        self.requests.append(version)
        return ActivationResult(True, self.action, "prepared", "process", True)


def test_pc_info_viewmodel_refresh_updates_rows() -> None:
    view_model = PcInfoViewModel(FakeLoadPcInfo())

    view_model.refresh()

    assert view_model.status_message == "PC 정보를 불러왔습니다."
    assert ("PC 이름", "PC01") in view_model.rows
    assert view_model.windows_version_detail == "26100.3323 (64비트)"


def test_settings_viewmodel_updates_status_and_apply_rows() -> None:
    check_status = FakeCheckSettingsStatus()
    apply_settings = FakeApplySettings()
    view_model = SettingsViewModel(check_status, apply_settings)

    assert view_model.summary_text == "상태 확인 필요"

    view_model.check_status(["hide_frequent_folders"])
    assert view_model.result_rows == [("설정", "-", "설정됨", "0")]
    assert view_model.summary_text == "모든 항목 정상"
    assert check_status.requests == [["hide_frequent_folders"]]

    view_model.apply_selected(["hide_frequent_folders"])
    assert view_model.result_rows == [("설정", "적용됨", "설정됨", "ok / 0")]
    assert apply_settings.requests == [["hide_frequent_folders"]]
    assert check_status.requests == [["hide_frequent_folders"], ["hide_frequent_folders"]]


def test_settings_viewmodel_summary_counts_attention_rows() -> None:
    view_model = SettingsViewModel(FakeCheckSettingsStatus(), FakeApplySettings())
    view_model.result_rows = [
        ("정상 설정", "-", "설정됨", ""),
        ("미설정 설정", "-", "미설정", "실제값 1"),
        ("확인 불가 설정", "-", "확인 불가", "권한 부족"),
    ]

    assert view_model.warning_count == 2
    assert view_model.summary_text == "확인 필요 2개"


def test_settings_viewmodel_exposes_all_setting_ids_for_status_check() -> None:
    view_model = SettingsViewModel(FakeCheckSettingsStatus(), FakeApplySettings())

    setting_ids = view_model.all_setting_ids()

    assert "hide_frequent_folders" in setting_ids
    assert len(setting_ids) == len(view_model.definitions)


def test_settings_viewmodel_rejects_apply_without_selection() -> None:
    apply_settings = FakeApplySettings()
    view_model = SettingsViewModel(FakeCheckSettingsStatus(), apply_settings)

    view_model.apply_selected([])

    assert view_model.status_message == "적용할 설정을 선택하세요."
    assert view_model.result_rows == []
    assert apply_settings.requests == []


def test_viewmodels_skip_work_when_busy() -> None:
    check_status = FakeCheckSettingsStatus()
    apply_settings = FakeApplySettings()
    settings_view_model = SettingsViewModel(check_status, apply_settings)
    settings_view_model.is_busy = True

    settings_view_model.check_status(["hide_frequent_folders"])
    settings_view_model.apply_selected(["hide_frequent_folders"])

    assert settings_view_model.status_message == "다른 작업이 진행 중입니다."
    assert check_status.requests == []
    assert apply_settings.requests == []


def test_network_viewmodel_calls_use_cases() -> None:
    view_model = NetworkViewModel(FakeListAdapters(), FakeApplyStaticIp(), FakeSetDhcp())

    view_model.load_adapters()
    assert view_model.adapters[0].name == "Ethernet"

    view_model.apply_static_ip("Ethernet", "192.168.0.10", "255.255.255.0", "192.168.0.1", "", "")
    assert view_model.status_message == "applied"

    view_model.set_dhcp("Ethernet")
    assert view_model.status_message == "dhcp"


def test_network_viewmodel_provides_legacy_default_ip_fields() -> None:
    view_model = NetworkViewModel(FakeListAdapters(), FakeApplyStaticIp(), FakeSetDhcp())

    assert view_model.default_static_ip_fields() == {
        "ip_address": "192.168.",
        "subnet_mask": "255.255.255.0",
        "gateway": "192.168.",
        "dns1": "203.246.75.1",
        "dns2": "",
    }


def test_network_viewmodel_updates_gateway_from_ip_prefix() -> None:
    view_model = NetworkViewModel(FakeListAdapters(), FakeApplyStaticIp(), FakeSetDhcp())

    assert view_model.gateway_for_ip_address("10.20.30.40") == "10.20.30.1"
    assert view_model.gateway_for_ip_address("192.168.") == "192.168.1"
    assert view_model.gateway_for_ip_address("") is None
    assert view_model.gateway_for_ip_address("localhost") is None


def test_pc_info_viewmodel_translates_unknown_values() -> None:
    view_model = PcInfoViewModel(FakeUnknownPcInfo())

    view_model.refresh()

    assert ("Windows", "알 수 없음") in view_model.rows
    assert ("GPU", "알 수 없음") in view_model.rows
    assert ("TPM", "알 수 없음") in view_model.rows


def test_pc_info_viewmodel_formats_windows_detail() -> None:
    assert _format_windows_detail("26200", "8655", "64비트") == "26200.8655 (64비트)"
    assert _format_windows_detail("26200", None, "64비트") == "26200 (64비트)"
    assert _format_windows_detail("26200", "8655", "64-bit") == "26200.8655 (64비트)"
    assert _format_windows_detail(None, None, "64비트") == "64비트"
    assert _format_windows_detail(None, None, None) == "알 수 없음"


def test_pc_check_viewmodel_updates_rows() -> None:
    view_model = PcCheckViewModel(FakeRunPcChecks())

    assert view_model.summary_text == "점검 필요"

    view_model.run_checks()

    assert view_model.result_rows == [("점검", "정상", "설치됨")]
    assert view_model.summary_text == "모든 항목 정상"


def test_pc_check_viewmodel_summary_counts_warning_and_error_rows() -> None:
    view_model = PcCheckViewModel(FakeRunPcChecks())
    view_model.result_rows = [
        ("정상", "정상", "문제 없음"),
        ("주의", "주의", "확인 필요"),
        ("오류", "오류", "실패"),
        ("미확인", "알 수 없음", "조회 실패"),
    ]

    assert view_model.warning_count == 1
    assert view_model.error_count == 1
    assert view_model.unknown_count == 1
    assert view_model.summary_text == "오류 1개"


def test_pc_check_viewmodel_translates_common_messages() -> None:
    class FakeRunTranslatedChecks:
        def execute(self) -> list[CheckResult]:
            return [
                CheckResult(
                    check_id="office",
                    label="Office",
                    status=CheckStatus.WARNING,
                    message="Office 2021 or 2024 is not installed.",
                ),
                CheckResult(
                    check_id="power",
                    label="전원",
                    status=CheckStatus.UNKNOWN,
                    message="Power settings could not be read.",
                ),
            ]

    view_model = PcCheckViewModel(FakeRunTranslatedChecks())

    view_model.run_checks()

    assert view_model.result_rows == [
        ("Office", "주의", "Office 2021 또는 2024가 설치되어 있지 않음"),
        ("전원", "알 수 없음", "전원 설정을 읽을 수 없음"),
    ]


def test_activation_viewmodel_does_not_expose_product_key() -> None:
    windows = FakeActivation("windows_activation")
    office = FakeActivation("office_activation")
    view_model = ActivationViewModel(windows, office)

    view_model.prepare_windows_activation("windows_10")
    assert view_model.status_message == "prepared"
    assert windows.requests == ["windows_10"]

    view_model.prepare_office_activation("2021")
    assert view_model.status_message == "prepared"
    assert office.requests == ["2021"]


def test_activation_viewmodel_applies_recommended_office_version() -> None:
    view_model = ActivationViewModel(FakeActivation("windows_activation"), FakeActivation("office_activation"))

    view_model.apply_recommended_office_version("2021")

    assert view_model.recommended_office_version == "2021"
    assert view_model.selected_office_version == "2021"


def test_activation_viewmodel_translates_product_key_messages() -> None:
    class FakeKoreanActivation:
        def __init__(self, message: str, success: bool = True) -> None:
            self.message = message
            self.success = success

        def execute(self, version: str | None = None) -> ActivationResult:
            return ActivationResult(self.success, "activation", self.message, copied_to_clipboard=True)

    view_model = ActivationViewModel(
        FakeKoreanActivation("Windows product key copied and activation window launched."),
        FakeKoreanActivation("Office product key is not configured.", success=False),
    )

    view_model.prepare_windows_activation()
    assert view_model.status_message == "Windows 제품키를 클립보드에 복사하고 인증 창을 열었습니다."

    view_model.prepare_office_activation()
    assert view_model.status_message == "Office 인증 준비 실패: Office 제품키가 설정되어 있지 않습니다."
