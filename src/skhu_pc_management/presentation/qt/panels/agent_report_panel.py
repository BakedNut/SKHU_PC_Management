from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.agent_report_viewmodel import AgentReportViewModel
from skhu_pc_management.presentation.qt.widgets.buttons import primary_button
from skhu_pc_management.presentation.qt.widgets.forms import FormGrid, ReadOnlyField
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
        self._view_model.refresh_worker_token_status()

        self.status_label = QLabel(view_model.status_message)
        self.status_label.setObjectName("mutedText")

        self.result_label = QLabel(view_model.last_result_message)
        self.result_label.setObjectName("mutedText")
        self.result_label.setWordWrap(True)

        self.last_sent_at = ReadOnlyField(view_model.last_sent_at)
        self.last_report_id = ReadOnlyField(view_model.last_report_id)
        self.last_match_status = ReadOnlyField(view_model.last_match_status)
        self.worker_token_status = ReadOnlyField(view_model.worker_token_status)
        self.retry_config = ReadOnlyField(
            f"{view_model.max_retry_count}회 / {view_model.retry_delay_seconds}초 간격"
        )

        self.send_button = primary_button("서버로 PC 보고 전송")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        status_card = Card(
            "Agent 서버 전송",
            "현재 PC 정보를 수집해 SKHU-Lab-Ops Backend로 전송합니다.",
        )
        status_card.body_layout.addWidget(self.send_button)
        status_card.body_layout.addWidget(self.status_label)
        status_card.body_layout.addWidget(self.result_label)

        detail_card = Card("전송 상태", "최근 서버 전송 결과와 Worker Token 감지 상태입니다.")
        detail_form = FormGrid(columns=2)
        detail_form.add_field("최근 전송 시각", self.last_sent_at)
        detail_form.add_field("최근 Report ID", self.last_report_id)
        detail_form.add_field("최근 매칭 상태", self.last_match_status)
        detail_form.add_field("Worker Token", self.worker_token_status)
        detail_form.add_field("재시도 설정", self.retry_config)
        detail_card.body_layout.addWidget(detail_form)

        root.addWidget(status_card)
        root.addWidget(detail_card)
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
        self._view_model.refresh_worker_token_status()
        self.status_label.setText(self._view_model.status_message)
        self.result_label.setText(self._view_model.last_result_message)
        self.last_sent_at.setText(self._view_model.last_sent_at)
        self.last_report_id.setText(self._view_model.last_report_id)
        self.last_match_status.setText(self._view_model.last_match_status)
        self.worker_token_status.setText(self._view_model.worker_token_status)
        self.retry_config.setText(
            f"{self._view_model.max_retry_count}회 / "
            f"{self._view_model.retry_delay_seconds}초 간격"
        )

    def set_busy(self, is_busy: bool) -> None:
        self.send_button.setEnabled(not is_busy)