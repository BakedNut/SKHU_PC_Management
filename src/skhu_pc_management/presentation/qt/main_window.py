from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from skhu_pc_management.application.safety import TEST_MODE_DISABLED_MESSAGE
from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator
from skhu_pc_management.presentation.qt.panels.action_center_panel import ActionCenterPanel
from skhu_pc_management.presentation.qt.panels.network_panel import NetworkPanel
from skhu_pc_management.presentation.qt.panels.pc_info_panel import PcInfoPanel
from skhu_pc_management.presentation.qt.startup_coordinator import StartupCoordinator
from skhu_pc_management.presentation.qt.styles import APP_QSS
from skhu_pc_management.presentation.qt.widgets.badges import StatusBadge
from skhu_pc_management.presentation.qt.widgets.buttons import nav_button
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

        self.windows_badge = StatusBadge("Windows: 알 수 없음", "info")
        self.pc_badge = StatusBadge("PC: 알 수 없음", "neutral")
        self.test_mode_badge = StatusBadge("테스트 모드", "warning")
        self.test_mode_badge.setVisible(test_mode)

        self.busy_banner = QFrame()
        self.busy_banner.setObjectName("infoBanner")
        self.busy_banner.setVisible(False)
        busy_layout = QVBoxLayout(self.busy_banner)
        busy_layout.setContentsMargins(14, 10, 14, 10)
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedText")
        busy_layout.addWidget(self.status_label)

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
        self.stack = QStackedWidget()
        self.stack.addWidget(self.pc_info_panel)
        self.stack.addWidget(self.action_center_panel)
        self.stack.addWidget(self.network_panel)

        self.nav_buttons = [
            nav_button("PC 정보"),
            nav_button("작업 센터"),
            nav_button("네트워크"),
        ]
        for index, button in enumerate(self.nav_buttons):
            button.clicked.connect(lambda checked=False, page_index=index: self._select_page(page_index))

        central = QWidget()
        central.setObjectName("appShell")
        shell = QVBoxLayout(central)
        shell.setContentsMargins(16, 16, 16, 16)
        shell.setSpacing(14)
        shell.addWidget(self._top_bar())
        shell.addWidget(self.busy_banner)
        if test_mode:
            test_banner = QFrame()
            test_banner.setObjectName("warningBanner")
            test_layout = QVBoxLayout(test_banner)
            test_layout.setContentsMargins(14, 10, 14, 10)
            test_text = QLabel(TEST_MODE_DISABLED_MESSAGE)
            test_text.setObjectName("mutedText")
            test_layout.addWidget(test_text)
            shell.addWidget(test_banner)
        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._side_nav(), 0)
        body.addWidget(self._content_surface(), 1)
        shell.addLayout(body, 1)
        self.setCentralWidget(central)
        self.resize(1350, 1020)
        self.setMinimumSize(1000, 700)
        self._select_page(0)
        self._apply_branding()
        QTimer.singleShot(0, self.initialize_startup)

    def _top_bar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("topBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel("성공회대학교 PC 관리 프로그램")
        title.setObjectName("appTitle")
        subtitle = QLabel("SKHU PC Management")
        subtitle.setObjectName("appSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column)
        layout.addStretch()
        layout.addWidget(self.windows_badge)
        layout.addWidget(self.pc_badge)
        layout.addWidget(self.test_mode_badge)
        return frame

    def _side_nav(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("sideNav")
        frame.setFixedWidth(210)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        for button in self.nav_buttons:
            layout.addWidget(button)
        layout.addStretch()
        return frame

    def _content_surface(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("contentSurface")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(0)
        layout.addWidget(self.stack)
        return frame

    def _select_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("selected", "true" if button_index == index else "false")
            button.style().unpolish(button)
            button.style().polish(button)

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
        self.busy_banner.setVisible(is_busy)
        self.status_label.setText(message)
        self.stack.setEnabled(not is_busy)
        for button in self.nav_buttons:
            button.setEnabled(not is_busy)

    def _update_header_badges(self) -> None:
        self.windows_badge.set_status(self._pc_info_view_model.windows_version or "Windows: 알 수 없음", "info")
        self.pc_badge.set_status(self._pc_info_view_model.pc_name or "PC: 알 수 없음", "neutral")

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
