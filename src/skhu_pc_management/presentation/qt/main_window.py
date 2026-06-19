from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.panels.action_center_panel import ActionCenterPanel
from skhu_pc_management.presentation.qt.panels.network_panel import NetworkPanel
from skhu_pc_management.presentation.qt.panels.pc_info_panel import PcInfoPanel
from skhu_pc_management.presentation.qt.startup_coordinator import StartupCoordinator
from skhu_pc_management.presentation.qt.styles import APP_QSS
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
        launch_program_use_case: object | None = None,
        maintenance_use_case: object | None = None,
        resource_resolver: ResourceResolver | None = None,
        test_mode: bool = False,
    ) -> None:
        super().__init__()
        self.setWindowTitle("성공회대학교 PC 관리 프로그램")
        self.setStyleSheet(APP_QSS)
        self._pc_info_view_model = pc_info_view_model
        self._startup_coordinator = startup_coordinator
        self._resource_resolver = resource_resolver
        self._test_mode = test_mode
        self._busy_coordinator = BusyCoordinator()
        self._busy_coordinator.add_listener(self._on_busy_changed)
        self.is_busy = self._busy_coordinator.is_busy
        self.busy_message = self._busy_coordinator.message

        self.windows_badge = QLabel("Windows: 알 수 없음")
        self.windows_badge.setObjectName("windowsBadge")
        self.pc_badge = QLabel("PC: 알 수 없음")
        self.pc_badge.setObjectName("pcBadge")
        self.busy_card = QFrame()
        self.busy_card.setObjectName("busyCard")
        self.busy_card.setVisible(False)
        busy_layout = QVBoxLayout(self.busy_card)
        busy_layout.setContentsMargins(10, 8, 10, 8)
        self.status_label = QLabel("")
        self.status_label.setObjectName("busyLabel")
        busy_layout.addWidget(self.status_label)

        self.test_mode_label = QLabel(TEST_MODE_DISABLED_MESSAGE if test_mode else "")
        self.test_mode_label.setVisible(test_mode)
        self.test_mode_label.setObjectName("busyLabel")

        self.tabs = QTabWidget()
        self.pc_info_panel = PcInfoPanel(pc_info_view_model, self._busy_coordinator, test_mode=test_mode)
        self.action_center_panel = ActionCenterPanel(
            settings_view_model,
            pc_check_view_model,
            activation_view_model,
            launch_program_use_case,
            maintenance_use_case,
            self._busy_coordinator,
            test_mode=test_mode,
        )
        self.network_panel = NetworkPanel(network_view_model, self._busy_coordinator, test_mode=test_mode)
        self.tabs.addTab(self.pc_info_panel, "PC 정보")
        self.tabs.addTab(self.action_center_panel, "작업 센터")
        self.tabs.addTab(self.network_panel, "네트워크")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self._header())
        layout.addWidget(self.busy_card)
        layout.addWidget(self.test_mode_label)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)
        self.resize(1350, 1020)
        self.setMinimumSize(900, 600)
        self._apply_branding()
        QTimer.singleShot(0, self.initialize_startup)

    def _header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("headerCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("SKHU PC Management")
        title.setObjectName("headerTitle")
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.windows_badge)
        layout.addWidget(self.pc_badge)
        return frame

    def initialize_startup(self) -> None:
        if not self._busy_coordinator.try_begin("초기 정보를 불러오는 중..."):
            return

        try:
            result = self._startup_coordinator.initialize()
            self.pc_info_panel.render()
            self.action_center_panel.render()
            self.action_center_panel.set_detected_windows_text(self._pc_info_view_model.windows_version)
            self._update_header_badges()

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
        self.busy_card.setVisible(is_busy)
        self.status_label.setText(message)
        self.tabs.setEnabled(not is_busy)

    def _update_header_badges(self) -> None:
        self.windows_badge.setText(self._pc_info_view_model.windows_version)
        self.pc_badge.setText(self._pc_info_view_model.pc_name)

    def _apply_branding(self) -> None:
        if self._resource_resolver is None:
            return
        try:
            icon_path = self._resource_resolver.resolve("images/skhu_logo.ico")
        except Exception:
            return
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            self.setWindowIcon(icon)
