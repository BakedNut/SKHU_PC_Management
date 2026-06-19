from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.panels.pc_info_panel import NOT_IMPLEMENTED_MESSAGE
from skhu_pc_management.presentation.qt.styles import make_card, set_button_role
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


@dataclass(frozen=True)
class SettingOption:
    label: str
    setting_id: str | None
    win11_only: bool = False


SETTING_SECTIONS: tuple[tuple[str, tuple[SettingOption, ...]], ...] = (
    (
        "기본 환경",
        (
            # TODO: Port default wallpaper behavior from C# SettingsApplyService.cs
            # and WindowsSystemService.cs.
            SettingOption("기본 배경화면 설정", None),
            SettingOption("바탕화면 '내 PC' 아이콘 표시", "show_this_pc_on_desktop"),
            SettingOption("바탕화면 '제어판' 아이콘 표시", "show_control_panel_on_desktop"),
            # TODO: Compare this policy-based Python mapping with C#
            # WindowsSystemService.DeleteEdgeShortcuts.
            SettingOption("바탕화면 Edge 바로가기 삭제", "disable_edge_desktop_shortcut_policy"),
            # TODO: Integrate checkbox-driven taskbar icon apply with C#
            # TaskbarIconService.cs and MainViewModel.Settings.cs.
            SettingOption("작업표시줄 아이콘 설정", None),
            SettingOption("부팅 시 암호 입력 생략 설정 활성화", "enable_passwordless_signin"),
            SettingOption("빠른 시작 켜기 비활성화", "disable_fast_startup"),
            SettingOption("사용자 계정 암호 만료 비활성화", "disable_password_expiration"),
        ),
    ),
    (
        "탐색기/작업 표시줄",
        (
            SettingOption("자주 사용하는 폴더 숨김", "hide_frequent_folders"),
            SettingOption("최근 사용한 항목 숨김", "hide_recent_files"),
            SettingOption("탐색기 실행 시 '내 PC'로", "explorer_launch_to_this_pc"),
            SettingOption("파일 선택 확인란 비활성화", "disable_item_checkboxes"),
            SettingOption("파일 확장자 표시", "show_file_extensions"),
            SettingOption("작업 보기 버튼 숨김", "hide_task_view_button"),
            SettingOption("검색 아이콘만 표시", "show_search_icon"),
        ),
    ),
    (
        "시작 메뉴",
        (
            SettingOption("시작 메뉴: 고정된 항목 더 보기", "win11_start_more_pins", win11_only=True),
            SettingOption("시작 메뉴: 최근 추가 앱 숨김", "win11_hide_recent_apps", win11_only=True),
            SettingOption("시작 메뉴: 자주 사용 앱 숨김", "win11_hide_frequent_apps", win11_only=True),
            SettingOption("시작 메뉴: 추천 파일 숨김", "win11_hide_recommended_files", win11_only=True),
            SettingOption("시작 메뉴: 팁/권장 사항 숨김", "win11_hide_iris_recommendations", win11_only=True),
            SettingOption("시작 메뉴: 계정 알림 숨김", "win11_hide_account_notifications", win11_only=True),
        ),
    ),
)


class ActionCenterPanel(QWidget):
    def __init__(
        self,
        settings_view_model: SettingsViewModel,
        pc_check_view_model: PcCheckViewModel,
        activation_view_model: ActivationViewModel,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings_view_model
        self._pc_check = pc_check_view_model
        self._activation = activation_view_model
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode
        self._checkboxes: dict[str, QCheckBox] = {}
        self._win11_only_checkboxes: list[QCheckBox] = []

        root = QGridLayout(self)
        root.setColumnStretch(0, 115)
        root.setColumnStretch(1, 100)
        root.setHorizontalSpacing(12)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_content = QWidget()
        self.left_layout = QVBoxLayout(left_content)
        self.left_layout.addWidget(self._windows_target_card())
        self.left_layout.addWidget(self._activation_card())
        self.left_layout.addWidget(self._settings_card())
        self.left_layout.addWidget(self._quick_tools_card())
        self.left_layout.addStretch()
        left_scroll.setWidget(left_content)

        right = QVBoxLayout()
        right.addWidget(QLabel("시스템 설정 적용 상태"))
        right.itemAt(0).widget().setObjectName("cardTitle")
        self.settings_table = QTableWidget(0, 2)
        self.settings_table.setHorizontalHeaderLabels(["설정 항목", "상태"])
        self.settings_table.horizontalHeader().setStretchLastSection(True)
        self.settings_table.setAlternatingRowColors(True)
        settings_card, settings_card_layout = make_card()
        settings_card_layout.addWidget(self.settings_table)
        right.addWidget(settings_card)

        pc_check_title = QLabel("PC 점검 결과")
        pc_check_title.setObjectName("cardTitle")
        right.addWidget(pc_check_title)
        self.pc_check_table = QTableWidget(0, 3)
        self.pc_check_table.setHorizontalHeaderLabels(["항목", "상태", "상세 내용"])
        self.pc_check_table.horizontalHeader().setStretchLastSection(True)
        self.pc_check_table.setAlternatingRowColors(True)
        pc_check_card, pc_check_card_layout = make_card()
        pc_check_card_layout.addWidget(self.pc_check_table)
        right.addWidget(pc_check_card)
        right.addWidget(self._classroom_checks_card())
        self.refresh_status_button = QPushButton("상태 새로고침")
        set_button_role(self.refresh_status_button, "primary")
        right.addWidget(self.refresh_status_button)
        right.addStretch()

        root.addWidget(left_scroll, 0, 0)
        root.addLayout(right, 0, 1)

        self.refresh_status_button.clicked.connect(self._refresh_status)
        self._sync_win11_only_state()
        self._apply_test_mode()
        self.render()

    def _windows_target_card(self) -> QWidget:
        card, layout = make_card("대상 Windows 버전", object_name="startPointCard")
        self.detected_windows_label = QLabel("현재 감지: 알 수 없음")
        layout.addWidget(self.detected_windows_label)
        row = QHBoxLayout()
        self.win11_radio = QRadioButton("Win 11")
        self.win10_radio = QRadioButton("Win 10")
        self.win11_radio.setChecked(self._activation.selected_windows_version != "windows_10")
        self.windows_group = QButtonGroup(self)
        self.windows_group.addButton(self.win11_radio)
        self.windows_group.addButton(self.win10_radio)
        row.addWidget(self.win11_radio)
        row.addWidget(self.win10_radio)
        row.addStretch()
        layout.addLayout(row)
        self.win11_radio.toggled.connect(self._on_windows_version_changed)
        return card

    def _activation_card(self) -> QWidget:
        card, layout = make_card("인증 작업")
        layout.addWidget(_label("Windows 키"))
        self.windows_key = QLineEdit("제품키는 화면에 표시하지 않습니다.")
        self.windows_key.setReadOnly(True)
        self.windows_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.windows_key)
        self.windows_activation_button = QPushButton("복사 및 인증 창 열기")
        set_button_role(self.windows_activation_button, "primary")
        layout.addWidget(self.windows_activation_button)

        layout.addWidget(_label("Office 키"))
        office_row = QHBoxLayout()
        self.office2021_radio = QRadioButton("Office 2021")
        self.office2024_radio = QRadioButton("Office 2024")
        self.office2024_radio.setChecked(self._activation.selected_office_version != "2021")
        self.office2021_radio.setChecked(self._activation.selected_office_version == "2021")
        self.office_group = QButtonGroup(self)
        self.office_group.addButton(self.office2021_radio)
        self.office_group.addButton(self.office2024_radio)
        office_row.addWidget(self.office2021_radio)
        office_row.addWidget(self.office2024_radio)
        office_row.addStretch()
        layout.addLayout(office_row)
        self.office_status_label = QLabel("설치된 Office 상태: 미확인")
        layout.addWidget(self.office_status_label)
        self.office_key = QLineEdit("제품키는 화면에 표시하지 않습니다.")
        self.office_key.setReadOnly(True)
        self.office_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.office_key)
        self.office_activation_button = QPushButton("복사 및 Excel 실행")
        set_button_role(self.office_activation_button, "primary")
        layout.addWidget(self.office_activation_button)
        self.activation_status = QLabel(self._activation.status_message)
        layout.addWidget(self.activation_status)

        self.windows_activation_button.clicked.connect(self._prepare_windows_activation)
        self.office_activation_button.clicked.connect(self._prepare_office_activation)
        self.office2021_radio.toggled.connect(self._on_office_version_changed)
        return card

    def _settings_card(self) -> QWidget:
        card, layout = make_card("시스템 설정 선택")
        button_row = QHBoxLayout()
        self.select_all_button = QPushButton("모두 선택")
        self.deselect_all_button = QPushButton("모두 해제")
        self.apply_settings_button = QPushButton("선택한 설정 적용")
        set_button_role(self.apply_settings_button, "primary")
        button_row.addWidget(self.select_all_button)
        button_row.addWidget(self.deselect_all_button)
        button_row.addWidget(self.apply_settings_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        for title, options in SETTING_SECTIONS:
            section_label = _label(title)
            section_label.setObjectName("sectionTitle")
            layout.addWidget(section_label)
            grid = QGridLayout()
            for index, option in enumerate(options):
                checkbox = QCheckBox(option.label)
                if option.setting_id is None:
                    checkbox.setToolTip("TODO: C# SettingsApplyService.cs / WindowsSystemService.cs 참고")
                    checkbox.setEnabled(False)
                else:
                    self._checkboxes[option.setting_id] = checkbox
                if option.win11_only:
                    self._win11_only_checkboxes.append(checkbox)
                grid.addWidget(checkbox, index // 2, index % 2)
            layout.addLayout(grid)

        self.select_all_button.clicked.connect(self._select_all)
        self.deselect_all_button.clicked.connect(self._deselect_all)
        self.apply_settings_button.clicked.connect(self._apply_settings)
        return card

    def _quick_tools_card(self) -> QWidget:
        card, layout = make_card("즉시 실행 도구")
        grid = QGridLayout()
        labels = (
            "휴지통 비우기",
            "Chrome 실행",
            "Edge 실행",
            "팟플레이어 실행",
            "반디집 실행",
            "Chrome 기록 삭제",
            "Edge 기록 삭제",
        )
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.clicked.connect(self._show_actions_todo)
            grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(grid)
        return card

    def _classroom_checks_card(self) -> QWidget:
        card, layout = make_card("강의실 PC 전용 추가 점검 항목")
        self.power_status_label = QLabel("전원 옵션 상태: 미확인")
        self.shutdown_status_label = QLabel("23시 자동종료 상태: 미확인")
        power_row = QHBoxLayout()
        self.power_apply_button = QPushButton("전원 옵션 '안 함' 적용")
        set_button_role(self.power_apply_button, "primary")
        power_row.addWidget(self.power_apply_button)
        power_row.addWidget(self.power_status_label)
        power_row.addStretch()
        shutdown_row = QHBoxLayout()
        self.shutdown_apply_button = QPushButton("23시 자동종료 적용")
        set_button_role(self.shutdown_apply_button, "primary")
        shutdown_row.addWidget(self.shutdown_apply_button)
        shutdown_row.addWidget(self.shutdown_status_label)
        shutdown_row.addStretch()
        layout.addLayout(power_row)
        layout.addLayout(shutdown_row)
        self.power_apply_button.clicked.connect(self._show_maintenance_todo)
        self.shutdown_apply_button.clicked.connect(self._show_maintenance_todo)
        return card

    def render(self) -> None:
        self._render_settings_rows()
        self._render_pc_check_rows()
        self.activation_status.setText(self._activation.status_message)
        self._sync_status_summaries()

    def _render_settings_rows(self) -> None:
        rows = self._settings.result_rows
        self.settings_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            name = row[0] if row else ""
            status = row[1] if len(row) > 1 else ""
            self.settings_table.setItem(row_index, 0, QTableWidgetItem(name))
            self.settings_table.setItem(row_index, 1, QTableWidgetItem(status))

    def _render_pc_check_rows(self) -> None:
        rows = self._pc_check.result_rows
        self.pc_check_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                self.pc_check_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def set_detected_windows_text(self, value: str) -> None:
        self.detected_windows_label.setText(f"현재 감지: {value or '알 수 없음'}")

    def _selected_setting_ids(self) -> list[str]:
        return [setting_id for setting_id, checkbox in self._checkboxes.items() if checkbox.isChecked()]

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)

    def _apply_settings(self) -> None:
        if self._test_mode:
            self._settings.status_message = TEST_MODE_DISABLED_MESSAGE
            self.render()
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("선택한 기본 설정을 적용하는 중..."):
            return
        try:
            self._settings.apply_selected(self._selected_setting_ids())
            self.render()
        finally:
            if self._busy_coordinator:
                self._busy_coordinator.end(self._settings.status_message)

    def _refresh_status(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("상태를 새로고침하는 중..."):
            return
        try:
            self._settings.check_status(self._settings.all_setting_ids())
            self._pc_check.run_checks()
            self.render()
        finally:
            if self._busy_coordinator:
                self._busy_coordinator.end("상태 새로고침이 완료되었습니다.")

    def _prepare_windows_activation(self) -> None:
        if self._test_mode:
            self._activation.status_message = TEST_MODE_DISABLED_MESSAGE
            self.render()
            return
        version = "windows_11" if self.win11_radio.isChecked() else "windows_10"
        self._activation.prepare_windows_activation(version)
        self.render()

    def _prepare_office_activation(self) -> None:
        if self._test_mode:
            self._activation.status_message = TEST_MODE_DISABLED_MESSAGE
            self.render()
            return
        version = "2021" if self.office2021_radio.isChecked() else "2024"
        self._activation.prepare_office_activation(version)
        self.render()

    def _on_windows_version_changed(self) -> None:
        self._activation.selected_windows_version = "windows_11" if self.win11_radio.isChecked() else "windows_10"
        self._sync_win11_only_state()

    def _on_office_version_changed(self) -> None:
        self._activation.selected_office_version = "2021" if self.office2021_radio.isChecked() else "2024"

    def _sync_win11_only_state(self) -> None:
        is_win11 = self.win11_radio.isChecked()
        for checkbox in self._win11_only_checkboxes:
            checkbox.setEnabled(is_win11 and not self._test_mode)
            if not is_win11:
                checkbox.setChecked(False)

    def _sync_status_summaries(self) -> None:
        for name, status, detail in self._pc_check.result_rows:
            text = detail or status
            if "전원" in name:
                self.power_status_label.setText(text)
            if "자동종료" in name or "자동 종료" in name:
                self.shutdown_status_label.setText(text)
            if "Office" in name:
                self.office_status_label.setText(f"설치된 Office 상태: {detail or status}")

    def _show_actions_todo(self) -> None:
        # TODO: Port C# ViewModels/PcActionsViewModel.cs, Services/PcProgramLaunchService.cs,
        # ViewModels/PcMaintenanceViewModel.cs, and Services/PcMaintenanceService.cs.
        QMessageBox.information(self, "미구현", NOT_IMPLEMENTED_MESSAGE)

    def _show_maintenance_todo(self) -> None:
        # TODO: Port C# Services/PcMaintenanceService.cs SetPowerNever/SetAutoShutdownAt23
        # and ViewModels/PcMaintenanceViewModel.cs.
        QMessageBox.information(self, "미구현", NOT_IMPLEMENTED_MESSAGE)

    def _apply_test_mode(self) -> None:
        if not self._test_mode:
            return
        for button in (
            self.apply_settings_button,
            self.windows_activation_button,
            self.office_activation_button,
            self.power_apply_button,
            self.shutdown_apply_button,
        ):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label
