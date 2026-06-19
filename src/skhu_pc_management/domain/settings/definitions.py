from __future__ import annotations

from dataclasses import dataclass, field


HKCU = "HKEY_CURRENT_USER"
HKLM = "HKEY_LOCAL_MACHINE"
REG_DWORD = "REG_DWORD"
REG_STRING = "REG_SZ"

UPDATE_USER_PARAMETERS_COMMAND = ("RUNDLL32.EXE", "user32.dll,UpdatePerUserSystemParameters")
DISABLE_PASSWORD_EXPIRATION_COMMAND = ("net", "accounts", "/maxpwage:unlimited")
STOP_EXPLORER_COMMAND = ("taskkill", "/F", "/IM", "explorer.exe")
START_EXPLORER_COMMAND = ("explorer.exe",)


@dataclass(frozen=True)
class RegistrySettingDefinition:
    setting_id: str
    name: str
    root: str
    path: str
    value_name: str
    expected_value: object
    value_type: str


@dataclass(frozen=True)
class SettingDefinition:
    setting_id: str
    name: str
    registry_values: tuple[RegistrySettingDefinition, ...] = field(default_factory=tuple)
    post_commands: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    requires_user_parameter_update: bool = True
    requires_explorer_restart: bool = False


def _registry(
    setting_id: str,
    name: str,
    root: str,
    path: str,
    value_name: str,
    expected_value: object,
    value_type: str = REG_DWORD,
) -> RegistrySettingDefinition:
    return RegistrySettingDefinition(
        setting_id=setting_id,
        name=name,
        root=root,
        path=path,
        value_name=value_name,
        expected_value=expected_value,
        value_type=value_type,
    )


DEFAULT_SETTING_DEFINITIONS: tuple[SettingDefinition, ...] = (
    SettingDefinition(
        setting_id="hide_frequent_folders",
        name="자주 사용하는 폴더 숨김",
        registry_values=(
            _registry(
                "hide_frequent_folders",
                "자주 사용하는 폴더 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer",
                "ShowFrequent",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="hide_recent_files",
        name="최근 사용한 항목 숨김",
        registry_values=(
            _registry(
                "hide_recent_files",
                "최근 사용 항목 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer",
                "ShowRecent",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="explorer_launch_to_this_pc",
        name="탐색기 실행 시 '내 PC'로",
        registry_values=(
            _registry(
                "explorer_launch_to_this_pc",
                "탐색기 시작 위치를 내 PC로 설정",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "LaunchTo",
                1,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="show_file_extensions",
        name="파일 확장자 표시",
        registry_values=(
            _registry(
                "show_file_extensions",
                "파일 확장자 표시",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "HideFileExt",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="disable_item_checkboxes",
        name="파일 선택 확인란 비활성화",
        registry_values=(
            _registry(
                "disable_item_checkboxes",
                "파일 선택 확인란 비활성화",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "AutoCheckSelect",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="show_this_pc_on_desktop",
        name="바탕화면 '내 PC' 아이콘 표시",
        registry_values=(
            _registry(
                "show_this_pc_on_desktop",
                "바탕화면 내 PC 표시",
                HKCU,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
                "{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="show_control_panel_on_desktop",
        name="바탕화면 '제어판' 아이콘 표시",
        registry_values=(
            _registry(
                "show_control_panel_on_desktop",
                "바탕화면 제어판 표시",
                HKCU,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
                "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="enable_passwordless_signin",
        name="부팅 시 암호 입력 생략 설정 활성화",
        registry_values=(
            _registry(
                "enable_passwordless_signin",
                "부팅 시 암호 입력 생략",
                HKLM,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device",
                "DevicePasswordLessBuildVersion",
                0,
            ),
        ),
    ),
    SettingDefinition(
        setting_id="disable_fast_startup",
        name="빠른 시작 켜기 비활성화",
        registry_values=(
            _registry(
                "disable_fast_startup",
                "빠른 시작 비활성화",
                HKLM,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                "HiberbootEnabled",
                0,
            ),
        ),
        requires_user_parameter_update=False,
    ),
    SettingDefinition(
        setting_id="delete_edge_shortcut",
        name="바탕화면 Edge 바로가기 삭제",
        registry_values=(
            _registry(
                "disable_edge_desktop_shortcut_policy",
                "Edge 바로가기 생성 정책 비활성화",
                HKLM,
                r"SOFTWARE\Policies\Microsoft\EdgeUpdate",
                "CreateDesktopShortcutDefault",
                0,
            ),
        ),
        requires_user_parameter_update=False,
    ),
    SettingDefinition(
        setting_id="hide_task_view_button",
        name="작업 보기 버튼 숨김",
        registry_values=(
            _registry(
                "hide_task_view_button",
                "작업 보기 버튼 숨김",
                HKCU,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "ShowTaskViewButton",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="show_search_icon",
        name="검색 아이콘만 표시",
        registry_values=(
            _registry(
                "show_search_icon",
                "검색 아이콘만 표시",
                HKCU,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
                "SearchboxTaskbarMode",
                1,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_start_more_pins",
        name="시작 메뉴: 고정된 항목 더 보기",
        registry_values=(
            _registry(
                "win11_start_more_pins",
                "Win11 시작 메뉴: 고정된 항목 더 보기",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "Start_Layout",
                1,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_hide_recent_apps",
        name="시작 메뉴: 최근 추가 앱 숨김",
        registry_values=(
            _registry(
                "win11_hide_recent_apps",
                "Win11 시작 메뉴: 최근 추가 앱 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Start",
                "ShowRecentList",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_hide_frequent_apps",
        name="시작 메뉴: 자주 사용 앱 숨김",
        registry_values=(
            _registry(
                "win11_hide_frequent_apps",
                "Win11 시작 메뉴: 자주 사용 앱 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Start",
                "ShowFrequentList",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_hide_recommended_files",
        name="시작 메뉴: 추천 파일 숨김",
        registry_values=(
            _registry(
                "win11_hide_recommended_files",
                "Win11 시작 메뉴: 추천 파일 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "Start_TrackDocs",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_hide_iris_recommendations",
        name="시작 메뉴: 팁/권장 사항 숨김",
        registry_values=(
            _registry(
                "win11_hide_iris_recommendations",
                "Win11 시작 메뉴: 팁/권장 사항 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "Start_IrisRecommendations",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="win11_hide_account_notifications",
        name="시작 메뉴: 계정 알림 숨김",
        registry_values=(
            _registry(
                "win11_hide_account_notifications",
                "Win11 시작 메뉴: 계정 알림 숨김",
                HKCU,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "Start_AccountNotifications",
                0,
            ),
        ),
        requires_explorer_restart=True,
    ),
    SettingDefinition(
        setting_id="disable_password_expiration",
        name="사용자 계정 암호 만료 비활성화",
        post_commands=(DISABLE_PASSWORD_EXPIRATION_COMMAND,),
        requires_user_parameter_update=False,
    ),
    SettingDefinition(
        setting_id="set_default_wallpaper",
        name="기본 배경화면 설정",
        requires_user_parameter_update=False,
    ),
    SettingDefinition(
        setting_id="set_taskbar_icons",
        name="작업표시줄 아이콘 설정",
        requires_user_parameter_update=False,
        requires_explorer_restart=True,
    ),
)


DEFAULT_SETTING_DEFINITIONS_BY_ID = {
    definition.setting_id: definition for definition in DEFAULT_SETTING_DEFINITIONS
}
