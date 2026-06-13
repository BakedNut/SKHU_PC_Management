from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from skhu_pc_management.presentation.qt.panels.network_panel import NetworkPanel
from skhu_pc_management.presentation.qt.panels.pc_check_panel import PcCheckPanel
from skhu_pc_management.presentation.qt.panels.pc_info_panel import PcInfoPanel
from skhu_pc_management.presentation.qt.panels.settings_panel import SettingsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SKHU PC Management")

        tabs = QTabWidget()
        tabs.addTab(PcInfoPanel(), "PC 정보")
        tabs.addTab(SettingsPanel(), "기본 설정")
        tabs.addTab(NetworkPanel(), "네트워크 설정")
        tabs.addTab(PcCheckPanel(), "PC 점검")

        self.setCentralWidget(tabs)
        self.resize(900, 600)
