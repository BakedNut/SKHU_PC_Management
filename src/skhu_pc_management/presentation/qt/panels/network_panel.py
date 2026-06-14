from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
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
        self.refresh_button = QPushButton("어댑터 새로고침")
        self.defaults_button = QPushButton("기본값 입력")
        self.ip_input = QLineEdit()
        self.subnet_input = QLineEdit("255.255.255.0")
        self.gateway_input = QLineEdit()
        self.dns1_input = QLineEdit()
        self.dns2_input = QLineEdit()
        self.apply_button = QPushButton("정적 IP 적용")
        self.dhcp_button = QPushButton("DHCP 전환")
        self.status_label = QLabel(view_model.status_message)

        form = QFormLayout()
        form.addRow("어댑터", self.adapter_combo)
        form.addRow("IP 주소", self.ip_input)
        form.addRow("서브넷 마스크", self.subnet_input)
        form.addRow("게이트웨이", self.gateway_input)
        form.addRow("DNS1", self.dns1_input)
        form.addRow("DNS2", self.dns2_input)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.defaults_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.dhcp_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.refresh_button.clicked.connect(self._load_adapters)
        self.defaults_button.clicked.connect(self._fill_defaults)
        self.ip_input.textEdited.connect(self._update_gateway_from_ip)
        self.apply_button.clicked.connect(self._apply_static_ip)
        self.dhcp_button.clicked.connect(self._set_dhcp)
        self._apply_test_mode()

    def _load_adapters(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("네트워크 어댑터를 불러오는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.load_adapters()
            self.adapter_combo.clear()
            for adapter in self._view_model.adapters:
                self.adapter_combo.addItem(adapter.name)
            self.status_label.setText(self._view_model.status_message)
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

    def _update_gateway_from_ip(self, value: str) -> None:
        gateway = self._view_model.gateway_for_ip_address(value)
        if gateway is not None:
            self.gateway_input.setText(gateway)

    def _apply_static_ip(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        if QMessageBox.question(self, "정적 IP 적용", "입력한 네트워크 설정을 적용하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("정적 IP를 적용하는 중..."):
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
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _set_dhcp(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        if QMessageBox.question(self, "DHCP 전환", "선택한 어댑터를 DHCP로 전환하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("DHCP로 전환하는 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.set_dhcp(self.adapter_combo.currentText())
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

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
