from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel


class ActivationPanel(QWidget):
    def __init__(
        self,
        view_model: ActivationViewModel,
        busy_coordinator: BusyCoordinator | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._busy_coordinator = busy_coordinator
        self._test_mode = test_mode

        self.windows_combo = QComboBox()
        self.windows_combo.addItem("Windows 11", "windows_11")
        self.windows_combo.addItem("Windows 10", "windows_10")
        self.office_combo = QComboBox()
        self.office_combo.addItem("Office 2024", "2024")
        self.office_combo.addItem("Office 2021", "2021")
        self.recommended_label = QLabel(_recommended_text(view_model.recommended_office_version))
        self.windows_button = QPushButton("Windows 인증 준비")
        self.office_button = QPushButton("Office 인증 준비")
        self.status_label = QLabel(view_model.status_message)

        form = QFormLayout()
        form.addRow("Windows 버전", self.windows_combo)
        form.addRow("Office 버전", self.office_combo)
        form.addRow("추천 Office", self.recommended_label)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.windows_button)
        layout.addWidget(self.office_button)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.windows_button.clicked.connect(self._prepare_windows)
        self.office_button.clicked.connect(self._prepare_office)
        self._apply_test_mode()

    def _prepare_windows(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        if self._busy_coordinator and not self._busy_coordinator.try_begin("Windows 인증 준비 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.prepare_windows_activation(self.windows_combo.currentData())
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _prepare_office(self) -> None:
        if self._test_mode:
            self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)
            return

        if self._busy_coordinator and not self._busy_coordinator.try_begin("Office 인증 준비 중..."):
            self.status_label.setText("다른 작업이 진행 중입니다.")
            return
        self._set_busy(True)
        try:
            self._view_model.prepare_office_activation(self.office_combo.currentData())
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)
            if self._busy_coordinator:
                self._busy_coordinator.end(self._view_model.status_message)

    def _set_busy(self, is_busy: bool) -> None:
        self.windows_combo.setEnabled(not is_busy)
        self.office_combo.setEnabled(not is_busy)
        self.windows_button.setEnabled(not is_busy and not self._test_mode)
        self.office_button.setEnabled(not is_busy and not self._test_mode)

    def _apply_test_mode(self) -> None:
        if not self._test_mode:
            return
        for button in (self.windows_button, self.office_button):
            button.setEnabled(False)
            button.setToolTip(TEST_MODE_DISABLED_MESSAGE)
        self.status_label.setText(TEST_MODE_DISABLED_MESSAGE)


def _recommended_text(version: str | None) -> str:
    return f"Office {version}" if version in {"2021", "2024"} else "없음"
