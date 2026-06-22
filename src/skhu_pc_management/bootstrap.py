from __future__ import annotations

import os
from dataclasses import dataclass

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
from skhu_pc_management.infrastructure.windows.auto_shutdown_cancel_shortcut import WindowsAutoShutdownCancelShortcut
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
from skhu_pc_management.infrastructure.windows.windows_process_launcher import WindowsProcessLauncher
from skhu_pc_management.infrastructure.windows.windows_program_launcher import WindowsProgramLauncher
from skhu_pc_management.infrastructure.windows.windows_scheduled_task_reader import WindowsScheduledTaskReader
from skhu_pc_management.infrastructure.windows.windows_setting_status_providers import (
    DefaultWallpaperStatusProvider,
    EdgeShortcutStatusProvider,
    PasswordExpirationStatusProvider,
    TaskbarLayoutStatusProvider,
)
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


@dataclass(frozen=True)
class InfrastructureContainer:
    registry: WinregRegistry
    command_runner: SubprocessCommandRunner
    process_launcher: WindowsProcessLauncher
    clipboard: WindowsClipboard
    product_key_provider: EmbeddedProductKeyProvider
    resource_resolver: PyInstallerResourceResolver
    network_configurator: NetshNetworkConfigurator
    taskbar_configurator: WindowsTaskbarConfigurator
    pc_renamer: WindowsPcRenamer
    program_launcher: WindowsProgramLauncher
    system_maintenance: WindowsSystemMaintenance
    system_settings_operator: WindowsSystemSettingsOperator
    installed_program_reader: WindowsInstalledProgramReader
    latest_version_provider: WindowsLatestVersionProvider
    browser_data_reader: WindowsBrowserDataReader
    auto_shutdown_cancel_shortcut: WindowsAutoShutdownCancelShortcut
    power_settings_reader: WindowsPowerSettingsReader
    scheduled_task_reader: WindowsScheduledTaskReader
    recycle_bin_reader: WindowsRecycleBinReader
    admin_privilege_checker: WindowsAdminPrivilegeChecker


@dataclass(frozen=True)
class UseCaseContainer:
    load_pc_info: LoadPcInfo
    check_settings_status: CheckSettingsStatus
    validate_taskbar_resources: ValidateTaskbarResources
    apply_taskbar_layout: ApplyTaskbarLayout
    system_settings_actions: SystemSettingsActions
    apply_settings: ApplySettings
    list_network_adapters: ListNetworkAdapters
    apply_static_ip: ApplyStaticIp
    set_dhcp: SetDhcp
    rename_pc: RenamePc
    launch_program: LaunchProgram
    run_pc_maintenance: RunPcMaintenance
    run_pc_checks: RunPcChecks
    activate_windows: ActivateWindows
    activate_office: ActivateOffice


@dataclass(frozen=True)
class ViewModelContainer:
    pc_info: PcInfoViewModel
    settings: SettingsViewModel
    network: NetworkViewModel
    pc_check: PcCheckViewModel
    activation: ActivationViewModel


def is_test_mode_enabled() -> bool:
    return os.environ.get("SKHU_PC_MANAGEMENT_TEST_MODE") == "1"


def create_safety_guard(test_mode: bool | None = None) -> SafetyGuard:
    enabled_test_mode = is_test_mode_enabled() if test_mode is None else test_mode
    return SafetyGuard(
        test_mode=enabled_test_mode,
        allow_real_taskbar_apply=not enabled_test_mode,
    )


def create_infrastructure() -> InfrastructureContainer:
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
    auto_shutdown_cancel_shortcut = WindowsAutoShutdownCancelShortcut(resource_resolver)
    system_maintenance = WindowsSystemMaintenance(command_runner, auto_shutdown_cancel_shortcut)
    system_settings_operator = WindowsSystemSettingsOperator(registry, command_runner)
    installed_program_reader = WindowsInstalledProgramReader(registry)

    return InfrastructureContainer(
        registry=registry,
        command_runner=command_runner,
        process_launcher=process_launcher,
        clipboard=clipboard,
        product_key_provider=product_key_provider,
        resource_resolver=resource_resolver,
        network_configurator=network_configurator,
        taskbar_configurator=taskbar_configurator,
        pc_renamer=pc_renamer,
        program_launcher=program_launcher,
        system_maintenance=system_maintenance,
        system_settings_operator=system_settings_operator,
        installed_program_reader=installed_program_reader,
        latest_version_provider=WindowsLatestVersionProvider(),
        browser_data_reader=WindowsBrowserDataReader(),
        auto_shutdown_cancel_shortcut=auto_shutdown_cancel_shortcut,
        power_settings_reader=WindowsPowerSettingsReader(command_runner),
        scheduled_task_reader=WindowsScheduledTaskReader(command_runner),
        recycle_bin_reader=WindowsRecycleBinReader(),
        admin_privilege_checker=WindowsAdminPrivilegeChecker(),
    )


def create_use_cases(infra: InfrastructureContainer, safety_guard: SafetyGuard) -> UseCaseContainer:
    setting_status_providers = {
        "set_default_wallpaper": DefaultWallpaperStatusProvider(infra.registry),
        "delete_edge_shortcut": EdgeShortcutStatusProvider(infra.registry),
        "set_taskbar_icons": TaskbarLayoutStatusProvider(infra.resource_resolver),
        "disable_password_expiration": PasswordExpirationStatusProvider(infra.command_runner),
    }
    check_settings_status = CheckSettingsStatus(
        infra.registry,
        setting_status_providers=setting_status_providers,
    )
    apply_taskbar_layout = ApplyTaskbarLayout(infra.taskbar_configurator, safety_guard=safety_guard)
    system_settings_actions = SystemSettingsActions(infra.system_settings_operator, safety_guard=safety_guard)

    return UseCaseContainer(
        load_pc_info=LoadPcInfo(WmiPcInfoReader(registry=infra.registry, command_runner=infra.command_runner)),
        check_settings_status=check_settings_status,
        validate_taskbar_resources=ValidateTaskbarResources(infra.taskbar_configurator),
        apply_taskbar_layout=apply_taskbar_layout,
        system_settings_actions=system_settings_actions,
        apply_settings=ApplySettings(
            infra.registry,
            infra.command_runner,
            safety_guard=safety_guard,
            system_settings_actions=system_settings_actions,
            apply_taskbar_layout_use_case=apply_taskbar_layout,
        ),
        list_network_adapters=ListNetworkAdapters(infra.network_configurator),
        apply_static_ip=ApplyStaticIp(infra.network_configurator, safety_guard=safety_guard),
        set_dhcp=SetDhcp(infra.network_configurator, safety_guard=safety_guard),
        rename_pc=RenamePc(infra.pc_renamer, safety_guard=safety_guard),
        launch_program=LaunchProgram(infra.program_launcher, safety_guard=safety_guard),
        run_pc_maintenance=RunPcMaintenance(infra.system_maintenance, safety_guard=safety_guard),
        run_pc_checks=RunPcChecks(_create_pc_checks(infra)),
        activate_windows=ActivateWindows(
            infra.product_key_provider,
            infra.clipboard,
            infra.process_launcher,
            safety_guard=safety_guard,
        ),
        activate_office=ActivateOffice(
            infra.product_key_provider,
            infra.clipboard,
            infra.process_launcher,
            safety_guard=safety_guard,
        ),
    )


def create_view_models(use_cases: UseCaseContainer) -> ViewModelContainer:
    return ViewModelContainer(
        pc_info=PcInfoViewModel(use_cases.load_pc_info, use_cases.rename_pc),
        settings=SettingsViewModel(
            use_cases.check_settings_status,
            use_cases.apply_settings,
            use_cases.validate_taskbar_resources,
            use_cases.apply_taskbar_layout,
        ),
        network=NetworkViewModel(
            use_cases.list_network_adapters,
            use_cases.apply_static_ip,
            use_cases.set_dhcp,
        ),
        pc_check=PcCheckViewModel(use_cases.run_pc_checks),
        activation=ActivationViewModel(use_cases.activate_windows, use_cases.activate_office),
    )


def create_startup_coordinator(infra: InfrastructureContainer, view_models: ViewModelContainer) -> StartupCoordinator:
    return StartupCoordinator(
        admin_privilege_checker=infra.admin_privilege_checker,
        pc_info_view_model=view_models.pc_info,
        settings_view_model=view_models.settings,
        pc_check_view_model=view_models.pc_check,
    )


def create_main_window() -> MainWindow:
    test_mode = is_test_mode_enabled()
    safety_guard = create_safety_guard(test_mode)
    infra = create_infrastructure()
    use_cases = create_use_cases(infra, safety_guard)
    view_models = create_view_models(use_cases)
    startup_coordinator = create_startup_coordinator(infra, view_models)

    return MainWindow(
        pc_info_view_model=view_models.pc_info,
        settings_view_model=view_models.settings,
        network_view_model=view_models.network,
        pc_check_view_model=view_models.pc_check,
        activation_view_model=view_models.activation,
        launch_program_use_case=use_cases.launch_program,
        maintenance_use_case=use_cases.run_pc_maintenance,
        startup_coordinator=startup_coordinator,
        resource_resolver=infra.resource_resolver,
        test_mode=test_mode,
    )


def _create_pc_checks(infra: InfrastructureContainer) -> list[object]:
    return [
        RecycleBinCheck(infra.recycle_bin_reader),
        ProgramVersionCheck(
            infra.installed_program_reader,
            infra.latest_version_provider,
            "chrome_install",
            "Chrome 설치/버전 확인",
            "chrome",
            "Chrome",
        ),
        BrowserHistoryCheck(infra.browser_data_reader, "chrome_history", "Chrome 기록 확인", "chrome"),
        ProgramVersionCheck(
            infra.installed_program_reader,
            infra.latest_version_provider,
            "edge_install",
            "Edge 설치/버전 확인",
            "edge",
            "Edge",
        ),
        BrowserHistoryCheck(infra.browser_data_reader, "edge_history", "Edge 기록 확인", "edge"),
        PowerSettingsCheck(infra.power_settings_reader),
        AutoShutdownScheduleCheck(infra.scheduled_task_reader, infra.auto_shutdown_cancel_shortcut),
        ProgramVersionCheck(
            infra.installed_program_reader,
            infra.latest_version_provider,
            "potplayer_install",
            "PotPlayer 설치/버전 확인",
            "potplayer",
            "PotPlayer",
        ),
        ProgramVersionCheck(
            infra.installed_program_reader,
            infra.latest_version_provider,
            "bandizip_install",
            "Bandizip 설치/버전 확인",
            "bandizip",
            "Bandizip",
        ),
        OfficeInstallCheck(infra.installed_program_reader),
    ]
