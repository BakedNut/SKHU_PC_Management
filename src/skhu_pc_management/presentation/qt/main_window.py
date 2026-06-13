from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from skhu_pc_management.presentation.qt.panels.activation_panel import ActivationPanel
from skhu_pc_management.presentation.qt.panels.network_panel import NetworkPanel
from skhu_pc_management.presentation.qt.panels.pc_check_panel import PcCheckPanel
from skhu_pc_management.presentation.qt.panels.pc_info_panel import PcInfoPanel
from skhu_pc_management.presentation.qt.panels.settings_panel import SettingsPanel
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


class MainWindow(QMainWindow):
    def __init__(
        self,
        pc_info_view_model: PcInfoViewModel,
        settings_view_model: SettingsViewModel,
        network_view_model: NetworkViewModel,
        pc_check_view_model: PcCheckViewModel,
        activation_view_model: ActivationViewModel,
    ) -> None:
        super().__init__()
        self.setWindowTitle("SKHU PC Management")

        tabs = QTabWidget()
        tabs.addTab(PcInfoPanel(pc_info_view_model), "PC 정보")
        tabs.addTab(SettingsPanel(settings_view_model), "기본 설정")
        tabs.addTab(NetworkPanel(network_view_model), "네트워크 설정")
        tabs.addTab(PcCheckPanel(pc_check_view_model), "PC 점검")
        tabs.addTab(ActivationPanel(activation_view_model), "인증")

        self.setCentralWidget(tabs)
        self.resize(1000, 700)
