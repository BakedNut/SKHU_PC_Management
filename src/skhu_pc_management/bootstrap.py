from __future__ import annotations

from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.application.use_cases.apply_settings import ApplySettings
from skhu_pc_management.application.use_cases.apply_static_ip import ApplyStaticIp
from skhu_pc_management.application.use_cases.check_settings_status import CheckSettingsStatus
from skhu_pc_management.application.use_cases.list_network_adapters import ListNetworkAdapters
from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo
from skhu_pc_management.application.use_cases.run_pc_checks import (
    BrowserHistoryCheck,
    InstalledProgramCheck,
    OfficeInstallCheck,
    PowerSettingsCheck,
    RecycleBinCheck,
    RunPcChecks,
)
from skhu_pc_management.application.use_cases.set_dhcp import SetDhcp
from skhu_pc_management.infrastructure.license.embedded_product_key_provider import EmbeddedProductKeyProvider
from skhu_pc_management.infrastructure.windows.browser_data_reader import WindowsBrowserDataReader
from skhu_pc_management.infrastructure.windows.installed_program_reader import WindowsInstalledProgramReader
from skhu_pc_management.infrastructure.windows.netsh_network_configurator import NetshNetworkConfigurator
from skhu_pc_management.infrastructure.windows.power_settings_reader import WindowsPowerSettingsReader
from skhu_pc_management.infrastructure.windows.recycle_bin_reader import WindowsRecycleBinReader
from skhu_pc_management.infrastructure.windows.subprocess_command_runner import SubprocessCommandRunner
from skhu_pc_management.infrastructure.windows.windows_clipboard import WindowsClipboard
from skhu_pc_management.infrastructure.windows.windows_process_launcher import WindowsProcessLauncher
from skhu_pc_management.infrastructure.windows.winreg_registry import WinregRegistry
from skhu_pc_management.infrastructure.windows.wmi_pc_info_reader import WmiPcInfoReader
from skhu_pc_management.presentation.qt.main_window import MainWindow
from skhu_pc_management.presentation.qt.viewmodels.activation_viewmodel import ActivationViewModel
from skhu_pc_management.presentation.qt.viewmodels.network_viewmodel import NetworkViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_check_viewmodel import PcCheckViewModel
from skhu_pc_management.presentation.qt.viewmodels.pc_info_viewmodel import PcInfoViewModel
from skhu_pc_management.presentation.qt.viewmodels.settings_viewmodel import SettingsViewModel


def create_main_window() -> MainWindow:
    registry = WinregRegistry()
    command_runner = SubprocessCommandRunner()
    process_launcher = WindowsProcessLauncher()
    clipboard = WindowsClipboard()
    product_key_provider = EmbeddedProductKeyProvider()

    network_configurator = NetshNetworkConfigurator(command_runner)
    installed_program_reader = WindowsInstalledProgramReader(registry)
    browser_data_reader = WindowsBrowserDataReader()
    power_settings_reader = WindowsPowerSettingsReader(command_runner)
    recycle_bin_reader = WindowsRecycleBinReader()

    load_pc_info = LoadPcInfo(WmiPcInfoReader(registry=registry, command_runner=command_runner))
    check_settings_status = CheckSettingsStatus(registry)
    apply_settings = ApplySettings(registry, command_runner)
    list_network_adapters = ListNetworkAdapters(network_configurator)
    apply_static_ip = ApplyStaticIp(network_configurator)
    set_dhcp = SetDhcp(network_configurator)
    run_pc_checks = RunPcChecks(
        [
            RecycleBinCheck(recycle_bin_reader),
            InstalledProgramCheck(installed_program_reader, "chrome_install", "Chrome 설치/버전 확인", "chrome"),
            BrowserHistoryCheck(browser_data_reader, "chrome_history", "Chrome 기록 확인", "chrome"),
            InstalledProgramCheck(installed_program_reader, "edge_install", "Edge 설치/버전 확인", "edge"),
            BrowserHistoryCheck(browser_data_reader, "edge_history", "Edge 기록 확인", "edge"),
            PowerSettingsCheck(power_settings_reader),
            InstalledProgramCheck(installed_program_reader, "potplayer_install", "PotPlayer 설치/버전 확인", "potplayer"),
            InstalledProgramCheck(installed_program_reader, "bandizip_install", "Bandizip 설치/버전 확인", "bandizip"),
            OfficeInstallCheck(installed_program_reader),
        ]
    )
    activate_windows = ActivateWindows(product_key_provider, clipboard, process_launcher)
    activate_office = ActivateOffice(product_key_provider, clipboard, process_launcher)

    return MainWindow(
        pc_info_view_model=PcInfoViewModel(load_pc_info),
        settings_view_model=SettingsViewModel(check_settings_status, apply_settings),
        network_view_model=NetworkViewModel(list_network_adapters, apply_static_ip, set_dhcp),
        pc_check_view_model=PcCheckViewModel(run_pc_checks),
        activation_view_model=ActivationViewModel(activate_windows, activate_office),
    )
