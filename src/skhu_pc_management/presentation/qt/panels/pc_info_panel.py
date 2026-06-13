from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel


class PcInfoPanel(QWidget):
    def __init__(self, view_model: PcInfoViewModel) -> None:
        super().__init__()
        self._view_model = view_model

        self.refresh_button = QPushButton("새로고침")
        self.status_label = QLabel(view_model.status_message)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["항목", "값"])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

        self.refresh_button.clicked.connect(self._refresh)

    def _refresh(self) -> None:
        self.refresh_button.setEnabled(False)
        try:
            self._view_model.refresh()
            self._render()
        finally:
            self.refresh_button.setEnabled(True)

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.table.setRowCount(len(self._view_model.rows))
        for row_index, (label, value) in enumerate(self._view_model.rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(label))
            self.table.setItem(row_index, 1, QTableWidgetItem(value))
