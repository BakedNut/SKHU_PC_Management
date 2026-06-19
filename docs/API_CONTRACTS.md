# API Contracts

## 1. 계층별 책임

| 계층 | 책임 | 허용 의존성 | 금지 의존성 | 테스트 전략 |
| --- | --- | --- | --- | --- |
| `domain` | 순수 모델, 값 검증, 상태 상수 | 표준 라이브러리, dataclass, typing | PySide6, winreg, subprocess, WMI, netsh, powercfg | 순수 unit test |
| `application` | use case orchestration, `SafetyGuard`, port 호출 | `domain`, `ports` | PySide6, winreg, subprocess, Windows API 직접 호출 | fake port 기반 |
| `ports` | 외부 시스템 계약 | `typing.Protocol`, domain model | 구현 세부사항 | protocol shape/fake |
| `infrastructure` | Windows/라이선스 실제 구현 | winreg, subprocess, ctypes, PowerShell, WMI, filesystem | domain/application로 역의존 금지 | fake/monkeypatch, command builder |
| `presentation` | PySide6 UI, ViewModel, 사용자 확인 dialog | PySide6, application use case | Windows API 직접 호출, 비즈니스 로직 과다 | ViewModel fake use case, UI는 가능하면 skip/offscreen |

## 2. 공통 결과 모델

| 모델 | 파일 | 주요 필드/타입 | 의미 | 성공/실패 기준 | UI 표시 | 테스트 |
| --- | --- | --- | --- | --- | --- | --- |
| `ApplyResult` | `domain/settings/models.py` | `name: str`, `success: bool`, `message: str`, `setting_id: str`, `status: str` | 설정/유지보수 단일 작업 결과 | `success`, `status` | 적용 결과/상세 | `tests/test_apply_settings.py`, `tests/test_test_mode_safety.py` |
| `ApplySettingsResult` | 동일 | `results: list[ApplyResult]`, count properties | 설정 묶음 적용 결과 | `is_success` | 성공/실패/스킵 요약 | `tests/test_apply_settings.py` |
| `SettingStatus` | 동일 | `setting_id`, `label`, `expected_value`, `actual_value`, `is_configured`, `severity`, `status_text`, `detail` | 현재 설정 상태 | `is_configured`, `status_text` | 현재 상태/상세 | `tests/test_check_settings_status.py` |
| `CheckResult` | `domain/checks/models.py` | `check_id`, `label`, `category`, `status`, `message`, `detail`, `raw_value`, `passed` | PC 점검 단일 결과 | `status == ok` 또는 `passed` | 점검 table | `tests/test_pc_checks.py` |
| `NetworkConfigResult` | `domain/network/models.py` | `operation`, `success`, `adapter_name`, `message`, `commands` | IP/DHCP 적용 결과 | `success` | 네트워크 status | `tests/test_network_settings.py` |
| `ActivationResult` | `domain/activation/models.py` | `success`, `action`, `message`, `launched_process`, `copied_to_clipboard`, `error` | 인증 준비 결과 | `success` | 인증 status. 키 값 금지 | `tests/test_activation.py` |
| `TaskbarApplyResult` | `domain/resources/models.py` | `success`, `message`, `dry_run`, `reg_file`, `shortcut_files`, `planned_actions` | 작업표시줄 dry-run/적용 결과 | `success` | 계획/상세 | `tests/test_taskbar_configurator.py` |
| `ResourceValidationResult` | 동일 | `success`, `message`, `resources_root`, `reg_file`, `taskbar_dir`, `shortcut_files`, `warnings` | resource 검증 | `success` | 리소스 상태 | `tests/test_taskbar_configurator.py` |
| `PcInfo` | `domain/pc/models.py` | PC/OS/CPU/RAM/GPU/disk/security fields | PC 정보 snapshot | 모델 생성 성공 | PC 정보 panel | `tests/test_load_pc_info.py` |
| `DiskInfo` | 동일 | `model`, `actual_size_gib`, `rated_size`, `bus_type`, `display_type`, `serial_number` | 디스크 표시 모델 | 읽기 모델 | disk table | `tests/test_load_pc_info.py` |
| `NetworkAdapterInfo` | `domain/network/models.py` | `name`, `description`, `is_enabled`, `mac_address`, `ip_addresses`, `subnet_mask`, `gateway`, `dns_servers`, `is_dhcp_enabled` | adapter 상태 | 읽기 모델 | adapter list/current table | `tests/test_network_settings.py` |
| `StaticIpConfig` | 동일 | `adapter_name`, `ip_address`, `subnet_mask`, `gateway`, `dns1`, `dns2`, `dns_servers` | static IP 입력 | 생성 시 validation | use case 입력 | `tests/test_domain_models.py`, `tests/test_network_settings.py` |
| `StartupResult` | `presentation/qt/startup_coordinator.py` | `is_admin`, `step_results`, `has_failures` | startup 초기화 결과 | step success | MainWindow status | `tests/test_startup_coordinator.py` |
| `StartupStepResult` | 동일 | `name`, `success`, `message` | startup 단계별 결과 | `success` | 관리자/초기화 메시지 | `tests/test_startup_coordinator.py` |

## 3. SafetyGuard 계약

파일: `src/skhu_pc_management/application/safety.py`

| 항목 | 계약 |
| --- | --- |
| 필드 | `test_mode: bool = False`, `allow_real_taskbar_apply: bool = False` |
| 메시지 | `TEST_MODE_DISABLED_MESSAGE`, `REAL_TASKBAR_APPLY_DISABLED_MESSAGE` |
| `blocked_message(action)` | `test_mode=True`면 모든 mutating action에 공통 차단 메시지 반환. 아니면 `None` |
| `blocked_taskbar_apply_message(dry_run)` | `dry_run=True`면 항상 `None`. `dry_run=False`는 test mode면 test mode 메시지, 아니면 `allow_real_taskbar_apply=False`에서 real apply 차단 메시지 |
| test mode | use case guard와 UI disabled가 같이 사용됨 |
| real taskbar apply | 명시적으로 `SafetyGuard(allow_real_taskbar_apply=True)`를 주지 않으면 차단 |
| 한계 | 현재는 위험도 enum/OperationPolicy 전체 모델이 아니라 test mode + taskbar 특수 정책 구조다. 기능별 위험도 일반화는 후속 작업이다. |

## 4. Use Case 계약

| Use case | 파일 | 입력 | 출력 | side effect | 위험도 | SafetyGuard/test mode | 관련 port | ViewModel | 테스트 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `LoadPcInfo` | `use_cases/load_pc_info.py` | 없음 | `PcInfo` | 읽기 | 낮음 | 없음 | `PcInfoReader` | `PcInfoViewModel` | `test_load_pc_info.py` |
| `RenamePc` | `use_cases/rename_pc.py` | `new_name` | `ApplyResult` | PC 이름 변경 | 높음 | 차단 | `PcRenamer` | `PcInfoViewModel` | `test_test_mode_safety.py` |
| `ApplySettings` | `use_cases/apply_settings.py` | setting ids | `ApplySettingsResult` | registry write/command/action | 높음 | 차단 | `Registry`, `CommandRunner`, taskbar/system actions | `SettingsViewModel` | `test_apply_settings.py` |
| `CheckSettingsStatus` | `use_cases/check_settings_status.py` | setting ids | `list[SettingStatus]` | 읽기 | 낮음 | 허용 | `Registry`, `SettingStatusProvider` | `SettingsViewModel` | `test_check_settings_status.py` |
| `ApplyTaskbarLayout` | `use_cases/apply_taskbar_layout.py` | `dry_run` | `TaskbarApplyResult` | dry-run/실제 적용 | 매우 높음 | dry-run 허용, real 기본 차단 | `TaskbarConfigurator` | `SettingsViewModel` | `test_taskbar_configurator.py` |
| `ValidateTaskbarResources` | `use_cases/validate_taskbar_resources.py` | 없음 | `ResourceValidationResult` | 읽기 | 낮음 | 허용 | `TaskbarConfigurator` | `SettingsViewModel` | `test_taskbar_configurator.py` |
| `ActivateWindows` | `use_cases/activate_windows.py` | edition optional | `ActivationResult` | clipboard + `slui.exe` | 민감 | 차단 | `ProductKeyProvider`, `Clipboard`, `ProcessLauncher` | `ActivationViewModel` | `test_activation.py` |
| `ActivateOffice` | `use_cases/activate_office.py` | version optional | `ActivationResult` | clipboard + `excel.exe` | 민감 | 차단 | 동일 | `ActivationViewModel` | `test_activation.py` |
| `ListNetworkAdapters` | `use_cases/list_network_adapters.py` | 없음 | `list[NetworkAdapterInfo]` | 읽기 | 낮음 | 허용 | `NetworkConfigurator` | `NetworkViewModel` | `test_network_settings.py` |
| `ApplyStaticIp` | `use_cases/apply_static_ip.py` | `StaticIpConfig` | `NetworkConfigResult` | IP/DNS 변경 | 높음 | 차단 | `NetworkConfigurator` | `NetworkViewModel` | `test_network_settings.py` |
| `SetDhcp` | `use_cases/set_dhcp.py` | adapter name | `NetworkConfigResult` | DHCP/DNS 변경 | 높음 | 차단 | `NetworkConfigurator` | `NetworkViewModel` | `test_network_settings.py` |
| `RunPcChecks` | `use_cases/run_pc_checks.py` | 없음 | `list[CheckResult]` | 읽기 중심 | 낮음 | 허용 | check reader ports | `PcCheckViewModel` | `test_pc_checks.py` |
| `RunPcMaintenance` | `use_cases/run_pc_maintenance.py` | method별 | `ApplyResult` | 삭제/전원/스케줄 변경 | 높음 | 차단 | `SystemMaintenance` | `ActionCenterPanel` | `test_browser_user_data_reset.py`, `test_test_mode_safety.py` |
| `LaunchProgram` | `use_cases/launch_program.py` | program id | `ApplyResult` | 프로세스 실행 | 낮음~중간 | 차단 | `ProgramLauncher` | `ActionCenterPanel` | `test_test_mode_safety.py` |
| `SystemSettingsActions` | `use_cases/system_settings_actions.py` | setting id, label | `ApplyResult` | 배경/shortcut/password 변경 | 중간~높음 | 차단 | `SystemSettingsOperator` | `ApplySettings` | `test_test_mode_safety.py` |

특수 계약:

- `ApplySettings`에서 `set_taskbar_icons`는 `dry_run=True`로만 `ApplyTaskbarLayout`을 호출한다.
- `ApplyTaskbarLayout(dry_run=False)`는 기본 `SafetyGuard`에서 차단된다.
- `RunPcMaintenance.delete_browser_history()`는 이름과 달리 브라우저 `User Data` root 초기화 정책이다.
- `CheckSettingsStatus`는 provider map으로 registry만으로 확인할 수 없는 action-only 설정을 확인한다.

## 5. Ports 계약

| Port | 목적 | 메서드 | 출력 | 구현체 | side effect | fake/mock | 테스트 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Registry` | registry access | `read_value`, `list_subkeys`, `write_value` | object/list/None | `WinregRegistry` | 쓰기 시 있음 | 필수 | `test_registry_adapter.py`, fake tests |
| `CommandRunner` | 외부 명령 | `run(command)` | stdout | `SubprocessCommandRunner` | 명령별 | 필수 | network/power/task tests |
| `NetworkConfigurator` | adapter/IP | `list_adapters`, `apply_static_ip`, `set_dhcp` | network models | `NetshNetworkConfigurator` | 변경 메서드 있음 | 필수 | `test_network_settings.py` |
| `ProcessLauncher` | 프로세스 실행 | `launch` | None | `WindowsProcessLauncher` | 있음 | 필수 | activation tests |
| `ProductKeyProvider` | 제품키 공급 | `get_windows_product_key`, `get_office_product_key` | str/None | `EmbeddedProductKeyProvider` | 없음, 민감 | fake 필수 | `test_activation.py` |
| `Clipboard` | 클립보드 | `set_text` | None | `WindowsClipboard` | 있음 | 필수 | `test_activation.py` |
| `ResourceResolver` | resources 경로 | `resolve`, `resources_root` | Path | `PyInstallerResourceResolver` | 없음 | monkeypatch | `test_resource_resolver.py` |
| `SystemMaintenance` | 유지보수 변경 | `empty_recycle_bin`, `delete_browser_history`, `set_power_never`, `set_auto_shutdown_at_23` | code/bool/str | `WindowsSystemMaintenance` | 있음 | 필수 | `test_browser_user_data_reset.py` |
| `PcRenamer` | PC 이름 변경 | `rename` | bool | `WindowsPcRenamer` | 있음 | 필수 | `test_test_mode_safety.py` |
| `ProgramLauncher` | 프로그램 실행 | `launch_program` | bool | `WindowsProgramLauncher` | 있음 | 필수 | `test_test_mode_safety.py` |
| `CheckProvider` | 개별 점검 | `run` | `CheckResult` | check classes | 보통 읽기 | fake 가능 | `test_pc_checks.py` |
| `SettingStatusProvider` | action-only 상태 | `check(setting_id)` | `SettingStatus` | `windows_setting_status_providers.py` | 읽기 | fake 가능 | `test_setting_status_providers.py` |
| 기타 reader ports | 설치/브라우저/전원/휴지통/예약 작업 조회 | port별 `read_status` 등 | domain model | Windows adapters | 읽기 | fake/monkeypatch | 각 test |

## 6. Infrastructure Adapter 계약

| Adapter | Port | Windows API/명령 | 관리자 권한 | 실패 처리 | 단위 테스트 대체 | 위험 |
| --- | --- | --- | --- | --- | --- | --- |
| `winreg_registry.py` | `Registry` | winreg | HKLM 쓰기/일부 읽기 | missing은 None, 권한은 예외 유지 | fake/monkeypatch | registry write |
| `subprocess_command_runner.py` | `CommandRunner` | subprocess | 명령별 | command failure 예외 | fake | 명령별 |
| `netsh_network_configurator.py` | `NetworkConfigurator` | PowerShell JSON, netsh fallback | IP 변경 시 예 | result/exception | fake command runner | network change |
| `windows_system_maintenance.py` | `SystemMaintenance` | 파일 삭제, powercfg, ScheduledTasks 등 | 작업별 | bool/str/예외 | tmp_path/fake | destructive |
| `windows_taskbar_configurator.py` | `TaskbarConfigurator` | file copy, reg import, Explorer 계획/실행 | real apply 시 | validation/result | tmp_path/fake runner | taskbar |
| `windows_system_settings_operator.py` | `SystemSettingsOperator` | registry/file/command | 작업별 | 예외 | fake | system setting |
| `windows_setting_status_providers.py` | `SettingStatusProvider` | registry/file/PowerShell read | 읽기 | unknown status | fake registry/runner | read only |
| `embedded_product_key_provider.py` | `ProductKeyProvider` | dynamic import local module | 없음 | 파일 누락 한국어 오류 | monkeypatch import | secret |
| `windows_clipboard.py` | `Clipboard` | ctypes Win32 clipboard | 없음 | 예외 | fake | secret exposure |
| `windows_process_launcher.py` | `ProcessLauncher` | process launch | 대상별 | 예외 | fake | process |
| `windows_program_launcher.py` | `ProgramLauncher` | registry + process | 대상별 | False/예외 | fake | process |
| `wmi_pc_info_reader.py` | `PcInfoReader` | WMI, registry/command fallback | 일부 | Unknown/None fallback | fake/helper | read |
| `windows_pc_renamer.py` | `PcRenamer` | command/WMI | 예 | bool/예외 | fake | rename |
| `browser_data_reader.py` | `BrowserDataReader` | filesystem | 아니오 | 접근 실패 skip | tmp_path | read |
| `recycle_bin_reader.py` | `RecycleBinReader` | Win32/Shell 확인 필요 | 상황별 | unknown 가능 | fake | read |
| `power_settings_reader.py` | `PowerSettingsReader` | powercfg via CommandRunner | 상황별 | parse 실패 unknown | fake output | read |
| `windows_scheduled_task_reader.py` | `ScheduledTaskReader` | PowerShell ScheduledTasks | 상황별 | exists false/unknown | fake output | read |
| `installed_program_reader.py` | `InstalledProgramReader` | registry | 읽기 | missing None | fake registry | read |
| `latest_version_provider.py` | `LatestVersionProvider` | 최신 버전 조회 구조 | 네트워크 확인 필요 | None | fake | network 확인 필요 |

## 7. ViewModel 계약

| ViewModel | 입력 use case | public state/method | result row | summary/validation | test mode 관계 | 테스트 |
| --- | --- | --- | --- | --- | --- | --- |
| `PcInfoViewModel` | `LoadPcInfo`, optional `RenamePc` | `refresh`, `rename_pc`, `auto_rename_pc`, PC/OS/hardware/security fields | `rows: list[tuple[str, str]]`, `disks: list[tuple[str,str,str,str]]` | 없음 | Panel/use case에서 차단 | `test_qt_viewmodels.py` |
| `SettingsViewModel` | `CheckSettingsStatus`, `ApplySettings`, taskbar use cases | `all_setting_ids`, `check_status`, `apply_selected`, `validate_taskbar_resources`, `apply_taskbar_layout` | `list[tuple[str, str, str, str]]` | `warning_count`, `summary_text` | use case guard. UI disabled 별도 | `test_qt_viewmodels.py` |
| `PcCheckViewModel` | `RunPcChecks` | `run_checks`, Office/power/auto shutdown summary texts | `list[tuple[str, str, str]]` | `warning_count`, `error_count`, `unknown_count`, `summary_text` | 읽기 중심 | `test_qt_viewmodels.py` |
| `NetworkViewModel` | `ListNetworkAdapters`, `ApplyStaticIp`, `SetDhcp` | `load_adapters`, `select_adapter_by_name`, `apply_static_ip`, `set_dhcp`, `default_static_ip_fields`, `gateway_for_ip_address`, `validate_static_ip_fields` | `current_network_info_rows` | IP validation, apply/DHCP 후 reload | use case guard. UI disabled | `test_network_settings.py`, `test_qt_viewmodels.py` |
| `ActivationViewModel` | `ActivateWindows`, `ActivateOffice` | `prepare_windows_activation`, `prepare_office_activation`, `apply_recommended_office_version` | 없음 | selected/recommended version | use case guard. UI disabled | `test_activation.py`, `test_qt_viewmodels.py` |

## 8. Presentation/UI Helper 계약

| Helper | 주요 class/function | objectName/property | 사용 위치 | 테스트 |
| --- | --- | --- | --- | --- |
| `buttons.py` | `primary_button`, `secondary_button`, `subtle_button`, `warning_button`, `danger_button`, `nav_button`, `set_button_role`, `set_selected` | `buttonRole`, `selected` | 모든 panel, nav | 간접/compile |
| `badges.py` | `StatusBadge`, `badge_tone_from_status`, alias helpers | `statusBadge`, `tone` | header/status | `test_qt_viewmodels.py` 간접 |
| `surfaces.py` | `Card`, `SectionCard`, `SummaryCard`, alias helpers | `card`, `sectionCard`, summary label names | panels | 간접 |
| `forms.py` | `ReadOnlyField`, `FieldRow`, `FormGrid`, alias helpers | `fieldLabel`, `mutedText`, `readOnlyField` | PC/network | 간접 |
| `tables.py` | `configure_table`, `table_item`, `status_item` | QTableWidget settings | settings/check/disk table | 간접 |

## 9. Bootstrap 계약

파일: `src/skhu_pc_management/bootstrap.py`

| Factory/container | 역할 |
| --- | --- |
| `InfrastructureContainer` | registry, command runner, process/clipboard/product key/resource resolver, Windows adapters 보관 |
| `UseCaseContainer` | load/check/apply/network/maintenance/activation use case 보관 |
| `ViewModelContainer` | PC 정보, 설정, 네트워크, PC 점검, 인증 ViewModel 보관 |
| `is_test_mode_enabled()` | 환경변수 `SKHU_PC_MANAGEMENT_TEST_MODE=1` 확인 |
| `create_safety_guard()` | test mode 반영 `SafetyGuard` 생성 |
| `create_infrastructure()` | Windows adapter 인스턴스 생성 |
| `create_use_cases()` | provider map 포함 use case 조립 |
| `create_view_models()` | ViewModel 생성 |
| `create_startup_coordinator()` | 관리자 권한/초기 로딩 coordinator 생성 |
| `create_main_window()` | MainWindow 최종 조립 |

## 10. API 변경 원칙

- public method 변경 시 UI 호출부와 테스트를 같이 수정한다.
- 결과 모델 필드 변경 시 ViewModel과 table rendering을 같이 수정한다.
- Windows side effect는 fake로 테스트한다.
- UI는 infrastructure 세부 구현을 몰라야 한다.
- 위험 작업은 `SafetyGuard` 또는 `SAFETY_POLICY.md` 기준을 거쳐야 한다.
- 제품키/비밀값은 결과 모델, 로그, UI에 포함하지 않는다.
- docs 계약 변경 시 README/RELEASE_CHECKLIST와 충돌 여부를 감사한다.

## 11. API 감사 결과

| 계약 항목 | 현재 구현 | 테스트 고정 | 문서화 | 불일치/취약점 | 후속 작업 |
| --- | --- | --- | --- | --- | --- |
| SafetyGuard | test mode + taskbar 특수 정책 | 있음 | 이 문서/README | 위험도 일반화 아님 | OperationPolicy 검토 |
| Settings result row | 4-tuple | 있음 | 이 문서 | tuple 의미 암묵적 | dataclass 전환 |
| PC check result row | 3-tuple | 있음 | 이 문서 | detail/raw_value 일부 손실 가능 | detail 모델 확장 |
| Network reload | ViewModel sync reload | 있음 | README/체크리스트 | UI freeze 가능 | async/QTimer 검토 |
| Action-only status provider | 4개 provider | 있음 | README/이 문서 | 일부 action 추가 시 누락 가능 | provider registry 관리 |
| Product key provider | local module dynamic import | 있음 | README/이 문서 | PyInstaller 포함 정책 수동 | 배포 절차 점검 |
| Maintenance naming | method name은 `delete_browser_history`, 실제는 User Data reset | 테스트/문서 있음 | 이 문서 | 이름과 정책 불일치 | method rename 검토 |
