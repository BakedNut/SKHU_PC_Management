from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.styles import make_card, set_button_role
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel


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
        self.refresh_button = QPushButton("PC 정보 새로고침")
        set_button_role(self.refresh_button, "primary")
        self.rename_button = QPushButton("PC 이름 변경")
        self.auto_rename_button = QPushButton("PC 이름 사용자 이름과 맞추기")
        set_button_role(self.auto_rename_button, "danger")

        self.pc_name = _read_only()
        self.user_name = _read_only()
        self.windows = _read_only()
        self.windows_detail = _read_only()
        self.cpu = _read_only()
        self.ram = _read_only()
        self.gpu = _read_only()
        self.tpm_version = _read_only()
        self.tpm_status = QLabel()
        self.secure_boot = _read_only()
        self.boot_mode = _read_only()

        self.disk_table = QTableWidget(0, 4)
        self.disk_table.setHorizontalHeaderLabels(["모델", "타입", "정격 용량", "실제 용량"])
        self.disk_table.horizontalHeader().setStretchLastSection(True)
        self.disk_table.setAlternatingRowColors(True)

        root_layout = QGridLayout(self)
        root_layout.setColumnStretch(0, 115)
        root_layout.setColumnStretch(1, 100)
        root_layout.setHorizontalSpacing(12)

        left = QVBoxLayout()
        left.addWidget(self._system_card())
        left.addWidget(self._hardware_card())
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(self._pc_actions_card())
        right.addWidget(self._disk_card())
        right.addWidget(self._security_card())
        right.addStretch()

        root_layout.addLayout(left, 0, 0)
        root_layout.addLayout(right, 0, 1)

        self.refresh_button.clicked.connect(self._refresh)
        self.rename_button.clicked.connect(self._rename_pc)
        self.auto_rename_button.clicked.connect(self._auto_rename_pc)

    def _system_card(self) -> QWidget:
        card, layout = make_card("시스템 정보")
        grid = QGridLayout()
        _add_field(grid, 0, 0, "PC 이름", self.pc_name)
        _add_field(grid, 0, 1, "사용자 이름", self.user_name)
        _add_field(grid, 1, 0, "Windows", self.windows)
        _add_field(grid, 1, 1, "상세 버전", self.windows_detail)
        layout.addLayout(grid)
        return card

    def _hardware_card(self) -> QWidget:
        card, layout = make_card("하드웨어 정보")
        layout.addWidget(_label("CPU"))
        layout.addWidget(self.cpu)
        layout.addWidget(_label("RAM"))
        layout.addWidget(self.ram)
        layout.addWidget(_label("GPU"))
        layout.addWidget(self.gpu)
        return card

    def _pc_actions_card(self) -> QWidget:
        card, layout = make_card("PC 작업")
        button_row = QGridLayout()
        button_row.addWidget(self.rename_button, 0, 0)
        button_row.addWidget(self.auto_rename_button, 0, 1)
        button_row.addWidget(self.refresh_button, 0, 2)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        return card

    def _disk_card(self) -> QWidget:
        card, layout = make_card("디스크 정보")
        layout.addWidget(self.disk_table)
        return card

    def _security_card(self) -> QWidget:
        card, layout = make_card("보안/호환 상태")
        grid = QGridLayout()
        grid.addWidget(_label("TPM"), 0, 0)
        grid.addWidget(self.tpm_version, 0, 1)
        grid.addWidget(self.tpm_status, 0, 2)
        _add_field(grid, 1, 0, "Secure Boot", self.secure_boot, colspan=2)
        _add_field(grid, 2, 0, "Boot Mode", self.boot_mode, colspan=2)
        layout.addLayout(grid)
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
            QMessageBox.information(self, "테스트 모드", "테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.")
            return
        new_name, accepted = QInputDialog.getText(self, "PC 이름 변경", "새 PC 이름")
        if not accepted:
            return
        result = self._view_model.rename_pc(new_name)
        self._show_rename_result(result)

    def _auto_rename_pc(self) -> None:
        if self._test_mode:
            QMessageBox.information(self, "테스트 모드", "테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.")
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
        self.rename_button.setEnabled(not is_busy)
        self.auto_rename_button.setEnabled(not is_busy)
        if self._test_mode:
            self.rename_button.setEnabled(False)
            self.auto_rename_button.setEnabled(False)

    def _render(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.pc_name.setText(self._view_model.pc_name)
        self.user_name.setText(self._view_model.user_name)
        self.windows.setText(self._view_model.windows_version)
        self.windows_detail.setText(self._view_model.windows_version_detail)
        self.cpu.setText(self._view_model.cpu)
        self.ram.setText(self._view_model.ram)
        self.gpu.setText(self._view_model.gpu)
        self.tpm_version.setText(self._view_model.tpm_version)
        self.tpm_status.setText(self._view_model.tpm_status_text)
        self.secure_boot.setText(self._view_model.secure_boot_status_text)
        self.boot_mode.setText(self._view_model.boot_mode)
        self.disk_table.setRowCount(len(self._view_model.disks))
        for row_index, row in enumerate(self._view_model.disks):
            for column_index, value in enumerate(row):
                self.disk_table.setItem(row_index, column_index, QTableWidgetItem(value))


def _read_only() -> QLineEdit:
    widget = QLineEdit()
    widget.setReadOnly(True)
    return widget


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def _add_field(grid: QGridLayout, row: int, column: int, label: str, widget: QWidget, colspan: int = 1) -> None:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 8)
    layout.addWidget(_label(label))
    layout.addWidget(widget)
    grid.addWidget(container, row, column, 1, colspan)
