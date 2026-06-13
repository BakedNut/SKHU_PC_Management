from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel


class ActivationPanel(QWidget):
    def __init__(self, view_model: ActivationViewModel) -> None:
        super().__init__()
        self._view_model = view_model

        self.windows_button = QPushButton("Windows 인증 준비")
        self.office_button = QPushButton("Office 인증 준비")
        self.status_label = QLabel(view_model.status_message)

        layout = QVBoxLayout(self)
        layout.addWidget(self.windows_button)
        layout.addWidget(self.office_button)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.windows_button.clicked.connect(self._prepare_windows)
        self.office_button.clicked.connect(self._prepare_office)

    def _prepare_windows(self) -> None:
        self._set_busy(True)
        try:
            self._view_model.prepare_windows_activation()
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)

    def _prepare_office(self) -> None:
        self._set_busy(True)
        try:
            self._view_model.prepare_office_activation()
            self.status_label.setText(self._view_model.status_message)
        finally:
            self._set_busy(False)

    def _set_busy(self, is_busy: bool) -> None:
        self.windows_button.setEnabled(not is_busy)
        self.office_button.setEnabled(not is_busy)
