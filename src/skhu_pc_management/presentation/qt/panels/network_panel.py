from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class NetworkPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("네트워크 설정 기능은 아직 구현되지 않았습니다."))
        layout.addStretch()
