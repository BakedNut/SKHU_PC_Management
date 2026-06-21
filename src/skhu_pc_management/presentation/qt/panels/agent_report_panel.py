from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.agent_report_viewmodel import AgentReportViewModel
from skhu_pc_management.presentation.qt.widgets.buttons import primary_button
from skhu_pc_management.presentation.qt.widgets.surfaces import Card


class AgentReportPanel(QWidget):
    def __init__(
        self,
        view_model: AgentReportViewModel,
        busy_coordinator: BusyCoordinator | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator

        self.status_label = QLabel(view_model.status_message)
        self.status_label.setObjectName("mutedText")

        self.result_label = QLabel(view_model.last_result_message)
        self.result_label.setObjectName("mutedText")
        self.result_label.setWordWrap(True)

        self.send_button = primary_button("서버로 PC 보고 전송")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        card = Card(
            "Agent 서버 전송",
            "현재 PC 정보를 수집해 SKHU-Lab-Ops Backend로 전송합니다.",
        )
        card.body_layout.addWidget(self.send_button)
        card.body_layout.addWidget(self.status_label)
        card.body_layout.addWidget(self.result_label)

        root.addWidget(card)
        root.addStretch()

        self.send_button.clicked.connect(self._send_report)

    def _send_report(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("서버로 PC 보고를 전송하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return

        self.set_busy(True)

        try:
            self._view_model.send_report()
            self.render()

            if self._view_model.status_message == "서버 전송이 완료되었습니다.":
                QMessageBox.information(self, "전송 완료", self._view_model.last_result_message)
        finally:
            self.set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.result_label.setText(self._view_model.last_result_message)

    def set_busy(self, is_busy: bool) -> None:
        self.send_button.setEnabled(not is_busy)