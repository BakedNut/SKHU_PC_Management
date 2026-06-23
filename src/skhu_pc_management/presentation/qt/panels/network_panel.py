from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.widgets.buttons import primary_button, secondary_button, subtle_button
from skhu_pc_management.presentation.qt.widgets.forms import FieldRow
from skhu_pc_management.presentation.qt.widgets.surfaces import Card
from skhu_pc_management.presentation.qt.widgets.tables import configure_table, set_column_widths, table_item


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
        self.dhcp_button = secondary_button("자동 IP(DHCP)로 전환")
        self.defaults_button = subtle_button("학교 기본 대역 입력")
        self.apply_button = primary_button("IP 설정 적용")
        self.refresh_button = primary_button("어댑터 새로고침")
        self.ip_input = QLineEdit()
        self.subnet_input = QLineEdit("255.255.255.0")
        self.gateway_input = QLineEdit()
        self.dns1_input = QLineEdit()
        self.dns2_input = QLineEdit()
        self.validation_label = QLabel("")
        self.validation_label.setObjectName("mutedText")
        self.status_label = QLabel(view_model.status_message)
        self.status_label.setObjectName("mutedText")

        self.current_table = QTableWidget(0, 2)
        self.current_table.setHorizontalHeaderLabels(["항목", "값"])
        configure_table(self.current_table, compact=True)
        set_column_widths(self.current_table, (140,))
        self.current_table.setMinimumHeight(190)
        self.current_table.setMaximumHeight(250)

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
        content_layout.addLayout(self._body_layout())
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

        self.refresh_button.clicked.connect(self._load_adapters)
        self.defaults_button.clicked.connect(self._fill_defaults)
        self.ip_input.textEdited.connect(self._update_gateway_from_ip)
        for widget in (self.subnet_input, self.gateway_input, self.dns1_input, self.dns2_input):
            widget.textEdited.connect(self._render_validation)
        self.adapter_combo.currentTextChanged.connect(self._adapter_changed)
        self.apply_button.clicked.connect(self._apply_static_ip)
        self.dhcp_button.clicked.connect(self._set_dhcp)
        self._apply_test_mode()
        self._render_status_message()

    def _page_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("네트워크")
        title.setObjectName("pageTitle")
        subtitle = QLabel("네트워크 어댑터의 현재 상태를 확인하고 IP 구성을 변경합니다.")
        subtitle.setObjectName("pageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        row.addLayout(title_column)
        row.addStretch()
        row.addWidget(self.refresh_button)
        return row

    def _body_layout(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._config_card(), 3)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._status_card())
        right.addStretch()
        body.addLayout(right, 2)
        return body

    def _config_card(self) -> QWidget:
        card = Card("IP 구성")
        form_container = QWidget()
        form_container.setObjectName("transparentContainer")
        form_container.setMaximumWidth(760)
        grid = QGridLayout(form_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        _add_field(grid, 0, 0, "어댑터", _combo_with_arrow(self.adapter_combo))
        _add_field(grid, 1, 0, "IP 주소", self.ip_input)
        _add_field(grid, 1, 1, "서브넷 마스크", self.subnet_input)
        _add_field(grid, 2, 0, "기본 게이트웨이", self.gateway_input)
        _add_field(grid, 2, 1, "기본 DNS", self.dns1_input)
        _add_field(grid, 3, 0, "보조 DNS", self.dns2_input)
        card.body_layout.addWidget(form_container)
        self.validation_banner = QFrame()
        self.validation_banner.setObjectName("infoBanner")
        validation_layout = QVBoxLayout(self.validation_banner)
        validation_layout.setContentsMargins(12, 8, 12, 8)
        validation_layout.addWidget(self.validation_label)
        card.body_layout.addWidget(self.validation_banner)
        card.body_layout.addWidget(self.status_label)
        button_row = QHBoxLayout()
        button_row.addWidget(self.defaults_button)
        button_row.addStretch()
        button_row.addWidget(self.dhcp_button)
        button_row.addWidget(self.apply_button)
        card.body_layout.addLayout(button_row)
        return card

    def _status_card(self) -> QWidget:
        card = Card("현재 네트워크 상태")
        card.body_layout.setSpacing(8)
        card.body_layout.addWidget(self.current_table)
        return card

    def _load_adapters(self) -> None:
        if self._busy_coordinator and not self._busy_coordinator.try_begin("네트워크 어댑터를 불러오는 중..."):
            self._set_status_message("다른 작업이 진행 중입니다.")
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

    def load_adapters(self) -> None:
        self._load_adapters()

    def _fill_defaults(self) -> None:
        defaults = self._view_model.default_static_ip_fields()
        self.ip_input.setText(defaults["ip_address"])
        self.subnet_input.setText(defaults["subnet_mask"])
        self.gateway_input.setText(defaults["gateway"])
        self.dns1_input.setText(defaults["dns1"])
        self.dns2_input.setText(defaults["dns2"])
        self._render_status()

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
        self._render_validation()

    def _adapter_changed(self, adapter_name: str) -> None:
        self._view_model.select_adapter_by_name(adapter_name)
        self._fill_from_selected_adapter()
        self._render_status()

    def _apply_static_ip(self) -> None:
        if self._test_mode:
            self._set_status_message(TEST_MODE_DISABLED_MESSAGE)
            return
        if QMessageBox.question(self, "IP 설정 적용", "입력한 네트워크 설정을 적용하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("IP 설정을 적용하는 중..."):
            self._set_status_message("다른 작업이 진행 중입니다.")
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
            self._set_status_message(TEST_MODE_DISABLED_MESSAGE)
            return
        if QMessageBox.question(self, "자동 IP(DHCP)로 전환", "선택한 어댑터를 DHCP로 전환하시겠습니까?") != QMessageBox.Yes:
            return
        if self._busy_coordinator and not self._busy_coordinator.try_begin("DHCP로 전환하는 중..."):
            self._set_status_message("다른 작업이 진행 중입니다.")
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
        self._render_status_message()
        self._render_validation()
        self.current_table.setRowCount(len(self._view_model.current_network_info_rows))
        for row_index, row in enumerate(self._view_model.current_network_info_rows):
            self.current_table.setItem(row_index, 0, table_item(row[0]))
            self.current_table.setItem(row_index, 1, table_item(row[1]))
        self._resize_current_table_to_contents()

    def _render_validation(self) -> None:
        is_valid, message = self._view_model.validate_static_ip_fields(
            self.adapter_combo.currentText(),
            self.ip_input.text(),
            self.subnet_input.text(),
            self.gateway_input.text(),
            self.dns1_input.text(),
            self.dns2_input.text(),
        )
        text = self._view_model.validation_message or message or "입력값을 확인한 뒤 적용하세요."
        self.validation_label.setText(text)
        self.validation_banner.setObjectName("infoBanner" if is_valid and not self._view_model.validation_message else "warningBanner")
        self.validation_banner.style().unpolish(self.validation_banner)
        self.validation_banner.style().polish(self.validation_banner)

    def _render_status_message(self) -> None:
        self._set_status_message(self._view_model.status_message)

    def _set_status_message(self, message: str) -> None:
        display_message = _display_network_status_message(message)
        self.status_label.setText(display_message)
        self.status_label.setVisible(bool(display_message))

    def _resize_current_table_to_contents(self) -> None:
        self.current_table.setFixedHeight(_current_table_height(self.current_table.rowCount()))

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
        self._set_status_message(TEST_MODE_DISABLED_MESSAGE)


def _add_field(grid: QGridLayout, row: int, column: int, label_text: str, widget: QWidget) -> None:
    grid.addWidget(FieldRow(label_text, widget), row, column)


def _combo_with_arrow(combo: QComboBox) -> QWidget:
    wrapper = QFrame()
    wrapper.setObjectName("comboShell")
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    combo.setObjectName("comboInShell")
    arrow = QLabel("▾")
    arrow.setObjectName("comboArrow")
    arrow.setAttribute(Qt.WA_TransparentForMouseEvents)

    layout.addWidget(combo, 1)
    layout.addWidget(arrow)
    return wrapper


def _display_network_status_message(message: str) -> str:
    text = message.strip()
    if not text:
        return ""
    suppressed_fragments = (
        "네트워크 어댑터를 불러오지 않았습니다.",
        "네트워크 어댑터를 불러오는 중입니다",
        "개를 불러왔습니다.",
    )
    if any(fragment in text for fragment in suppressed_fragments):
        return ""
    return text


def _current_table_height(row_count: int) -> int:
    normalized_row_count = max(1, row_count)
    height = 42 + normalized_row_count * 28
    return min(max(height, 180), 250)
