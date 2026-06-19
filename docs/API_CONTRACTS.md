# API Contracts

## 1. 계층 규칙

| 계층 | 역할 | 허용 의존성 | 금지/주의 |
| --- | --- | --- | --- |
| `domain` | dataclass 모델, enum-like 상수, 순수 검증 | 표준 라이브러리, typing | PySide6, winreg, subprocess, WMI, netsh, powercfg 직접 의존 금지 |
| `application` | use case orchestration, SafetyGuard, port 호출 | domain, ports | Windows API/명령 직접 호출 금지. PySide6 import 금지 |
| `ports` | 외부 시스템 계약 `Protocol` | domain model, typing | 구현 세부사항 금지 |
| `infrastructure` | Windows adapter, license adapter | winreg, subprocess, ctypes, PowerShell/netsh/powercfg 등 필요 시 사용 가능 | 단위 테스트에서는 fake로 대체 |
| `presentation` | PySide6 UI, ViewModel, 사용자 확인 dialog | PySide6, application use case | 비즈니스 로직/Windows 직접 호출을 넣지 않는다 |

Windows 동작은 반드시 `ports` + `infrastructure/windows` adapter를 통해 처리한다. GUI는 얇게 유지하고, ViewModel은 use case 호출과 표시 상태 변환에 집중한다.

## 2. 공통 결과 모델

| 모델 | 파일 | 필드 | 성공/실패 판단 | UI 표시 |
| --- | --- | --- | --- | --- |
| `ApplyResult` | `domain/settings/models.py` | `name`, `success`, `message`, `setting_id`, `status` | `success`; `status`는 `applied/failed/skipped` | 설정/유지보수 결과 행 |
| `ApplySettingsResult` | `domain/settings/models.py` | `results` | `is_success`, `success_count`, `failure_count`, `skipped_count` | 설정 적용 요약 |
| `SettingStatus` | `domain/settings/models.py` | `setting_id`, `label`, `expected_value`, `actual_value`, `is_configured`, `severity`, `status_text`, `name`, `is_applied`, `current_value`, `detail` | `is_configured`와 `status_text` | 설정 상태표의 현재 상태/상세 |
| `CheckResult` | `domain/checks/models.py` | `check_id`, `label`, `category`, `status`, `message`, `detail`, `raw_value`, `name`, `passed` | `status == ok` 또는 `passed` | PC 점검 표 |
| `NetworkConfigResult` | `domain/network/models.py` | `operation`, `success`, `adapter_name`, `message`, `commands` | `success` | 네트워크 적용 결과 메시지 |
| `ActivationResult` | `domain/activation/models.py` | `success`, `action`, `message`, `launched_process`, `copied_to_clipboard`, `error` | `success` | 인증 탭 결과. 제품키 값 표시 금지 |
| `ResourceValidationResult` | `domain/resources/models.py` | `success`, `message`, `resources_root`, `reg_file`, `taskbar_dir`, `shortcut_files`, `warnings` | `success` | 작업표시줄 리소스 검증 |
| `TaskbarApplyResult` | `domain/resources/models.py` | `success`, `message`, `dry_run`, `reg_file`, `shortcut_files`, `planned_actions` | `success` | 작업표시줄 dry-run/적용 결과 |
| `StaticIpConfig` | `domain/network/models.py` | `adapter_name`, `ip_address`, `subnet_mask`, `gateway`, `dns1`, `dns2`, `dns_servers` | 생성 시 IP 검증 성공 | 네트워크 use case 입력 |
| `NetworkAdapterInfo` | `domain/network/models.py` | `name`, `description`, `is_enabled`, `mac_address`, `ip_addresses`, `subnet_mask`, `gateway`, `dns_servers`, `is_dhcp_enabled` | 읽기 모델 | 네트워크 adapter list/current table |
| `PcInfo` | `domain/pc/models.py` | `computer_name`, `user_name`, OS/CPU/RAM/GPU/disk/security fields | 읽기 모델 | PC 정보 화면 |
| `DiskInfo` | `domain/pc/models.py` | `model`, `size_gb`, `actual_size_gib`, `rated_size`, `disk_type`, `bus_type`, `display_type`, `serial_number`, `raw_size_bytes` | 읽기 모델 | 디스크 표 |

## 3. Use Case 계약

| Use case | 파일 | 입력 | 출력 | side effect | 위험도 | SafetyGuard/test mode | 실패 처리 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `LoadPcInfo` | `application/use_cases/load_pc_info.py` | 없음 | `PcInfo` | 읽기 | 낮음 | 해당 없음 | reader 예외는 ViewModel에서 메시지화 |
| `RenamePc` | `application/use_cases/rename_pc.py` | `new_name` | `ApplyResult` 유사 결과 | PC 이름 변경 | 높음 | 차단 | 실패 메시지 반환 |
| `ApplySettings` | `application/use_cases/apply_settings.py` | setting id iterable | `ApplySettingsResult` | registry write, command, action use case | 높음 | 차단 시 각 항목 `skipped` | 항목별 실패 결과 |
| `CheckSettingsStatus` | `application/use_cases/check_settings_status.py` | setting id iterable | `list[SettingStatus]` | 읽기 | 낮음 | 허용 | missing/read_failed/provider_missing 표현 |
| `ApplyTaskbarLayout` | `application/use_cases/apply_taskbar_layout.py` | `dry_run=True/False` | `TaskbarApplyResult` | dry-run 또는 작업표시줄 적용 | 매우 높음 | test mode 차단, real apply 기본 차단 | 차단 메시지 결과 |
| `ValidateTaskbarResources` | `application/use_cases/validate_taskbar_resources.py` | 없음 | `ResourceValidationResult` | 읽기 | 낮음 | 허용 | configurator 결과 |
| `ActivateWindows` | `application/use_cases/activate_windows.py` | edition optional | `ActivationResult` | clipboard, `slui.exe` 실행 | 민감 | 차단 | 제품키 없음/실행 실패 메시지 |
| `ActivateOffice` | `application/use_cases/activate_office.py` | version optional | `ActivationResult` | clipboard, `excel.exe` 실행 | 민감 | 차단 | 제품키 없음/실행 실패 메시지 |
| `ListNetworkAdapters` | `application/use_cases/list_network_adapters.py` | 없음 | `list[NetworkAdapterInfo]` | 읽기 | 낮음 | 허용 | adapter 예외는 ViewModel에서 처리 |
| `ApplyStaticIp` | `application/use_cases/apply_static_ip.py` | `StaticIpConfig` | `NetworkConfigResult` | netsh adapter 호출 | 높음 | 차단 | 실패 결과 반환 |
| `SetDhcp` | `application/use_cases/set_dhcp.py` | adapter name | `NetworkConfigResult` | netsh adapter 호출 | 높음 | 차단 | 실패 결과 반환 |
| `RunPcChecks` | `application/use_cases/run_pc_checks.py` | 없음 | `list[CheckResult]` | 읽기 | 낮음 | 허용 | 개별 check 실패가 전체 중단되지 않도록 error/unknown 결과 |
| `RunPcMaintenance` | `application/use_cases/run_pc_maintenance.py` | method별 action | `ApplyResult` | 삭제/전원/스케줄 변경 | 높음 | 차단 | 실패 결과 반환 |
| `LaunchProgram` | `application/use_cases/launch_program.py` | program id | `ApplyResult` | 프로그램 실행 | 낮음~중간 | 차단 | 실패 결과 반환 |
| `SystemSettingsActions` | `application/use_cases/system_settings_actions.py` | action id, label | `ApplyResult` | 배경화면/Edge shortcut/password expiration | 중간~높음 | 차단 | 실패 결과 반환 |

## 4. Ports 계약

| Port | 목적 | 메서드 | 반환값 | 구현체 예 | Windows side effect |
| --- | --- | --- | --- | --- | --- |
| `Registry` | 레지스트리 읽기/쓰기 | `read_value`, `list_subkeys`, `write_value` | object/list/None | `WinregRegistry` | 쓰기 시 있음 |
| `CommandRunner` | 외부 명령 실행 | `run(command)` | stdout string | `SubprocessCommandRunner` | 명령에 따라 있음 |
| `NetworkConfigurator` | 어댑터 조회/IP 변경 | `list_adapters`, `apply_static_ip`, `set_dhcp` | network models | `NetshNetworkConfigurator` | IP/DHCP 변경 |
| `ProcessLauncher` | 프로세스 실행 | `launch(executable, args)` | None | `WindowsProcessLauncher` | 있음 |
| `ProductKeyProvider` | 제품키 공급 | `get_windows_product_key`, `get_office_product_key` | str 또는 None | `EmbeddedProductKeyProvider` | 없음. 민감값 취급 |
| `Clipboard` | 클립보드 복사 | `set_text` | None | `WindowsClipboard` | 클립보드 변경 |
| `ResourceResolver` | resources 경로 resolve | `resolve`, `resources_root` | `Path` | `PyInstallerResourceResolver` | 없음 |
| `SystemMaintenance` | 유지보수 변경 작업 | `empty_recycle_bin`, `delete_browser_history`, `set_power_never`, `set_auto_shutdown_at_23` | code/bool/str | `WindowsSystemMaintenance` | 삭제/설정 변경 |
| `PcRenamer` | PC 이름 변경 | `rename` | bool | `WindowsPcRenamer` | 있음 |
| `ProgramLauncher` | 알려진 프로그램 실행 | `launch_program` | bool | `WindowsProgramLauncher` | 있음 |
| `CheckProvider` | 개별 PC 점검 | `run` | `CheckResult` | use case check classes | 보통 읽기 |
| `SettingStatusProvider` | action-only 설정 상태 확인 | `check(setting_id)` | `SettingStatus` | `WindowsSettingStatusProviders` | 읽기 |
| `AdminPrivilegeChecker` | 관리자 권한 확인 | `is_running_as_admin` | bool | `WindowsAdminPrivilegeChecker` | 없음 |
| `InstalledProgramReader` | 설치 프로그램 조회 | `get_program`, `get_installed_office_name` | program info/str/None | `WindowsInstalledProgramReader` | 읽기 |
| `LatestVersionProvider` | 최신 버전 조회 | `get_latest_version` | str/None | `WindowsLatestVersionProvider` | 네트워크 가능성. 확인 필요 |
| `BrowserDataReader` | 브라우저 사용자 데이터 상태 조회 | `get_browser_data_status` | `BrowserDataStatus` | `WindowsBrowserDataReader` | 읽기 |
| `PowerSettingsReader` | 전원 설정 조회 | `read_status` | `PowerSettingsStatus` | `WindowsPowerSettingsReader` | 읽기 |
| `RecycleBinReader` | 휴지통 상태 조회 | `read_status` | `RecycleBinStatus` | `WindowsRecycleBinReader` | 읽기 |
| `ScheduledTaskReader` | 예약 작업 조회 | `get_task` | `ScheduledTaskInfo` | `WindowsScheduledTaskReader` | 읽기 |
| `TaskbarConfigurator` | 작업표시줄 리소스 검증/적용 | `validate_resources`, `apply_taskbar_layout` | resource models | `WindowsTaskbarConfigurator` | real apply 시 있음 |
| `SystemSettingsOperator` | 특수 시스템 설정 변경 | `set_default_wallpaper`, `delete_edge_shortcuts`, `disable_password_expiration_for_all_users` | None | `WindowsSystemSettingsOperator` | 있음 |

## 5. Infrastructure Adapter 계약

| Adapter | 구현 port | 실제 Windows API/명령 | 관리자 권한 | 실패 처리 | 단위 테스트 |
| --- | --- | --- | --- | --- | --- |
| `WinregRegistry` | `Registry` | winreg | HKLM 쓰기/일부 읽기 필요 | missing은 None 반환, 권한 문제는 예외 유지 | fake 사용 |
| `SubprocessCommandRunner` | `CommandRunner` | subprocess | 명령별 | 예외/출력 | fake 사용 |
| `WmiPcInfoReader` | `PcInfoReader` | WMI, registry/command fallback | 일부 필요 가능 | Unknown/None fallback 목표 | fake/private helper |
| `NetshNetworkConfigurator` | `NetworkConfigurator` | PowerShell JSON, netsh fallback | IP 변경 시 필요 | 실패 시 fallback 또는 result | fake command runner |
| `WindowsTaskbarConfigurator` | `TaskbarConfigurator` | 파일/레지스트리/Explorer 관련 계획 | real apply 시 필요 | validation warning/result | fake resolver/runner |
| `WindowsSystemMaintenance` | `SystemMaintenance` | shell/PowerShell/file delete/powercfg/scheduled tasks | 작업별 | bool/str/예외 | fake 사용 |
| `WindowsSystemSettingsOperator` | `SystemSettingsOperator` | registry/command/file | 작업별 | 예외 | fake 사용 |
| `WindowsInstalledProgramReader` | `InstalledProgramReader` | registry | 읽기 | missing은 None | fake registry |
| `WindowsBrowserDataReader` | `BrowserDataReader` | filesystem | 아니오 | 접근 실패 무시/unknown | tmp_path |
| `WindowsPowerSettingsReader` | `PowerSettingsReader` | powercfg via CommandRunner | 아니오/상황별 | parse 실패 unknown | fake command runner |
| `WindowsScheduledTaskReader` | `ScheduledTaskReader` | PowerShell ScheduledTasks via CommandRunner | 읽기 권한 | exists false/unknown | fake command runner |
| `WindowsClipboard` | `Clipboard` | ctypes Win32 clipboard | 아니오 | 예외 | 실제 호출 금지 |
| `WindowsProcessLauncher` | `ProcessLauncher` | process launch | 실행 대상별 | 예외 | fake 사용 |
| `WindowsAdminPrivilegeChecker` | `AdminPrivilegeChecker` | Windows 권한 API | 아니오 | bool | fake 사용 |
| `PyInstallerResourceResolver` | `ResourceResolver` | sys._MEIPASS/path | 아니오 | 명확한 path 예외 | monkeypatch |

## 6. ViewModel 계약

| ViewModel | 입력 use case | public state | public method | UI 호출 방식 | busy/status |
| --- | --- | --- | --- | --- | --- |
| `PcInfoViewModel` | `LoadPcInfo`, optional `RenamePc` | `rows`, `pc_name`, `windows_version`, `cpu`, `ram`, `gpu`, `disks`, security texts, `status_message` | `refresh`, `rename_pc`, `auto_rename_pc` | PC 정보 패널 버튼/startup | local `is_busy`, status message |
| `SettingsViewModel` | `CheckSettingsStatus`, `ApplySettings`, optional taskbar use cases | `definitions`, `result_rows`, `summary_text`, `warning_count`, `status_message` | `all_setting_ids`, `check_status`, `apply_selected`, `validate_taskbar_resources`, `apply_taskbar_layout` | 작업 센터 설정/리소스 영역 | local `is_busy`; 적용 후 상태 재검증 |
| `PcCheckViewModel` | `RunPcChecks` | `result_rows`, Office/power/auto shutdown summary, count properties, `status_message` | `run_checks` | startup/작업 센터 | local `is_busy`; 메시지 한국어 변환 |
| `NetworkViewModel` | `ListNetworkAdapters`, `ApplyStaticIp`, `SetDhcp` | `adapters`, `selected_adapter`, current rows, validation/status text | `load_adapters`, `select_adapter_by_name`, `apply_static_ip`, `set_dhcp`, validation/default helpers | 네트워크 패널 | local `is_busy`; 적용 후 reload |
| `ActivationViewModel` | `ActivateWindows`, `ActivateOffice` | selected Windows/Office version, recommended version, `status_message` | `prepare_windows_activation`, `prepare_office_activation`, `apply_recommended_office_version` | 인증 영역 | local `is_busy`; 키 값 노출 금지 |

## 7. 안정화 작업 시 지켜야 할 API 원칙

- public method 이름을 바꿀 때는 UI 호출부와 tests를 함께 수정한다.
- 결과 모델 필드를 바꿀 때는 ViewModel 렌더링, table column, docs를 함께 수정한다.
- command runner, registry, network, filesystem side effect는 fake로 테스트한다.
- UI는 use case의 세부 구현을 몰라야 한다.
- 위험 작업은 `SafetyGuard` 또는 명시적 operation policy를 거쳐야 한다.
- test mode에서 차단되어야 하는 작업은 use case 레벨에서도 차단한다. 버튼 비활성화만으로 충분하지 않다.
- 제품키/비밀값은 model, log, exception, UI 문자열에 포함하지 않는다.
- action-only 설정은 상태 확인 provider가 없으면 `status_provider_missing`과 한국어 상세를 반환한다.
