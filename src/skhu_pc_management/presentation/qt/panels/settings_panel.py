from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsPanel(QWidget):
    def __init__(self, view_model: SettingsViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self._checkboxes: dict[str, QCheckBox] = {}

        self.status_label = QLabel(view_model.status_message)
        self.check_button = QPushButton("상태 확인")
        self.apply_button = QPushButton("선택 항목 적용")
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
        buttons.addWidget(self.check_button)
        buttons.addWidget(self.apply_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_table)

        self.check_button.clicked.connect(self._check_status)
        self.apply_button.clicked.connect(self._apply_selected)

    def _selected_ids(self) -> list[str]:
        return [
            setting_id for setting_id, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]

    def _check_status(self) -> None:
        self._set_busy(True)
        try:
            self._view_model.check_status(self._selected_ids())
            self._render()
        finally:
            self._set_busy(False)

    def _apply_selected(self) -> None:
        self._set_busy(True)
        try:
            self._view_model.apply_selected(self._selected_ids())
            self._render()
        finally:
            self._set_busy(False)

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.result_table.setRowCount(len(self._view_model.result_rows))
        for row_index, row in enumerate(self._view_model.result_rows):
            for column_index, value in enumerate(row):
                self.result_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _set_busy(self, is_busy: bool) -> None:
        self.check_button.setEnabled(not is_busy)
        self.apply_button.setEnabled(not is_busy)
