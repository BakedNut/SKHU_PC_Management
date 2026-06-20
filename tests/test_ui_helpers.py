from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QTableWidget

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, NetworkConfigResult
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.widgets.badges import StatusBadge, badge_tone_from_status
from skhu_pc_management.presentation.qt.widgets.buttons import info_button, primary_button, warning_button
from skhu_pc_management.presentation.qt.widgets.forms import FieldRow, FormGrid, ReadOnlyField, StatusValueField, read_only_field
from skhu_pc_management.presentation.qt.widgets.surfaces import SummaryCard
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, set_column_widths
from skhu_pc_management.presentation.qt.styles import APP_QSS
from skhu_pc_management.presentation.qt.panels.network_panel import (
    NetworkPanel,
    _combo_with_arrow,
    _current_table_height,
    _display_network_status_message,
)
from skhu_pc_management.presentation.qt.panels.action_center_panel import (
    ActionCenterPanel,
    _classroom_summary_value,
    _short_power_status,
    _short_shutdown_status,
)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_form_display_widgets_have_stable_object_names(qt_app: QApplication) -> None:
    assert FormGrid().objectName() == "formGrid"
    assert FieldRow("항목", QLabel("값")).objectName() == "fieldRow"
    assert ReadOnlyField("값").objectName() == "readOnlyField"


def test_read_only_field_helper_returns_label_not_input(qt_app: QApplication) -> None:
    field = read_only_field("표시값")

    assert isinstance(field, ReadOnlyField)
    assert field.text() == "표시값"
    assert field.toolTip() == "표시값"

    field.setText("긴 표시값")
    assert field.toolTip() == "긴 표시값"


def test_status_value_field_updates_text_tooltip_and_tone(qt_app: QApplication) -> None:
    field = StatusValueField("알 수 없음")

    assert field.objectName() == "statusValueField"
    assert field.property("tone") == "neutral"

    field.set_status("정상")
    assert field.text() == "정상"
    assert field.toolTip() == "정상"
    assert field.property("tone") == "success"


def test_button_roles_are_set_for_qss(qt_app: QApplication) -> None:
    assert primary_button("실행").property("buttonRole") == "primary"
    assert info_button("조회").property("buttonRole") == "info"
    assert warning_button("주의").property("buttonRole") == "warning"


def test_badge_tone_mapping_and_property(qt_app: QApplication) -> None:
    badge = StatusBadge("정상")

    assert badge_tone_from_status("정상") == "success"
    assert badge_tone_from_status("설정됨") == "success"
    assert badge_tone_from_status("확인 불가") == "neutral"
    assert badge.property("tone") == "neutral"

    badge.set_status("주의")
    assert badge.property("tone") == "warning"


def test_table_column_helper_keeps_last_column_stretch(qt_app: QApplication) -> None:
    table = QTableWidget(0, 4)
    configure_table(table)
    set_column_widths(table, (120, 80, 80))

    assert table.columnWidth(0) == 120
    assert table.columnWidth(1) == 80


def test_compact_table_helper_sets_compact_property_and_row_height(qt_app: QApplication) -> None:
    table = QTableWidget(0, 2)
    configure_table(table, compact=True)

    assert table.property("compact") is True
    assert table.verticalHeader().defaultSectionSize() == 28


def test_summary_card_tone_property_updates(qt_app: QApplication) -> None:
    card = SummaryCard("설정 상태", "정상")

    card.set_tone("success")
    assert card.property("tone") == "success"

    card.set_value("확인 필요", "전원: 확인 필요", "danger")
    assert card.value_label.text() == "확인 필요"
    assert card.subtitle_label is not None
    assert card.subtitle_label.text() == "전원: 확인 필요"
    assert card.property("tone") == "danger"


def test_app_qss_contains_modern_scrollbar_and_combobox_styles() -> None:
    assert "QScrollBar::handle:vertical" in APP_QSS
    assert "QScrollBar::handle:horizontal" in APP_QSS
    assert "QComboBox::drop-down" in APP_QSS
    assert "QComboBox::down-arrow" in APP_QSS
    assert "image: none;" in APP_QSS
    assert "border: 0;" in APP_QSS
    assert "QComboBox QAbstractItemView" in APP_QSS
    assert "QFrame#comboShell" in APP_QSS
    assert "QLabel#comboArrow" in APP_QSS
    assert "QComboBox#comboInShell::down-arrow" in APP_QSS


def test_app_qss_contains_header_badge_pill_styles() -> None:
    assert "QLabel#headerBadge" in APP_QSS
    assert 'QLabel#headerBadge[tone="info"]' in APP_QSS
    assert 'QLabel#headerBadge[tone="neutral"]' in APP_QSS
    assert "border-radius: 10px;" in APP_QSS
    assert "padding: 8px 14px;" in APP_QSS


def test_app_qss_contains_info_button_role() -> None:
    assert 'QPushButton[buttonRole="info"]' in APP_QSS
    assert 'QPushButton[buttonRole="info"]:hover' in APP_QSS
    assert 'QPushButton[buttonRole="info"]:pressed' in APP_QSS
    assert "background: #EFF6FF;" in APP_QSS
    assert "border: 1px solid #93C5FD;" in APP_QSS
    assert "color: #1D4ED8;" in APP_QSS


def test_combo_with_arrow_wraps_combobox_with_visible_indicator(qt_app: QApplication) -> None:
    combo = QComboBox()

    wrapper = _combo_with_arrow(combo)

    assert wrapper.objectName() == "comboShell"
    assert combo.objectName() == "comboInShell"
    arrows = wrapper.findChildren(QLabel, "comboArrow")
    assert len(arrows) == 1
    assert arrows[0].text() == "▾"


def test_current_network_table_height_is_bounded() -> None:
    assert _current_table_height(0) == 180
    assert _current_table_height(1) == 180
    assert _current_table_height(7) == 238
    assert _current_table_height(20) == 250


def test_network_status_message_filters_successful_adapter_load_text() -> None:
    assert _display_network_status_message("어댑터 2개를 불러왔습니다.") == ""
    assert _display_network_status_message("네트워크 어댑터를 불러오는 중입니다...") == ""
    assert _display_network_status_message("어댑터 조회 실패: PowerShell failed") == "어댑터 조회 실패: PowerShell failed"
    assert _display_network_status_message("입력 오류: IP 주소 형식이 올바르지 않습니다.") == "입력 오류: IP 주소 형식이 올바르지 않습니다."


def test_network_panel_hides_successful_adapter_load_message_and_removes_duplicate_mode_row(qt_app: QApplication) -> None:
    view_model = NetworkViewModel(_FakeListNetworkAdapters(), _FakeApplyStaticIp(), _FakeSetDhcp(), reload_sleep=lambda _: None)
    panel = NetworkPanel(view_model)

    panel._load_adapters()

    assert not hasattr(panel, "adapter_summary")
    assert not hasattr(panel, "mode_summary")
    assert not hasattr(panel, "ip_summary")
    assert panel.adapter_combo is not None
    assert panel.ip_input is not None
    assert panel.apply_button is not None
    assert panel.dhcp_button is not None
    assert panel.status_label.isHidden() is True
    label_texts = [label.text() for label in panel.findChildren(QLabel)]
    assert "할당 방식" not in label_texts
    assert label_texts.count("IP 할당 방식") == 1
    assert panel.current_table.minimumHeight() == 238
    assert panel.current_table.maximumHeight() == 238
    table_rows = [
        (panel.current_table.item(row, 0).text(), panel.current_table.item(row, 1).text())
        for row in range(panel.current_table.rowCount())
    ]
    assert ("네트워크 어댑터", "이더넷") in table_rows
    assert ("IP 할당 방식", "수동 IP") in table_rows
    assert ("IP 주소", "192.168.0.10") in table_rows


def test_classroom_summary_formatter_shortens_status_text() -> None:
    value, subtitle, tone = _classroom_summary_value(
        "전원 옵션이 올바르게 설정되어 있습니다. 화면 끄기: 안 함, 절전: 안 함, 최대 절전: 안 함",
        "23시 자동종료 스케줄이 정상 등록되어 있습니다.",
    )

    assert value == "정상"
    assert subtitle == "전원: 정상 · 자동 종료: 정상"
    assert tone == "success"

    value, subtitle, tone = _classroom_summary_value(
        "전원 옵션이 올바르게 설정되어 있습니다. 화면 끄기: 안 함, 절전: 안 함, 최대 절전: 안 함",
        "자동종료 스케줄 상태를 확인할 수 없습니다.",
    )

    assert value == "확인 필요"
    assert subtitle == "전원: 정상 · 자동 종료: 확인 불가"
    assert tone == "danger"


def test_classroom_row_status_formatters_return_short_text() -> None:
    assert _short_power_status("전원 옵션이 올바르게 설정되어 있습니다. 화면 끄기: 안 함") == (
        "정상",
        "화면 끄기 / 절전 / 최대 절전: 안 함",
    )
    assert _short_power_status("전원 옵션 상태를 확인할 수 없습니다.") == (
        "확인 불가",
        "전원 옵션 상태 확인 필요",
    )
    assert _short_power_status("전원 옵션 확인이 필요합니다.") == (
        "확인 필요",
        "전원 옵션 설정 확인 필요",
    )
    assert _short_shutdown_status("23시 자동종료 스케줄이 정상 등록되어 있습니다.") == (
        "정상",
        "22:55 시작, 23:00 종료 예약",
    )
    assert _short_shutdown_status("자동종료 스케줄 상태를 확인할 수 없습니다.") == (
        "확인 불가",
        "자동종료 스케줄 상태 확인 필요",
    )
    assert _short_shutdown_status("23시 자동종료 스케줄이 등록되어 있지 않습니다.") == (
        "확인 필요",
        "자동종료 예약 작업 확인 필요",
    )


def test_action_center_settings_table_renders_three_columns(qt_app: QApplication) -> None:
    panel = ActionCenterPanel(_FakeSettings(), _FakePcCheck(), _FakeActivation())

    assert not hasattr(panel, "recommended_action_label")
    assert not hasattr(panel, "windows_key")
    assert not hasattr(panel, "office_key")
    assert not hasattr(panel, "windows_selection_label")
    assert panel.windows_activation_button.width() == 220
    assert panel.office_activation_button.width() == 220
    label_texts = [label.text() for label in panel.findChildren(QLabel)]
    for removed_text in (
        "대상 Windows 버전을 선택한 뒤 인증 창을 엽니다.",
        "대상 Office 버전을 선택한 뒤 Excel을 실행합니다.",
        "제품키는 화면에 표시하지 않습니다.",
        "복사 작업은 버튼을 누를 때만 수행됩니다.",
    ):
        assert removed_text not in label_texts
    assert panel.settings_table.columnCount() == 3
    assert panel.settings_table.horizontalHeaderItem(0).text() == "설정 항목"
    assert panel.settings_table.horizontalHeaderItem(1).text() == "현재 상태"
    assert panel.settings_table.horizontalHeaderItem(2).text() == "상세"
    assert panel.settings_table.item(0, 1).text() == "설정됨"
    assert panel.settings_table.item(0, 2).text() == "적용 완료"
    assert panel.power_status_label.text() == "정상"
    assert panel.shutdown_status_label.text() == "정상"
    assert panel.office_status_label.text() == "현재 감지: Office 2024"
    assert not hasattr(panel, "office_summary")
    summary_titles = [card.title_label.text() for card in panel.findChildren(SummaryCard)]
    assert summary_titles == ["설정 상태", "PC 점검", "강의실 정책"]


def test_action_center_test_mode_disables_program_launch_buttons(qt_app: QApplication) -> None:
    panel = ActionCenterPanel(_FakeSettings(), _FakePcCheck(), _FakeActivation(), test_mode=True)

    assert panel._launch_buttons
    assert all(not button.isEnabled() for button in panel._launch_buttons)
    assert all(button.toolTip() for button in panel._launch_buttons)
    assert all("\n" not in button.text() for button in panel._launch_buttons)


def test_action_center_quick_tool_button_order(qt_app: QApplication) -> None:
    panel = ActionCenterPanel(_FakeSettings(), _FakePcCheck(), _FakeActivation())

    quick_tool_labels = {
        "휴지통 비우기",
        "Chrome 사용자 데이터 초기화",
        "Edge 사용자 데이터 초기화",
        "Chrome 실행",
        "Edge 실행",
        "팟플레이어 실행",
        "반디집 실행",
    }
    button_texts = [button.text() for button in panel.findChildren(QPushButton) if button.text() in quick_tool_labels]

    assert button_texts == [
        "휴지통 비우기",
        "Chrome 사용자 데이터 초기화",
        "Edge 사용자 데이터 초기화",
        "Chrome 실행",
        "Edge 실행",
        "팟플레이어 실행",
        "반디집 실행",
    ]


def test_action_center_quick_tool_button_roles(qt_app: QApplication) -> None:
    panel = ActionCenterPanel(_FakeSettings(), _FakePcCheck(), _FakeActivation())

    buttons = {button.text(): button for button in panel.findChildren(QPushButton)}

    assert buttons["Chrome 사용자 데이터 초기화"].property("buttonRole") == "danger"
    assert buttons["Edge 사용자 데이터 초기화"].property("buttonRole") == "danger"
    for label in (
        "휴지통 비우기",
        "Chrome 실행",
        "Edge 실행",
        "팟플레이어 실행",
        "반디집 실행",
        "전원 옵션 '안 함' 적용",
        "23시 자동종료 적용",
    ):
        assert buttons[label].property("buttonRole") == "info"

    for label in (
        "선택한 설정 적용",
        "복사 및 인증 창 열기",
        "복사 및 Excel 실행",
    ):
        assert buttons[label].property("buttonRole") == "primary"


def test_action_center_office_status_uses_detected_prefix_and_keeps_buttons_enabled(qt_app: QApplication) -> None:
    pc_check = _FakePcCheck()
    pc_check.installed_office_status_text = "현재 감지: Office 365"
    panel = ActionCenterPanel(_FakeSettings(), pc_check, _FakeActivation())

    assert panel.office_status_label.text() == "현재 감지: Office 365"
    assert panel.office2021_radio.isEnabled()
    assert panel.office2024_radio.isEnabled()
    assert panel.office_activation_button.isEnabled()


def test_action_center_summary_treats_cannot_confirm_messages_as_unknown() -> None:
    assert _short_shutdown_status("자동종료 스케줄 상태를 확인할 수 없습니다.") == (
        "확인 불가",
        "자동종료 스케줄 상태 확인 필요",
    )
    assert _short_power_status("전원 옵션 상태를 확인할 수 없습니다.") == (
        "확인 불가",
        "전원 옵션 상태 확인 필요",
    )


def test_app_qss_does_not_keep_unused_tab_widget_styles() -> None:
    assert "QTabWidget::pane" not in APP_QSS
    assert "QTabBar::tab" not in APP_QSS


class _FakeSettings:
    result_rows = [("파일 확장자 표시", "적용됨", "설정됨", "적용 완료")]
    status_message = ""

    @property
    def warning_count(self) -> int:
        return 0

    @property
    def summary_text(self) -> str:
        return "모든 항목 정상"


class _FakePcCheck:
    result_rows = [("전원", "정상", "문제 없음")]
    installed_office_status_text = "현재 감지: Office 2024"
    power_option_status_text = "전원 옵션이 올바르게 설정되어 있습니다. 화면 끄기: 안 함, 절전: 안 함, 최대 절전: 안 함"
    auto_shutdown_status_text = "23시 자동종료 스케줄이 정상 등록되어 있습니다."

    @property
    def error_count(self) -> int:
        return 0

    @property
    def warning_count(self) -> int:
        return 0

    @property
    def unknown_count(self) -> int:
        return 0

    @property
    def summary_text(self) -> str:
        return "모든 항목 정상"


class _FakeActivation:
    selected_windows_version = "windows_11"
    selected_office_version = "2024"
    status_message = ""


class _FakeListNetworkAdapters:
    def execute(self) -> list[NetworkAdapterInfo]:
        return [
            NetworkAdapterInfo(
                name="이더넷",
                description="Realtek",
                is_enabled=True,
                ip_addresses=("192.168.0.10",),
                subnet_mask="255.255.255.0",
                gateway="192.168.0.1",
                dns_servers=("8.8.8.8",),
                is_dhcp_enabled=False,
            ),
            NetworkAdapterInfo(name="Wi-Fi", description="Wi-Fi", is_enabled=False, is_dhcp_enabled=True),
        ]


class _FakeApplyStaticIp:
    def execute(self, config: object) -> NetworkConfigResult:
        return NetworkConfigResult("apply_static_ip", True, "이더넷", "ok")


class _FakeSetDhcp:
    def execute(self, adapter_name: str) -> NetworkConfigResult:
        return NetworkConfigResult("set_dhcp", True, adapter_name, "ok")
