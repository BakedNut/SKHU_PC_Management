from __future__ import annotations

import os

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.application.use_cases.apply_settings import ApplySettings
from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.apply_taskbar_layout import ApplyTaskbarLayout
from skhu_pc_management.application.use_cases.check_settings_status import CheckSettingsStatus
from skhu_pc_management.application.use_cases.list_network_adapters import ListNetworkAdapters
from skhu_pc_management.application.use_cases.launch_program import LaunchProgram
from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo
from skhu_pc_management.application.use_cases.rename_pc import RenamePc
from skhu_pc_management.application.use_cases.run_pc_maintenance import RunPcMaintenance
from skhu_pc_management.application.use_cases.run_pc_checks import (
    AutoShutdownScheduleCheck,
    BrowserHistoryCheck,
    OfficeInstallCheck,
    PowerSettingsCheck,
    ProgramVersionCheck,
    RecycleBinCheck,
    RunPcChecks,
)
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
from skhu_pc_management.application.use_cases.system_settings_actions import SystemSettingsActions
from skhu_pc_management.application.use_cases.validate_taskbar_resources import ValidateTaskbarResources
from skhu_pc_management.infrastructure.license.embedded_product_key_provider import EmbeddedProductKeyProvider
from skhu_pc_management.infrastructure.windows.browser_data_reader import WindowsBrowserDataReader
from skhu_pc_management.infrastructure.windows.installed_program_reader import WindowsInstalledProgramReader
from skhu_pc_management.infrastructure.windows.latest_version_provider import WindowsLatestVersionProvider
from skhu_pc_management.infrastructure.windows.netsh_network_configurator import NetshNetworkConfigurator
from skhu_pc_management.infrastructure.windows.power_settings_reader import WindowsPowerSettingsReader
from skhu_pc_management.infrastructure.windows.pyinstaller_resource_resolver import PyInstallerResourceResolver
from skhu_pc_management.infrastructure.windows.recycle_bin_reader import WindowsRecycleBinReader
from skhu_pc_management.infrastructure.windows.subprocess_command_runner import SubprocessCommandRunner
from skhu_pc_management.infrastructure.windows.windows_admin_privilege_checker import WindowsAdminPrivilegeChecker
from skhu_pc_management.infrastructure.windows.windows_clipboard import WindowsClipboard
from skhu_pc_management.infrastructure.windows.windows_pc_renamer import WindowsPcRenamer
from skhu_pc_management.infrastructure.windows.windows_program_launcher import WindowsProgramLauncher
from skhu_pc_management.infrastructure.windows.windows_process_launcher import WindowsProcessLauncher
from skhu_pc_management.infrastructure.windows.windows_scheduled_task_reader import WindowsScheduledTaskReader
from skhu_pc_management.infrastructure.windows.windows_system_maintenance import WindowsSystemMaintenance
from skhu_pc_management.infrastructure.windows.windows_system_settings_operator import WindowsSystemSettingsOperator
from skhu_pc_management.infrastructure.windows.windows_taskbar_configurator import WindowsTaskbarConfigurator
from skhu_pc_management.infrastructure.windows.winreg_registry import WinregRegistry
from skhu_pc_management.infrastructure.windows.wmi_pc_info_reader import WmiPcInfoReader
from skhu_pc_management.presentation.qt.main_window import MainWindow
from skhu_pc_management.presentation.qt.startup_coordinator import StartupCoordinator
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


def create_main_window() -> MainWindow:
    test_mode = os.environ.get("SKHU_PC_MANAGEMENT_TEST_MODE") == "1"
    safety_guard = SafetyGuard(test_mode=test_mode)

    registry = WinregRegistry()
    command_runner = SubprocessCommandRunner()
    process_launcher = WindowsProcessLauncher()
    clipboard = WindowsClipboard()
    product_key_provider = EmbeddedProductKeyProvider()
    resource_resolver = PyInstallerResourceResolver()

    network_configurator = NetshNetworkConfigurator(command_runner)
    taskbar_configurator = WindowsTaskbarConfigurator(resource_resolver, command_runner)
    pc_renamer = WindowsPcRenamer(command_runner)
    program_launcher = WindowsProgramLauncher(registry, process_launcher)
    system_maintenance = WindowsSystemMaintenance(command_runner)
    system_settings_operator = WindowsSystemSettingsOperator(registry, command_runner)
    installed_program_reader = WindowsInstalledProgramReader(registry)
    latest_version_provider = WindowsLatestVersionProvider()
    browser_data_reader = WindowsBrowserDataReader()
    power_settings_reader = WindowsPowerSettingsReader(command_runner)
    scheduled_task_reader = WindowsScheduledTaskReader(command_runner)
    recycle_bin_reader = WindowsRecycleBinReader()

    load_pc_info = LoadPcInfo(WmiPcInfoReader(registry=registry, command_runner=command_runner))
    check_settings_status = CheckSettingsStatus(registry)
    validate_taskbar_resources = ValidateTaskbarResources(taskbar_configurator)
    apply_taskbar_layout = ApplyTaskbarLayout(taskbar_configurator, safety_guard=safety_guard)
    system_settings_actions = SystemSettingsActions(system_settings_operator, safety_guard=safety_guard)
    apply_settings = ApplySettings(
        registry,
        command_runner,
        safety_guard=safety_guard,
        system_settings_actions=system_settings_actions,
        apply_taskbar_layout_use_case=apply_taskbar_layout,
    )
    list_network_adapters = ListNetworkAdapters(network_configurator)
    apply_static_ip = ApplyStaticIp(network_configurator, safety_guard=safety_guard)
    set_dhcp = SetDhcp(network_configurator, safety_guard=safety_guard)
    rename_pc = RenamePc(pc_renamer, safety_guard=safety_guard)
    launch_program = LaunchProgram(program_launcher, safety_guard=safety_guard)
    run_pc_maintenance = RunPcMaintenance(system_maintenance, safety_guard=safety_guard)
    run_pc_checks = RunPcChecks(
        [
            RecycleBinCheck(recycle_bin_reader),
            ProgramVersionCheck(
                installed_program_reader,
                latest_version_provider,
                "chrome_install",
                "Chrome 설치/버전 확인",
                "chrome",
                "Chrome",
            ),
            BrowserHistoryCheck(browser_data_reader, "chrome_history", "Chrome 기록 확인", "chrome"),
            ProgramVersionCheck(
                installed_program_reader,
                latest_version_provider,
                "edge_install",
                "Edge 설치/버전 확인",
                "edge",
                "Edge",
            ),
            BrowserHistoryCheck(browser_data_reader, "edge_history", "Edge 기록 확인", "edge"),
            PowerSettingsCheck(power_settings_reader),
            AutoShutdownScheduleCheck(scheduled_task_reader),
            ProgramVersionCheck(
                installed_program_reader,
                latest_version_provider,
                "potplayer_install",
                "PotPlayer 설치/버전 확인",
                "potplayer",
                "PotPlayer",
            ),
            ProgramVersionCheck(
                installed_program_reader,
                latest_version_provider,
                "bandizip_install",
                "Bandizip 설치/버전 확인",
                "bandizip",
                "Bandizip",
            ),
            OfficeInstallCheck(installed_program_reader),
        ]
    )
    activate_windows = ActivateWindows(product_key_provider, clipboard, process_launcher, safety_guard=safety_guard)
    activate_office = ActivateOffice(product_key_provider, clipboard, process_launcher, safety_guard=safety_guard)
    pc_info_view_model = PcInfoViewModel(load_pc_info, rename_pc)
    settings_view_model = SettingsViewModel(
        check_settings_status,
        apply_settings,
        validate_taskbar_resources,
        apply_taskbar_layout,
    )
    pc_check_view_model = PcCheckViewModel(run_pc_checks)
    startup_coordinator = StartupCoordinator(
        admin_privilege_checker=WindowsAdminPrivilegeChecker(),
        pc_info_view_model=pc_info_view_model,
        settings_view_model=settings_view_model,
        pc_check_view_model=pc_check_view_model,
    )

    return MainWindow(
        pc_info_view_model=pc_info_view_model,
        settings_view_model=settings_view_model,
        network_view_model=NetworkViewModel(list_network_adapters, apply_static_ip, set_dhcp),
        pc_check_view_model=pc_check_view_model,
        activation_view_model=ActivationViewModel(activate_windows, activate_office),
        launch_program_use_case=launch_program,
        maintenance_use_case=run_pc_maintenance,
        startup_coordinator=startup_coordinator,
        resource_resolver=resource_resolver,
        test_mode=test_mode,
    )
