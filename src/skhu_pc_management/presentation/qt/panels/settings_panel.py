from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsPanel(QWidget):
    def __init__(
        self,
        view_model: SettingsViewModel,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode
        self._checkboxes: dict[str, QCheckBox] = {}

        self.status_label = QLabel(view_model.status_message)
        self.check_button = QPushButton("상태 확인")
        self.apply_button = QPushButton("선택 항목 적용")
        self.select_all_button = QPushButton("전체 선택")
        self.clear_all_button = QPushButton("전체 해제")
        self.validate_taskbar_button = QPushButton("작업표시줄 리소스 확인")
        self.apply_taskbar_button = QPushButton("작업표시줄 설정 적용")
        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["설정", "상태", "세부 정보"])
        self.result_table.horizontalHeader().setStretchLastSection(True)

        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        for definition in self._view_model.definitions:
            checkbox = QCheckBox(definition.name)
            checkbox.setChecked(False)
            self._checkboxes[definition.setting_id] = checkbox
            options_layout.addWidget(checkbox)
        options_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(options_widget)

        buttons = QHBoxLayout()
        buttons.addWidget(self.select_all_button)
        buttons.addWidget(self.clear_all_button)
        buttons.addWidget(self.check_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.validate_taskbar_button)
        buttons.addWidget(self.apply_taskbar_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_table)

        self.check_button.clicked.connect(self._check_status)
        self.apply_button.clicked.connect(self._apply_selected)
        self.select_all_button.clicked.connect(self._select_all)
        self.clear_all_button.clicked.connect(self._clear_all)
        self.validate_taskbar_button.clicked.connect(self._validate_taskbar_resources)
        self.apply_taskbar_button.clicked.connect(self._apply_taskbar_layout)
        self._apply_test_mode()

    def _selected_ids(self) -> list[str]:
        return [
            setting_id for setting_id, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]

    def _check_status(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("기본 설정 상태를 확인하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.check_status(self._view_model.all_setting_ids())
            self._render()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _apply_selected(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        selected_ids = self._selected_ids()
        if not selected_ids:
            self._view_model.apply_selected([])
            self._render()
            return

        if QMessageBox.question(self, "기본 설정 적용", "선택한 설정을 적용하시겠습니까?") != QMessageBox.Yes:
            return

        if self._busy_coordinator and not self._busy_coordinator.try_begin("선택한 기본 설정을 적용하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.apply_selected(selected_ids)
            self._render()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)

    def _clear_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)

    def _validate_taskbar_resources(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("작업표시줄 리소스를 확인하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.validate_taskbar_resources()
            self._render()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _apply_taskbar_layout(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        if QMessageBox.question(
            self,
            "작업표시줄 설정 적용",
            "먼저 dry-run으로 적용 계획만 확인합니다. 실제 작업표시줄은 변경하지 않습니다. 계속하시겠습니까?",
        ) != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("작업표시줄 설정 적용 계획을 확인하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.apply_taskbar_layout(dry_run=True)
            self._render()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def render(self) -> None:
        self._render()

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.result_table.setRowCount(len(self._view_model.result_rows))
        for row_index, row in enumerate(self._view_model.result_rows):
            for column_index, value in enumerate(row):
                self.result_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _set_busy(self, is_busy: bool) -> None:
        self.select_all_button.setEnabled(not is_busy)
        self.clear_all_button.setEnabled(not is_busy)
        self.check_button.setEnabled(not is_busy)
        self.apply_button.setEnabled(not is_busy and not self._test_mode)
        self.validate_taskbar_button.setEnabled(not is_busy)
        self.apply_taskbar_button.setEnabled(not is_busy and not self._test_mode)

    def _apply_test_mode(self) -> None:
        if not self._test_mode:
            return
        for button in (self.apply_button, self.apply_taskbar_button):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)
        self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
