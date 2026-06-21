from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
from skhu_pc_management.presentation.qt.maintenance_confirmations import maintenance_confirmation_for
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel
from skhu_pc_management.presentation.qt.widgets.badges import StatusBadge
from skhu_pc_management.presentation.qt.widgets.buttons import (
    info_button,
    primary_button,
    repolish,
    set_button_role,
    subtle_button,
)
from skhu_pc_management.presentation.qt.widgets.surfaces import Card, SectionCard, SummaryCard
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, set_column_widths, status_item, table_item


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
        self._win11_setting_rows: list[QWidget] = []
        self._win11_badges: list[QLabel] = []
        self._danger_buttons: list[QPushButton] = []
        self._launch_buttons: list[QPushButton] = []

        self.refresh_status_button = primary_button("상태 새로고침")
        self.settings_summary = SummaryCard("설정 상태", "상태 확인 필요")
        self.pc_check_summary = SummaryCard("PC 점검", "점검 필요")
        self.classroom_summary = SummaryCard("강의실 정책", "미확인")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("scrollContent")
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
        row.addWidget(self.settings_summary, 1)
        row.addWidget(self.pc_check_summary, 1)
        row.addWidget(self.classroom_summary, 1)
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
        card = Card("인증", "제품키는 화면에 표시하지 않으며, 버튼 실행 시에만 복사됩니다.")
        self.win11_radio = QRadioButton("Windows 11")
        self.win10_radio = QRadioButton("Windows 10")
        self.win11_radio.setChecked(self._activation.selected_windows_version != "windows_10")
        self.win10_radio.setChecked(self._activation.selected_windows_version == "windows_10")
        self.windows_group = QButtonGroup(self)
        self.windows_group.addButton(self.win11_radio)
        self.windows_group.addButton(self.win10_radio)
        self.detected_windows_label = QLabel("현재 감지: 알 수 없음")
        self.detected_windows_label.setObjectName("mutedText")
        self.windows_activation_button = primary_button("복사 및 인증 창 열기")
        self.windows_activation_button.setObjectName("activationActionButton")
        self.windows_activation_button.setFixedWidth(220)

        windows_options = _option_column(
            self._radio_row(self.win11_radio, self.win10_radio),
            self.detected_windows_label,
        )
        card.body_layout.addWidget(
            self._action_row(
                "Windows 인증",
                "",
                self.windows_activation_button,
                option_widget=windows_options,
            )
        )

        self.office2021_radio = QRadioButton("Office 2021")
        self.office2024_radio = QRadioButton("Office 2024")
        self.office2024_radio.setChecked(self._activation.selected_office_version != "2021")
        self.office2021_radio.setChecked(self._activation.selected_office_version == "2021")
        self.office_group = QButtonGroup(self)
        self.office_group.addButton(self.office2021_radio)
        self.office_group.addButton(self.office2024_radio)
        self.office_activation_button = primary_button("복사 및 Excel 실행")
        self.office_activation_button.setObjectName("activationActionButton")
        self.office_status_label = QLabel("현재 감지: 미확인")
        self.office_status_label.setObjectName("mutedText")
        self.office_activation_button.setFixedWidth(220)
        office_options = _option_column(
            self._radio_row(self.office2021_radio, self.office2024_radio),
            self.office_status_label,
        )
        card.body_layout.addWidget(
            self._action_row(
                "Office 인증",
                "",
                self.office_activation_button,
                option_widget=office_options,
            )
        )

        self.activation_status = QLabel(self._activation.status_message)
        self.activation_status.setObjectName("mutedText")
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
        self.selected_count_label = QLabel("선택 0개")
        self.selected_count_label.setObjectName("mutedText")
        button_row.addWidget(self.select_all_button)
        button_row.addWidget(self.deselect_all_button)
        button_row.addWidget(self.selected_count_label)
        button_row.addStretch()
        button_row.addWidget(self.apply_settings_button)
        card.body_layout.addLayout(button_row)

        for title, options in SETTING_SECTIONS:
            section = SectionCard(title)
            is_start_menu_section = title == "시작 메뉴"
            if is_start_menu_section:
                self.start_menu_section = section
                self.start_menu_section.setObjectName("settingsSection")
                self.start_menu_section.setProperty("state", "active")
                self.start_menu_unavailable_label = QLabel("Windows 11 선택 시 사용할 수 있습니다.")
                self.start_menu_unavailable_label.setObjectName("sectionDisabledHint")
                self.start_menu_unavailable_label.setWordWrap(True)
                self.start_menu_unavailable_label.setVisible(False)
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
                    checkbox.toggled.connect(self._update_selected_count)
                if option.win11_only:
                    self._win11_only_checkboxes.append(checkbox)
                    badge = QLabel("Win11 전용")
                    badge.setObjectName("settingBadge")
                    badge.setProperty("tone", "info")
                    self._win11_badges.append(badge)
                    row.addWidget(checkbox)
                    row.addWidget(badge)
                else:
                    row.addWidget(checkbox)
                row.addStretch()
                container = QWidget()
                container.setLayout(row)
                if option.win11_only:
                    self._win11_setting_rows.append(container)
                grid.addWidget(container, index // 2, index % 2)
            section.body_layout.addLayout(grid)
            if is_start_menu_section:
                section.body_layout.addWidget(self.start_menu_unavailable_label)
            card.body_layout.addWidget(section)

        self.select_all_button.clicked.connect(self._select_all)
        self.deselect_all_button.clicked.connect(self._deselect_all)
        self.apply_settings_button.clicked.connect(self._apply_settings)
        self._update_selected_count()
        return card

    def _quick_tools_card(self) -> QWidget:
        card = Card("즉시 실행 도구")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        actions = (
            ("휴지통 비우기", "정리 작업", lambda: self._run_maintenance("empty_recycle_bin"), "info"),
            ("Chrome 사용자 데이터 초기화", "User Data 전체 삭제", lambda: self._run_maintenance("delete_chrome_history"), "danger"),
            ("Edge 사용자 데이터 초기화", "User Data 전체 삭제", lambda: self._run_maintenance("delete_edge_history"), "danger"),
            ("Chrome 실행", "브라우저 실행", lambda: self._launch_program("chrome"), "info"),
            ("Edge 실행", "브라우저 실행", lambda: self._launch_program("edge"), "info"),
            ("팟플레이어 실행", "동영상 플레이어", lambda: self._launch_program("potplayer"), "info"),
            ("반디집 실행", "압축 프로그램", lambda: self._launch_program("bandizip"), "info"),
        )
        for index, (label, description, callback, role) in enumerate(actions):
            button = QPushButton(label)
            set_button_role(button, role)
            button.setToolTip(description)
            button.clicked.connect(callback)
            if role == "danger":
                button.setToolTip("User Data 전체 폴더를 삭제합니다. 로그인 세션, 확장 프로그램 설정 등이 삭제될 수 있습니다.")
                self._danger_buttons.append(button)
            elif label.endswith("실행"):
                self._launch_buttons.append(button)
            grid.addWidget(button, index // 3, index % 3)
        card.body_layout.addLayout(grid)
        return card

    def _settings_status_card(self) -> QWidget:
        card = Card("시스템 설정 적용 상태")
        self.settings_table = QTableWidget(0, 3)
        self.settings_table.setHorizontalHeaderLabels(["설정 항목", "현재 상태", "상세"])
        configure_table(self.settings_table, compact=True)
        set_column_widths(self.settings_table, (220, 110))
        self.settings_table.setMinimumHeight(260)
        card.body_layout.addWidget(self.settings_table)
        return card

    def _pc_check_card(self) -> QWidget:
        card = Card("PC 점검 결과")
        self.pc_check_table = QTableWidget(0, 3)
        self.pc_check_table.setHorizontalHeaderLabels(["항목", "상태", "상세 내용"])
        configure_table(self.pc_check_table, compact=True)
        set_column_widths(self.pc_check_table, (170, 82))
        self.pc_check_table.setMinimumHeight(320)
        card.body_layout.addWidget(self.pc_check_table)
        return card

    def _classroom_checks_card(self) -> QWidget:
        card = Card("강의실 PC 전용 작업")
        self.power_status_label = StatusBadge("미확인", "neutral")
        self.shutdown_status_label = StatusBadge("미확인", "neutral")
        self.power_apply_button = primary_button("전원 옵션 '안 함' 적용")
        self.shutdown_apply_button = primary_button("23시 자동종료 적용")
        self.power_apply_button.setFixedWidth(220)
        self.shutdown_apply_button.setFixedWidth(220)
        self.power_description_label = QLabel("강의실 전원 정책 상태를 확인하고 필요 시 적용합니다.")
        self.power_description_label.setObjectName("mutedText")
        self.power_description_label.setWordWrap(True)
        self.power_detail_label = QLabel("전원 옵션 상태 확인 필요")
        self.power_detail_label.setObjectName("policyDetail")
        self.power_detail_label.setWordWrap(True)
        self.shutdown_description_label = QLabel("매일 22:55에 종료 예약 작업을 등록합니다.")
        self.shutdown_description_label.setObjectName("mutedText")
        self.shutdown_description_label.setWordWrap(True)
        self.shutdown_detail_label = QLabel("자동종료 스케줄 상태 확인 필요")
        self.shutdown_detail_label.setObjectName("policyDetail")
        self.shutdown_detail_label.setWordWrap(True)
        card.body_layout.addWidget(
            self._classroom_policy_row(
                "전원 옵션",
                self.power_description_label,
                self.power_detail_label,
                self.power_status_label,
                self.power_apply_button,
            )
        )
        card.body_layout.addWidget(
            self._classroom_policy_row(
                "23시 자동종료",
                self.shutdown_description_label,
                self.shutdown_detail_label,
                self.shutdown_status_label,
                self.shutdown_apply_button,
            )
        )
        self.power_apply_button.clicked.connect(lambda: self._run_maintenance("set_power_never"))
        self.shutdown_apply_button.clicked.connect(lambda: self._run_maintenance("set_auto_shutdown_at_23"))
        return card

    def _classroom_policy_row(
        self,
        title: str,
        description_label: QLabel,
        detail_label: QLabel,
        status_label: StatusBadge,
        action_button: QPushButton,
    ) -> QWidget:
        status_label.setObjectName("statusBadge")
        status_label.setFixedWidth(78)
        status_label.setAlignment(Qt.AlignCenter)

        text_container = QWidget()
        text_container.setObjectName("transparentContainer")
        text_container.setMinimumWidth(260)
        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("actionTitle")
        text_column.addWidget(title_label)
        text_column.addWidget(description_label)
        text_column.addWidget(detail_label)
        text_container.setLayout(text_column)
        return _PolicyActionRow(status_label, text_container, action_button)

    def _action_row(
        self,
        title: str,
        description: str,
        action_button: QPushButton,
        *,
        option_widget: QWidget | None = None,
        status_widget: QWidget | None = None,
        tooltip: str | None = None,
    ) -> QWidget:
        frame = QFrame()
        frame.setObjectName("actionRow")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        text_column = QVBoxLayout()
        text_column.setSpacing(5)
        name = QLabel(title)
        name.setObjectName("actionTitle")
        text_column.addWidget(name)
        if description:
            desc = QLabel(description)
            desc.setObjectName("actionDescription")
            desc.setWordWrap(True)
            if tooltip:
                frame.setToolTip(tooltip)
                desc.setToolTip(tooltip)
            text_column.addWidget(desc)
        if option_widget is not None:
            text_column.addWidget(option_widget)
        layout.addLayout(text_column, 1)
        if status_widget is not None:
            layout.addWidget(status_widget)
        layout.addWidget(action_button)
        return frame

    def _radio_row(self, *buttons: QRadioButton) -> QWidget:
        container = QWidget()
        container.setObjectName("transparentContainer")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        for button in buttons:
            row.addWidget(button)
        row.addStretch()
        return container

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
            apply_status = row[1] if len(row) > 1 else ""
            current_status = row[2] if len(row) > 2 else ""
            detail = row[3] if len(row) > 3 else ""
            self.settings_table.setItem(row_index, 0, table_item(name))
            self.settings_table.setItem(row_index, 1, status_item(current_status))
            detail_item = table_item(detail)
            detail_item.setToolTip(detail)
            self.settings_table.setItem(row_index, 2, detail_item)

    def _render_pc_check_rows(self) -> None:
        rows = self._pc_check.result_rows
        self.pc_check_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = status_item(value) if column_index == 1 else table_item(value)
                item.setToolTip(value)
                self.pc_check_table.setItem(row_index, column_index, item)

    def set_detected_windows_text(self, value: str) -> None:
        self.detected_windows_label.setText(f"현재 감지: {value or '알 수 없음'}")

    def _selected_setting_ids(self) -> list[str]:
        return [setting_id for setting_id, checkbox in self._checkboxes.items() if checkbox.isChecked()]

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)
        self._update_selected_count()

    def _deselect_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)
        self._update_selected_count()

    def _update_selected_count(self) -> None:
        if hasattr(self, "selected_count_label"):
            self.selected_count_label.setText(f"선택 {len(self._selected_setting_ids())}개")

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
        if hasattr(self, "start_menu_section"):
            self.start_menu_section.setProperty("state", "active" if is_win11 else "disabled")
            repolish(self.start_menu_section)
            self.start_menu_section.update()
        if hasattr(self, "start_menu_unavailable_label"):
            self.start_menu_unavailable_label.setVisible(not is_win11)
        for checkbox in self._win11_only_checkboxes:
            checkbox.setEnabled(is_win11 and not self._test_mode)
            checkbox.setToolTip("" if is_win11 else "Windows 11 전용 설정입니다.")
            if not is_win11:
                checkbox.setChecked(False)
        for row in self._win11_setting_rows:
            row.setVisible(is_win11)

    def _sync_status_summaries(self) -> None:
        self.settings_summary.set_value(self._settings.summary_text, tone=_settings_summary_tone(self._settings))
        self.pc_check_summary.set_value(self._pc_check.summary_text, tone=_pc_check_summary_tone(self._pc_check))
        office_text = _office_detected_text(self._pc_check.installed_office_status_text)
        classroom_value, classroom_subtitle, classroom_tone = _classroom_summary_value(
            self._pc_check.power_option_status_text,
            self._pc_check.auto_shutdown_status_text,
        )
        self.classroom_summary.set_value(classroom_value, classroom_subtitle, classroom_tone)
        self.classroom_summary.setToolTip(
            f"전원: {self._pc_check.power_option_status_text}\n자동 종료: {self._pc_check.auto_shutdown_status_text}"
        )
        _, power_detail = _short_power_status(self._pc_check.power_option_status_text)
        _, shutdown_detail = _short_shutdown_status(self._pc_check.auto_shutdown_status_text)
        power_badge_text, power_tone = _policy_status_tone(self._pc_check.power_option_status_text)
        shutdown_badge_text, shutdown_tone = _policy_status_tone(self._pc_check.auto_shutdown_status_text)
        self.power_status_label.set_status(power_badge_text, power_tone)
        self.power_status_label.setToolTip(self._pc_check.power_option_status_text)
        self.shutdown_status_label.set_status(shutdown_badge_text, shutdown_tone)
        self.shutdown_status_label.setToolTip(self._pc_check.auto_shutdown_status_text)
        _set_policy_detail(self.power_detail_label, power_detail, power_tone)
        self.power_detail_label.setToolTip(self._pc_check.power_option_status_text)
        _set_policy_detail(self.shutdown_detail_label, shutdown_detail, shutdown_tone)
        self.shutdown_detail_label.setToolTip(self._pc_check.auto_shutdown_status_text)
        self.office_status_label.setText(office_text)

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
        if not self._confirm_maintenance_action(action):
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

    def _confirm_maintenance_action(self, action: str) -> bool:
        confirmation = maintenance_confirmation_for(action)
        return QMessageBox.question(self, confirmation.title, confirmation.message) == QMessageBox.Yes

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
            *self._launch_buttons,
        ):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)


class _PolicyActionRow(QFrame):
    _COMPACT_WIDTH = 620

    def __init__(self, status_badge: QLabel, text_widget: QWidget, action_button: QPushButton) -> None:
        super().__init__()
        self.setObjectName("policyActionRow")
        self._status_badge = status_badge
        self._text_widget = text_widget
        self._action_button = action_button
        self._compact = False
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(14, 12, 14, 12)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(8)
        self._apply_layout(compact=False)

    @property
    def is_compact(self) -> bool:
        return self._compact

    @classmethod
    def should_use_compact_layout(cls, width: int) -> bool:
        return width < cls._COMPACT_WIDTH

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        self._apply_layout(self.should_use_compact_layout(self.width()))
        super().resizeEvent(event)

    def _apply_layout(self, compact: bool) -> None:
        if compact == self._compact and self._grid.indexOf(self._status_badge) != -1:
            return
        self._compact = compact
        if compact:
            self._grid.addWidget(self._status_badge, 0, 0, Qt.AlignTop)
            self._grid.addWidget(self._text_widget, 0, 1)
            self._grid.addWidget(self._action_button, 1, 1, Qt.AlignRight)
            self._grid.setColumnStretch(0, 0)
            self._grid.setColumnStretch(1, 1)
            self._grid.setColumnStretch(2, 0)
        else:
            self._grid.addWidget(self._status_badge, 0, 0, Qt.AlignTop)
            self._grid.addWidget(self._text_widget, 0, 1)
            self._grid.addWidget(self._action_button, 0, 2, Qt.AlignVCenter)
            self._grid.setColumnStretch(0, 0)
            self._grid.setColumnStretch(1, 1)
            self._grid.setColumnStretch(2, 0)


def _option_column(*widgets: QWidget) -> QWidget:
    container = QWidget()
    container.setObjectName("transparentContainer")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for widget in widgets:
        layout.addWidget(widget)
    return container


def _settings_summary_tone(settings: SettingsViewModel) -> str:
    if not settings.result_rows:
        return "danger"
    return "danger" if settings.warning_count else "success"


def _pc_check_summary_tone(pc_check: PcCheckViewModel) -> str:
    if not pc_check.result_rows:
        return "danger"
    return "danger" if pc_check.error_count or pc_check.warning_count or pc_check.unknown_count else "success"


def _office_detected_text(text: str) -> str:
    if not text or text == "미확인":
        return "현재 감지: 미확인"
    if text.startswith("현재 감지:"):
        return text
    if _contains_any(text, ("설치되어 있지", "설치되지")):
        return "현재 감지: 없음"
    return f"현재 감지: {text}"


def _classroom_summary_value(power_text: str, shutdown_text: str) -> tuple[str, str, str]:
    power_status, _ = _short_power_status(power_text)
    shutdown_status, _ = _short_shutdown_status(shutdown_text)
    is_ok = power_status == "정상" and shutdown_status == "정상"
    value = "정상" if is_ok else "확인 필요"
    subtitle = f"전원: {power_status} · 자동 종료: {shutdown_status}"
    return value, subtitle, "success" if is_ok else "danger"


def _short_power_status(text: str) -> tuple[str, str]:
    status = _short_policy_status(text, normal_tokens=("올바르게", "모두 비활성화", "안 함", "정상"))
    if status == "정상":
        return status, "화면 끄기: 안 함 · 절전: 안 함 · 최대 절전: 안 함"
    if status == "확인 불가":
        return status, "전원 옵션 상태 확인 필요"
    return status, "전원 옵션 설정 확인 필요"


def _short_shutdown_status(text: str) -> tuple[str, str]:
    status = _short_policy_status(text, normal_tokens=("정상 등록", "등록되어 있습니다", "정상", "올바르게 예약"))
    if status == "정상":
        return status, "22:55 시작, 23:00 종료 예약"
    if status == "확인 불가":
        return status, "자동종료 스케줄 상태를 확인할 수 없습니다."
    return status, "자동종료 예약 작업 확인 필요"


def _policy_status_tone(text: str) -> tuple[str, str]:
    if _contains_any(text, ("오류", "실패")):
        return "오류", "danger"
    if _contains_any(
        text,
        (
            "확인 불가",
            "읽을 수 없음",
            "알 수 없음",
            "미확인",
            "확인할 수 없습니다",
            "확인할 수 없음",
            "조회 실패",
            "읽기 실패",
            "상태를 확인할 수",
        ),
    ):
        return "확인 필요", "warning"
    if _contains_any(text, ("미설정", "필요", "주의", "등록되어 있지", "올바르지", "활성화됨")):
        return "주의", "warning"
    if _contains_any(text, ("정상", "올바르게 설정", "설정되어 있습니다", "정상 등록", "안 함")):
        return "정상", "success"
    return "확인 필요", "warning"


def _set_policy_detail(label: QLabel, text: str, tone: str) -> None:
    label.setText(text)
    label.setProperty("tone", tone)
    repolish(label)
    label.update()


def _short_policy_status(text: str, normal_tokens: tuple[str, ...]) -> str:
    if _contains_any(
        text,
        (
            "확인 불가",
            "읽을 수 없음",
            "알 수 없음",
            "미확인",
            "확인할 수 없습니다",
            "확인할 수 없음",
            "조회 실패",
            "읽기 실패",
            "상태를 확인할 수",
        ),
    ):
        return "확인 불가"
    if _contains_any(text, ("주의", "오류", "실패", "등록되어 있지", "올바르지", "필요", "활성화됨")):
        return "확인 필요"
    if _contains_any(text, normal_tokens):
        return "정상"
    return "확인 필요"


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)
