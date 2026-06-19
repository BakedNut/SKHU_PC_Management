from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.widgets.buttons import primary_button, secondary_button, set_button_role, warning_button
from skhu_pc_management.presentation.qt.widgets.forms import FormGrid, ReadOnlyField, StatusValueField
from skhu_pc_management.presentation.qt.widgets.surfaces import Card, SummaryCard
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, set_column_widths, table_item


NOT_IMPLEMENTED_MESSAGE = "아직 Python 마이그레이션에서 구현되지 않은 기능입니다."


class PcInfoPanel(QWidget):
    def __init__(
        self,
        view_model: PcInfoViewModel,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode

        self.status_label = QLabel(view_model.status_message)
        self.status_label.setObjectName("mutedText")
        self.refresh_button = primary_button("PC 정보 새로고침")
        self.rename_button = secondary_button("PC 이름 변경")
        self.auto_rename_button = warning_button("PC 이름 사용자 이름과 맞추기")

        self.summary_pc_name = SummaryCard("PC 이름", "알 수 없음")
        self.summary_windows = SummaryCard("Windows", "알 수 없음")
        self.summary_user = SummaryCard("사용자", "알 수 없음")

        self.pc_name = ReadOnlyField()
        self.user_name = ReadOnlyField()
        self.windows = ReadOnlyField()
        self.windows_detail = ReadOnlyField()
        self.cpu = ReadOnlyField()
        self.ram = ReadOnlyField()
        self.gpu = ReadOnlyField()
        self.tpm_version = StatusValueField("알 수 없음", "neutral")
        self.tpm_status = StatusValueField("알 수 없음", "neutral")
        self.secure_boot = StatusValueField("알 수 없음", "neutral")
        self.boot_mode = StatusValueField("알 수 없음", "neutral")

        self.disk_table = QTableWidget(0, 4)
        self.disk_table.setHorizontalHeaderLabels(["모델", "타입", "정격 용량", "실제 용량"])
        configure_table(self.disk_table)
        set_column_widths(self.disk_table, (260, 110, 100))
        self.disk_table.setMinimumHeight(180)
        self.disk_table.setMaximumHeight(240)

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

        self.refresh_button.clicked.connect(self._refresh)
        self.rename_button.clicked.connect(self._rename_pc)
        self.auto_rename_button.clicked.connect(self._auto_rename_pc)

    def _page_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("PC 정보")
        title.setObjectName("pageTitle")
        subtitle = QLabel("장치, Windows, 하드웨어 및 보안 호환성 정보를 확인합니다.")
        subtitle.setObjectName("pageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        row.addLayout(title_column)
        row.addStretch()
        row.addWidget(self.refresh_button)
        return row

    def _summary_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self.summary_pc_name)
        row.addWidget(self.summary_windows)
        row.addWidget(self.summary_user)
        return row

    def _body_layout(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(self._system_card())
        left.addWidget(self._hardware_card())
        left.addWidget(self._disk_card())
        right = QVBoxLayout()
        right.setSpacing(14)
        right.addWidget(self._pc_actions_card())
        right.addWidget(self._security_card())
        right.addStretch()
        body.addLayout(left, 3)
        body.addLayout(right, 2)
        return body

    def _system_card(self) -> QWidget:
        card = Card("시스템 정보")
        form = FormGrid(columns=2)
        form.add_field("PC 이름", self.pc_name)
        form.add_field("사용자 이름", self.user_name)
        form.add_field("Windows", self.windows)
        form.add_field("상세 버전", self.windows_detail)
        card.body_layout.addWidget(form)
        return card

    def _hardware_card(self) -> QWidget:
        card = Card("하드웨어 정보")
        form = FormGrid(columns=1)
        form.add_field("CPU", self.cpu)
        form.add_field("RAM", self.ram)
        form.add_field("GPU", self.gpu)
        card.body_layout.addWidget(form)
        return card

    def _pc_actions_card(self) -> QWidget:
        card = Card("PC 작업", "PC 이름 변경은 재부팅 후 적용됩니다.")
        card.body_layout.addWidget(self.rename_button)
        card.body_layout.addWidget(self.auto_rename_button)
        card.body_layout.addWidget(self.status_label)
        return card

    def _disk_card(self) -> QWidget:
        card = Card("디스크 정보")
        card.body_layout.addWidget(self.disk_table)
        return card

    def _security_card(self) -> QWidget:
        card = Card("보안/호환 상태")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        _add_value_row(grid, 0, "TPM 버전", self.tpm_version)
        _add_value_row(grid, 1, "TPM 상태", self.tpm_status)
        _add_value_row(grid, 2, "Secure Boot", self.secure_boot)
        _add_value_row(grid, 3, "Boot Mode", self.boot_mode)
        card.body_layout.addLayout(grid)
        return card

    def _refresh(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("PC 정보를 새로고침하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self.set_busy(True)
        try:
            self._view_model.refresh()
            self._render()
        finally:
            self.set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _rename_pc(self) -> None:
        if self._test_mode:
            QMessageBox.information(self, "테스트 모드", TEST_MODE_DISABLED_MESSAGE)
            return
        new_name, accepted = QInputDialog.getText(self, "PC 이름 변경", "새 PC 이름")
        if not accepted:
            return
        result = self._view_model.rename_pc(new_name)
        self._show_rename_result(result)

    def _auto_rename_pc(self) -> None:
        if self._test_mode:
            QMessageBox.information(self, "테스트 모드", TEST_MODE_DISABLED_MESSAGE)
            return
        result = self._view_model.auto_rename_pc()
        self._show_rename_result(result)

    def _show_rename_result(self, result: object | None) -> None:
        self._render()
        message = getattr(result, "message", self._view_model.status_message)
        if getattr(result, "success", False):
            QMessageBox.information(self, "재부팅 필요", f"{message}\n재부팅 후 적용됩니다.")
        else:
            QMessageBox.warning(self, "PC 이름 변경 실패", message)

    def render(self) -> None:
        self._render()

    def set_busy(self, is_busy: bool) -> None:
        self.refresh_button.setEnabled(not is_busy)
        self.rename_button.setEnabled(not is_busy and not self._test_mode)
        self.auto_rename_button.setEnabled(not is_busy and not self._test_mode)
        if self._test_mode:
            for button in (self.rename_button, self.auto_rename_button):
                button.setToolTip(TEST_MODE_DISABLED_MESSAGE)

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.summary_pc_name.set_value(self._view_model.pc_name)
        self.summary_windows.set_value(self._view_model.windows_version)
        self.summary_user.set_value(self._view_model.user_name)
        self.pc_name.setText(self._view_model.pc_name)
        self.user_name.setText(self._view_model.user_name)
        self.windows.setText(self._view_model.windows_version)
        self.windows_detail.setText(self._view_model.windows_version_detail)
        self.cpu.setText(self._view_model.cpu)
        self.ram.setText(self._view_model.ram)
        self.gpu.setText(self._view_model.gpu)
        self.tpm_version.set_status(self._view_model.tpm_version, "neutral")
        self.tpm_status.set_status(self._view_model.tpm_status_text)
        self.secure_boot.set_status(self._view_model.secure_boot_status_text)
        self.boot_mode.set_status(self._view_model.boot_mode)
        self.disk_table.setRowCount(len(self._view_model.disks))
        for row_index, row in enumerate(self._view_model.disks):
            for column_index, value in enumerate(row):
                self.disk_table.setItem(row_index, column_index, table_item(value))
        for field in (
            self.pc_name,
            self.user_name,
            self.windows,
            self.windows_detail,
            self.cpu,
            self.ram,
            self.gpu,
            self.tpm_version,
        ):
            field.setToolTip(field.text())


def _add_value_row(grid: QGridLayout, row: int, label_text: str, widget: QWidget) -> None:
    label = QLabel(label_text)
    label.setObjectName("fieldLabel")
    grid.addWidget(label, row, 0)
    grid.addWidget(widget, row, 1)
