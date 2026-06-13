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

from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel


class NetworkPanel(QWidget):
    def __init__(self, view_model: NetworkViewModel) -> None:
        super().__init__()
        self._view_model = view_model

        self.adapter_combo = QComboBox()
        self.refresh_button = QPushButton("어댑터 새로고침")
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
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.dhcp_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.refresh_button.clicked.connect(self._load_adapters)
        self.apply_button.clicked.connect(self._apply_static_ip)
        self.dhcp_button.clicked.connect(self._set_dhcp)

    def _load_adapters(self) -> None:
        self._set_busy(True)
        try:
            self._view_model.load_adapters()
            self.adapter_combo.clear()
            for adapter in self._view_model.adapters:
                self.adapter_combo.addItem(adapter.name)
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)

    def _apply_static_ip(self) -> None:
        if QMessageBox.question(self, "정적 IP 적용", "입력한 네트워크 설정을 적용하시겠습니까?") != QMessageBox.Yes:
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

    def _set_dhcp(self) -> None:
        if QMessageBox.question(self, "DHCP 전환", "선택한 어댑터를 DHCP로 전환하시겠습니까?") != QMessageBox.Yes:
            return
        self._set_busy(True)
        try:
            self._view_model.set_dhcp(self.adapter_combo.currentText())
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)

    def _set_busy(self, is_busy: bool) -> None:
        self.refresh_button.setEnabled(not is_busy)
        self.apply_button.setEnabled(not is_busy)
        self.dhcp_button.setEnabled(not is_busy)
