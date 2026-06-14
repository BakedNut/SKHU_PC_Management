from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.panels.activation_panel import ActivationPanel
from skhu_pc_management.presentation.qt.panels.network_panel import NetworkPanel
from skhu_pc_management.presentation.qt.panels.pc_check_panel import PcCheckPanel
from skhu_pc_management.presentation.qt.panels.pc_info_panel import PcInfoPanel
from skhu_pc_management.presentation.qt.panels.settings_panel import SettingsPanel
from skhu_pc_management.presentation.qt.startup_coordinator import StartupCoordinator
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel
from skhu_pc_management.ports.resource_resolver import ResourceResolver


class MainWindow(QMainWindow):
    def __init__(
        self,
        pc_info_view_model: PcInfoViewModel,
        settings_view_model: SettingsViewModel,
        network_view_model: NetworkViewModel,
        pc_check_view_model: PcCheckViewModel,
        activation_view_model: ActivationViewModel,
        startup_coordinator: StartupCoordinator,
        resource_resolver: ResourceResolver | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self.setWindowTitle("SKHU PC Management")
        self._startup_coordinator = startup_coordinator
        self._resource_resolver = resource_resolver
        self._test_mode = test_mode
        self._busy_coordinator = BusyCoordinator()
        self._busy_coordinator.add_listener(self._on_busy_changed)
        self.is_busy = self._busy_coordinator.is_busy
        self.busy_message = self._busy_coordinator.message

        self.status_label = QLabel("")
        self.test_mode_label = QLabel(TEST_MODE_DISABLED_MESSAGE if test_mode else "")
        self.test_mode_label.setVisible(test_mode)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(32, 32)
        self.logo_label.setScaledContents(True)
        self.title_label = QLabel("SKHU PC Management")
        self.tabs = QTabWidget()
        self.pc_info_panel = PcInfoPanel(pc_info_view_model, self._busy_coordinator)
        self.settings_panel = SettingsPanel(settings_view_model, self._busy_coordinator, test_mode=test_mode)
        self.network_panel = NetworkPanel(network_view_model, self._busy_coordinator, test_mode=test_mode)
        self.pc_check_panel = PcCheckPanel(pc_check_view_model, self._busy_coordinator)
        self.activation_panel = ActivationPanel(activation_view_model, self._busy_coordinator, test_mode=test_mode)
        self.tabs.addTab(self.pc_info_panel, "PC 정보")
        self.tabs.addTab(self.settings_panel, "기본 설정")
        self.tabs.addTab(self.network_panel, "네트워크 설정")
        self.tabs.addTab(self.pc_check_panel, "PC 점검")
        self.tabs.addTab(self.activation_panel, "인증")

        central = QWidget()
        layout = QVBoxLayout(central)
        header = QHBoxLayout()
        header.addWidget(self.logo_label)
        header.addWidget(self.title_label)
        header.addStretch()
        layout.addLayout(header)
        layout.addWidget(self.test_mode_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)
        self.resize(1000, 700)
        self._apply_branding()
        QTimer.singleShot(0, self.initialize_startup)

    def initialize_startup(self) -> None:
        if not self._busy_coordinator.try_begin("초기 정보를 불러오는 중..."):
            return

        try:
            result = self._startup_coordinator.initialize()
            self.pc_info_panel.render()
            self.settings_panel.render()
            self.pc_check_panel.render()

            messages: list[str] = []
            if not result.is_admin:
                warning = "관리자 권한이 아닙니다. 일부 기능이 제한될 수 있습니다."
                messages.append(warning)
                QMessageBox.warning(self, "관리자 권한 필요", warning)
            if result.has_failures:
                failed = ", ".join(
                    f"{step.name}: {step.message}" for step in result.step_results if not step.success
                )
                messages.append(f"초기화 일부 실패: {failed}")
            if not messages:
                messages.append("초기 정보를 불러왔습니다.")
            if self._test_mode:
                messages.append(TEST_MODE_DISABLED_MESSAGE)
            final_message = " ".join(messages)
        finally:
            self._busy_coordinator.end(locals().get("final_message", "초기화가 완료되었습니다."))
            QTimer.singleShot(0, self.network_panel._load_adapters)

    def _on_busy_changed(self, is_busy: bool, message: str) -> None:
        self.is_busy = is_busy
        self.busy_message = message
        if message:
            self.status_label.setText(message)
        self.tabs.setEnabled(not is_busy)

    def _apply_branding(self) -> None:
        if self._resource_resolver is None:
            return
        try:
            icon_path = self._resource_resolver.resolve("images/skhu_logo.ico")
        except Exception:
            return
        icon = QIcon(str(icon_path))
        if icon.isNull():
            return
        self.setWindowIcon(icon)
        self.logo_label.setPixmap(icon.pixmap(32, 32))
