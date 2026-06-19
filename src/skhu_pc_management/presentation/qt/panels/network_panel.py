from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.styles import make_card, set_button_role
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel


class NetworkPanel(QWidget):
    def __init__(
        self,
        view_model: NetworkViewModel,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode

        self.adapter_combo = QComboBox()
        self.dhcp_button = QPushButton("자동 IP(DHCP)로 전환")
        self.defaults_button = QPushButton("기본값 넣기")
        self.apply_button = QPushButton("IP 설정 적용")
        set_button_role(self.apply_button, "primary")
        self.refresh_button = QPushButton("어댑터 새로고침")
        self.ip_input = QLineEdit()
        self.subnet_input = QLineEdit("255.255.255.0")
        self.gateway_input = QLineEdit()
        self.dns1_input = QLineEdit()
        self.dns2_input = QLineEdit()
        self.validation_label = QLabel("")
        self.status_label = QLabel(view_model.status_message)
        self.ip_status_label = QLabel(view_model.ip_status_text)
        self.current_table = QTableWidget(0, 2)
        self.current_table.setHorizontalHeaderLabels(["항목", "값"])
        self.current_table.horizontalHeader().setStretchLastSection(True)
        self.current_table.setAlternatingRowColors(True)

        root = QGridLayout(self)
        root.setColumnStretch(0, 120)
        root.setColumnStretch(1, 100)
        root.setHorizontalSpacing(12)
        root.addWidget(self._config_card(), 0, 0)
        root.addWidget(self._status_card(), 0, 1)

        self.refresh_button.clicked.connect(self._load_adapters)
        self.defaults_button.clicked.connect(self._fill_defaults)
        self.ip_input.textEdited.connect(self._update_gateway_from_ip)
        self.adapter_combo.currentTextChanged.connect(self._adapter_changed)
        self.apply_button.clicked.connect(self._apply_static_ip)
        self.dhcp_button.clicked.connect(self._set_dhcp)
        self._apply_test_mode()

    def _config_card(self) -> QWidget:
        card, layout = make_card("IP 구성 작업")
        buttons = QHBoxLayout()
        buttons.addWidget(self.dhcp_button)
        buttons.addWidget(self.defaults_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        grid = QGridLayout()
        _add_field(grid, 0, "어댑터", self.adapter_combo)
        _add_field(grid, 1, "IP 주소", self.ip_input)
        _add_field(grid, 2, "서브넷 마스크", self.subnet_input)
        _add_field(grid, 3, "기본 게이트웨이", self.gateway_input)
        _add_field(grid, 4, "기본 DNS", self.dns1_input)
        _add_field(grid, 5, "보조 DNS", self.dns2_input)
        grid.addWidget(self.validation_label, 6, 1)
        layout.addLayout(grid)
        layout.addWidget(self.status_label)
        return card

    def _status_card(self) -> QWidget:
        card, layout = make_card("현재 네트워크 상태")
        row = QHBoxLayout()
        label = QLabel("할당 방식:")
        label.setObjectName("fieldLabel")
        row.addWidget(label)
        row.addWidget(self.ip_status_label)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(self.current_table)
        return card

    def _load_adapters(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("네트워크 어댑터를 불러오는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.load_adapters()
            self.adapter_combo.blockSignals(True)
            self.adapter_combo.clear()
            for adapter in self._view_model.adapters:
                self.adapter_combo.addItem(adapter.name)
            if self._view_model.selected_adapter is not None:
                self.adapter_combo.setCurrentText(self._view_model.selected_adapter.name)
            self.adapter_combo.blockSignals(False)
            self._fill_from_selected_adapter()
            self._render_status()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _fill_defaults(self) -> None:
        defaults = self._view_model.default_static_ip_fields()
        self.ip_input.setText(defaults["ip_address"])
        self.subnet_input.setText(defaults["subnet_mask"])
        self.gateway_input.setText(defaults["gateway"])
        self.dns1_input.setText(defaults["dns1"])
        self.dns2_input.setText(defaults["dns2"])

    def _fill_from_selected_adapter(self) -> None:
        adapter = self._view_model.selected_adapter
        if adapter is None:
            return
        self.ip_input.setText(adapter.ip_addresses[0] if adapter.ip_addresses else "")
        self.subnet_input.setText(adapter.subnet_mask or "255.255.255.0")
        self.gateway_input.setText(adapter.gateway or "")
        self.dns1_input.setText(adapter.dns_servers[0] if len(adapter.dns_servers) >= 1 else "")
        self.dns2_input.setText(adapter.dns_servers[1] if len(adapter.dns_servers) >= 2 else "")

    def _update_gateway_from_ip(self, value: str) -> None:
        gateway = self._view_model.gateway_for_ip_address(value)
        if gateway is not None:
            self.gateway_input.setText(gateway)

    def _adapter_changed(self, adapter_name: str) -> None:
        self._view_model.select_adapter_by_name(adapter_name)
        self._fill_from_selected_adapter()
        self._render_status()

    def _apply_static_ip(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return
        if QMessageBox.question(self, "IP 설정 적용", "입력한 네트워크 설정을 적용하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("IP 설정을 적용하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.apply_static_ip(
                self.adapter_combo.currentText(),
                self.ip_input.text(),
                self.subnet_input.text(),
                self.gateway_input.text(),
                self.dns1_input.text(),
                self.dns2_input.text(),
            )
            self._render_status()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _set_dhcp(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return
        if QMessageBox.question(self, "자동 IP(DHCP)로 전환", "선택한 어댑터를 DHCP로 전환하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("DHCP로 전환하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.set_dhcp(self.adapter_combo.currentText())
            self._render_status()
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _render_status(self) -> None:
        self.status_label.setText(self._view_model.status_message)
        self.validation_label.setText(self._view_model.validation_message)
        self.ip_status_label.setText(self._view_model.ip_status_text)
        self.current_table.setRowCount(len(self._view_model.current_network_info_rows))
        for row_index, row in enumerate(self._view_model.current_network_info_rows):
            self.current_table.setItem(row_index, 0, QTableWidgetItem(row[0]))
            self.current_table.setItem(row_index, 1, QTableWidgetItem(row[1]))

    def _set_busy(self, is_busy: bool) -> None:
        self.refresh_button.setEnabled(not is_busy)
        self.defaults_button.setEnabled(not is_busy)
        self.apply_button.setEnabled(not is_busy and not self._test_mode)
        self.dhcp_button.setEnabled(not is_busy and not self._test_mode)

    def _apply_test_mode(self) -> None:
        if not self._test_mode:
            return
        for button in (self.apply_button, self.dhcp_button):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)
        self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)


def _add_field(grid: QGridLayout, row: int, label_text: str, widget: QWidget) -> None:
    label = QLabel(label_text)
    label.setObjectName("fieldLabel")
    grid.addWidget(label, row, 0)
    grid.addWidget(widget, row, 1)
