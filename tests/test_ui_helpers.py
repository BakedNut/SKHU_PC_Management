from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from skhu_pc_management.presentation.qt.widgets.badges import StatusBadge, badge_tone_from_status
from skhu_pc_management.presentation.qt.widgets.buttons import primary_button, warning_button
from skhu_pc_management.presentation.qt.widgets.forms import FieldRow, FormGrid, ReadOnlyField, StatusValueField, read_only_field
from skhu_pc_management.presentation.qt.widgets.surfaces import SummaryCard
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, set_column_widths
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


def test_summary_card_tone_property_updates(qt_app: QApplication) -> None:
    card = SummaryCard("설정 상태", "정상")

    card.set_tone("success")
    assert card.property("tone") == "success"

    card.set_value("확인 필요", "전원: 확인 필요", "danger")
    assert card.value_label.text() == "확인 필요"
    assert card.subtitle_label is not None
    assert card.subtitle_label.text() == "전원: 확인 필요"
    assert card.property("tone") == "danger"


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
    assert panel.settings_table.item(0, 2).text() == "적용됨 / 적용 완료"
    assert panel.power_status_label.text() == "정상"
    assert panel.shutdown_status_label.text() == "정상"


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
    installed_office_status_text = "권장 Office 버전이 설치됨"
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
