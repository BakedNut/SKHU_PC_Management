from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel


class PcCheckPanel(QWidget):
    def __init__(self, view_model: PcCheckViewModel, busy_coordinator: BusyCoordinator | None = None) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator

        self.run_button = QPushButton("점검 실행")
        self.status_label = QLabel(view_model.status_message)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["항목", "상태", "메시지"])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

        self.run_button.clicked.connect(self._run_checks)

    def _run_checks(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("PC 점검을 실행하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self.run_button.setEnabled(False)
        try:
            self._view_model.run_checks()
            self._render()
        finally:
            self.run_button.setEnabled(True)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def render(self) -> None:
        self._render()

    def set_busy(self, is_busy: bool) -> None:
        self.run_button.setEnabled(not is_busy)

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.table.setRowCount(len(self._view_model.result_rows))
        for row_index, row in enumerate(self._view_model.result_rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(value)
                self.table.setItem(row_index, column_index, item)
