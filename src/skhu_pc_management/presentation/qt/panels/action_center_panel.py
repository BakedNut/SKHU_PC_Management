from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel
from skhu_pc_management.presentation.qt.widgets.badges import StatusBadge, badge_tone_from_status
from skhu_pc_management.presentation.qt.widgets.buttons import (
    danger_button,
    primary_button,
    secondary_button,
    set_button_role,
    subtle_button,
)
from skhu_pc_management.presentation.qt.widgets.surfaces import Card, SectionCard, SummaryCard
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, status_item, table_item


@dataclass(frozen=True)
class SettingOption:
    label: str
    setting_id: str | None
    win11_only: bool = False


SETTING_SECTIONS: tuple[tuple[str, tuple[SettingOption, ...]], ...] = (
    (
        "기본 환경",
        (
            SettingOption("기본 배경화면 설정", "set_default_wallpaper"),
            SettingOption("바탕화면 '내 PC' 아이콘 표시", "show_this_pc_on_desktop"),
            SettingOption("바탕화면 '제어판' 아이콘 표시", "show_control_panel_on_desktop"),
            SettingOption("바탕화면 Edge 바로가기 삭제", "delete_edge_shortcut"),
            SettingOption("작업표시줄 아이콘 설정", "set_taskbar_icons"),
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
        launch_program_use_case: object | None = None,
        maintenance_use_case: object | None = None,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings_view_model
        self._pc_check = pc_check_view_model
        self._activation = activation_view_model
        self._launch_program_use_case = launch_program_use_case
        self._maintenance_use_case = maintenance_use_case
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode
        self._checkboxes: dict[str, QCheckBox] = {}
        self._win11_only_checkboxes: list[QCheckBox] = []
        self._danger_buttons: list[QPushButton] = []

        self.refresh_status_button = primary_button("상태 새로고침")
        self.windows_summary = SummaryCard("Windows 대상", "Win 11")
        self.office_summary = SummaryCard("Office 상태", "미확인")
        self.power_summary = SummaryCard("전원 옵션", "미확인")
        self.shutdown_summary = SummaryCard("자동 종료", "미확인")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addLayout(self._page_header())
        content_layout.addLayout(self._summary_row())
        content_layout.addLayout(self._body_layout())
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

        self.refresh_status_button.clicked.connect(self._refresh_status)
        self._sync_win11_only_state()
        self._apply_test_mode()
        self.render()

    def _page_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("작업 센터")
        title.setObjectName("pageTitle")
        subtitle = QLabel("인증, 기본 설정, 점검 및 유지보수 작업을 한 곳에서 실행합니다.")
        subtitle.setObjectName("pageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        row.addLayout(title_column)
        row.addStretch()
        row.addWidget(self.refresh_status_button)
        return row

    def _summary_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self.windows_summary)
        row.addWidget(self.office_summary)
        row.addWidget(self.power_summary)
        row.addWidget(self.shutdown_summary)
        return row

    def _body_layout(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(self._activation_card())
        left.addWidget(self._settings_card())
        left.addWidget(self._quick_tools_card())
        right = QVBoxLayout()
        right.setSpacing(14)
        right.addWidget(self._settings_status_card())
        right.addWidget(self._pc_check_card())
        right.addWidget(self._classroom_checks_card())
        right.addStretch()
        body.addLayout(left, 3)
        body.addLayout(right, 2)
        return body

    def _activation_card(self) -> QWidget:
        card = Card("인증", "제품키는 화면에 표시하지 않고 클립보드 복사와 실행 준비만 수행합니다.")
        target_row = QHBoxLayout()
        target_label = QLabel("대상 Windows 버전")
        target_label.setObjectName("fieldLabel")
        self.win11_radio = QRadioButton("Windows 11")
        self.win10_radio = QRadioButton("Windows 10")
        self.win11_radio.setChecked(self._activation.selected_windows_version != "windows_10")
        self.windows_group = QButtonGroup(self)
        self.windows_group.addButton(self.win11_radio)
        self.windows_group.addButton(self.win10_radio)
        self.detected_windows_label = QLabel("현재 감지: 알 수 없음")
        self.detected_windows_label.setObjectName("mutedText")
        target_row.addWidget(target_label)
        target_row.addWidget(self.win11_radio)
        target_row.addWidget(self.win10_radio)
        target_row.addStretch()
        target_row.addWidget(self.detected_windows_label)
        card.body_layout.addLayout(target_row)

        key_grid = QGridLayout()
        key_grid.setHorizontalSpacing(12)
        key_grid.setVerticalSpacing(10)
        key_grid.addWidget(_label("Windows 키"), 0, 0)
        self.windows_key = QLineEdit("제품키는 화면에 표시하지 않습니다.")
        self.windows_key.setReadOnly(True)
        self.windows_key.setEchoMode(QLineEdit.Password)
        key_grid.addWidget(self.windows_key, 1, 0)
        self.windows_activation_button = primary_button("복사 및 인증 창 열기")
        key_grid.addWidget(self.windows_activation_button, 1, 1)

        key_grid.addWidget(_label("Office 키"), 2, 0)
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
        key_grid.addLayout(office_row, 2, 1)
        self.office_key = QLineEdit("제품키는 화면에 표시하지 않습니다.")
        self.office_key.setReadOnly(True)
        self.office_key.setEchoMode(QLineEdit.Password)
        key_grid.addWidget(self.office_key, 3, 0)
        self.office_activation_button = primary_button("복사 및 Excel 실행")
        key_grid.addWidget(self.office_activation_button, 3, 1)
        card.body_layout.addLayout(key_grid)

        self.office_status_label = QLabel("설치된 Office 상태: 미확인")
        self.office_status_label.setObjectName("mutedText")
        self.activation_status = QLabel(self._activation.status_message)
        self.activation_status.setObjectName("mutedText")
        card.body_layout.addWidget(self.office_status_label)
        card.body_layout.addWidget(self.activation_status)

        self.windows_activation_button.clicked.connect(self._prepare_windows_activation)
        self.office_activation_button.clicked.connect(self._prepare_office_activation)
        self.win11_radio.toggled.connect(self._on_windows_version_changed)
        self.office2021_radio.toggled.connect(self._on_office_version_changed)
        return card

    def _settings_card(self) -> QWidget:
        card = Card("시스템 설정 선택")
        button_row = QHBoxLayout()
        self.select_all_button = subtle_button("모두 선택")
        self.deselect_all_button = subtle_button("모두 해제")
        self.apply_settings_button = primary_button("선택한 설정 적용")
        button_row.addWidget(self.select_all_button)
        button_row.addWidget(self.deselect_all_button)
        button_row.addStretch()
        button_row.addWidget(self.apply_settings_button)
        card.body_layout.addLayout(button_row)

        for title, options in SETTING_SECTIONS:
            section = SectionCard(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(8)
            for index, option in enumerate(options):
                row = QHBoxLayout()
                checkbox = QCheckBox(option.label)
                if option.setting_id is None:
                    checkbox.setEnabled(False)
                else:
                    self._checkboxes[option.setting_id] = checkbox
                if option.win11_only:
                    self._win11_only_checkboxes.append(checkbox)
                    badge = StatusBadge("Win11 전용", "info")
                    row.addWidget(checkbox)
                    row.addWidget(badge)
                else:
                    row.addWidget(checkbox)
                row.addStretch()
                container = QWidget()
                container.setLayout(row)
                grid.addWidget(container, index // 2, index % 2)
            section.body_layout.addLayout(grid)
            card.body_layout.addWidget(section)

        self.select_all_button.clicked.connect(self._select_all)
        self.deselect_all_button.clicked.connect(self._deselect_all)
        self.apply_settings_button.clicked.connect(self._apply_settings)
        return card

    def _quick_tools_card(self) -> QWidget:
        card = Card("즉시 실행 도구")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        actions = (
            ("휴지통 비우기", "정리 작업", lambda: self._run_maintenance("empty_recycle_bin"), "danger"),
            ("Chrome 실행", "브라우저 실행", lambda: self._launch_program("chrome"), "secondary"),
            ("Edge 실행", "브라우저 실행", lambda: self._launch_program("edge"), "secondary"),
            ("팟플레이어 실행", "동영상 플레이어", lambda: self._launch_program("potplayer"), "secondary"),
            ("반디집 실행", "압축 프로그램", lambda: self._launch_program("bandizip"), "secondary"),
            ("Chrome 기록 삭제", "사용자 데이터 삭제", lambda: self._run_maintenance("delete_chrome_history"), "danger"),
            ("Edge 기록 삭제", "사용자 데이터 삭제", lambda: self._run_maintenance("delete_edge_history"), "danger"),
        )
        for index, (label, description, callback, role) in enumerate(actions):
            button = QPushButton(f"{label}\n{description}")
            set_button_role(button, role)
            button.clicked.connect(callback)
            if role == "danger":
                self._danger_buttons.append(button)
            grid.addWidget(button, index // 3, index % 3)
        card.body_layout.addLayout(grid)
        return card

    def _settings_status_card(self) -> QWidget:
        card = Card("시스템 설정 적용 상태")
        self.settings_table = QTableWidget(0, 2)
        self.settings_table.setHorizontalHeaderLabels(["설정 항목", "상태"])
        configure_table(self.settings_table, compact=True)
        self.settings_table.setMinimumHeight(260)
        card.body_layout.addWidget(self.settings_table)
        return card

    def _pc_check_card(self) -> QWidget:
        card = Card("PC 점검 결과")
        self.pc_check_table = QTableWidget(0, 3)
        self.pc_check_table.setHorizontalHeaderLabels(["항목", "상태", "상세 내용"])
        configure_table(self.pc_check_table, compact=True)
        self.pc_check_table.setMinimumHeight(320)
        card.body_layout.addWidget(self.pc_check_table)
        return card

    def _classroom_checks_card(self) -> QWidget:
        card = Card("강의실 PC 전용 작업")
        self.power_status_label = StatusBadge("미확인", "neutral")
        self.shutdown_status_label = StatusBadge("미확인", "neutral")
        self.power_apply_button = secondary_button("전원 옵션 '안 함' 적용")
        self.shutdown_apply_button = secondary_button("23시 자동종료 적용")
        card.body_layout.addWidget(
            self._action_row("전원 옵션", "화면 끄기/절전/최대 절전을 안 함으로 설정합니다.", self.power_status_label, self.power_apply_button)
        )
        card.body_layout.addWidget(
            self._action_row("23시 자동종료", "22:55에 시작해 23:00에 종료되도록 예약 작업을 등록합니다.", self.shutdown_status_label, self.shutdown_apply_button)
        )
        self.power_apply_button.clicked.connect(lambda: self._run_maintenance("set_power_never"))
        self.shutdown_apply_button.clicked.connect(lambda: self._run_maintenance("set_auto_shutdown_at_23"))
        return card

    def _action_row(self, title: str, description: str, badge: StatusBadge, button: QPushButton) -> QWidget:
        frame = QFrame()
        frame.setObjectName("sectionCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        text_column = QVBoxLayout()
        name = QLabel(title)
        name.setObjectName("fieldLabel")
        desc = QLabel(description)
        desc.setObjectName("mutedText")
        desc.setWordWrap(True)
        text_column.addWidget(name)
        text_column.addWidget(desc)
        layout.addLayout(text_column, 1)
        layout.addWidget(badge)
        layout.addWidget(button)
        return frame

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
            self.settings_table.setItem(row_index, 0, table_item(name))
            self.settings_table.setItem(row_index, 1, status_item(status))

    def _render_pc_check_rows(self) -> None:
        rows = self._pc_check.result_rows
        self.pc_check_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = status_item(value) if column_index == 1 else table_item(value)
                self.pc_check_table.setItem(row_index, column_index, item)

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
        self._sync_status_summaries()

    def _on_office_version_changed(self) -> None:
        self._activation.selected_office_version = "2021" if self.office2021_radio.isChecked() else "2024"

    def _sync_win11_only_state(self) -> None:
        is_win11 = self.win11_radio.isChecked()
        for checkbox in self._win11_only_checkboxes:
            checkbox.setEnabled(is_win11 and not self._test_mode)
            checkbox.setToolTip("" if is_win11 else "Windows 11 전용 설정입니다.")
            if not is_win11:
                checkbox.setChecked(False)

    def _sync_status_summaries(self) -> None:
        windows_target = "Win 11" if self.win11_radio.isChecked() else "Win 10"
        self.windows_summary.set_value(windows_target, self.detected_windows_label.text())
        self.office_summary.set_value(self._pc_check.installed_office_status_text)
        self.power_summary.set_value(self._pc_check.power_option_status_text)
        self.shutdown_summary.set_value(self._pc_check.auto_shutdown_status_text)
        self.power_status_label.set_status(self._pc_check.power_option_status_text, badge_tone_from_status(self._pc_check.power_option_status_text))
        self.shutdown_status_label.set_status(self._pc_check.auto_shutdown_status_text, badge_tone_from_status(self._pc_check.auto_shutdown_status_text))
        self.office_status_label.setText(f"설치된 Office 상태: {self._pc_check.installed_office_status_text}")

    def _launch_program(self, program_id: str) -> None:
        if self._launch_program_use_case is None:
            QMessageBox.information(self, "미구성", "프로그램 실행 기능이 구성되지 않았습니다.")
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("프로그램을 실행하는 중..."):
            return
        try:
            result = self._launch_program_use_case.execute(program_id)
            self._show_result(result)
            self._refresh_after_action()
        finally:
            if self._busy_coordinator:
                self._busy_coordinator.end("작업이 완료되었습니다.")

    def _run_maintenance(self, action: str) -> None:
        if self._maintenance_use_case is None:
            QMessageBox.information(self, "미구성", "PC 유지보수 기능이 구성되지 않았습니다.")
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("PC 유지보수 작업을 실행하는 중..."):
            return
        try:
            if action == "empty_recycle_bin":
                result = self._maintenance_use_case.empty_recycle_bin()
            elif action == "delete_chrome_history":
                result = self._maintenance_use_case.delete_browser_history("chrome")
            elif action == "delete_edge_history":
                result = self._maintenance_use_case.delete_browser_history("edge")
            elif action == "set_power_never":
                result = self._maintenance_use_case.set_power_never()
            elif action == "set_auto_shutdown_at_23":
                result = self._maintenance_use_case.set_auto_shutdown_at_23()
            else:
                raise ValueError(f"Unsupported maintenance action: {action}")
            self._show_result(result)
            self._refresh_after_action()
        finally:
            if self._busy_coordinator:
                self._busy_coordinator.end("작업이 완료되었습니다.")

    def _refresh_after_action(self) -> None:
        self._settings.check_status(self._settings.all_setting_ids())
        self._pc_check.run_checks()
        self.render()

    def _show_result(self, result: object) -> None:
        message = getattr(result, "message", "")
        success = bool(getattr(result, "success", False))
        if success:
            QMessageBox.information(self, "완료", message)
        else:
            QMessageBox.warning(self, "실패", message)

    def _apply_test_mode(self) -> None:
        if not self._test_mode:
            return
        for button in (
            self.apply_settings_button,
            self.windows_activation_button,
            self.office_activation_button,
            self.power_apply_button,
            self.shutdown_apply_button,
            *self._danger_buttons,
        ):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label
