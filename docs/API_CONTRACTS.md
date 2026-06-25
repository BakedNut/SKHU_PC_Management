# API Contracts

## 계층 책임

| 계층 | 책임 | 금지 |
| --- | --- | --- |
| `domain` | 순수 모델, 상태 값, 설정 정의 | PySide6, winreg, WMI, subprocess, netsh, powercfg |
| `application` | use case orchestration, `SafetyGuard`, port 호출 | PySide6, Windows API 직접 호출 |
| `ports` | 외부 시스템 계약 `Protocol` | 구현 세부사항 |
| `infrastructure/windows` | registry, PowerShell, WMI, filesystem, process adapter | domain/application 역의존 |
| `infrastructure/license` | 제품키 provider | 실제 제품키 커밋/출력 |
| `presentation/qt` | PySide6 UI, ViewModel, 사용자 확인 | Windows API 직접 호출 |

## 공통 결과 모델

| 모델 | 파일 | 목적 |
| --- | --- | --- |
| `ApplyResult` | `domain/settings/models.py` | 단일 설정/유지보수/설정 화면 열기 결과 |
| `ApplySettingsResult` | `domain/settings/models.py` | 설정 묶음 적용 요약 |
| `SettingStatus` | `domain/settings/models.py` | 현재 설정 상태 |
| `CheckResult` | `domain/checks/models.py` | PC 점검 단일 결과 |
| `NetworkConfigResult` | `domain/network/models.py` | 고정 IP/DHCP 처리 응답 |
| `ActivationResult` | `domain/activation/models.py` | 인증 준비 결과 |
| `TaskbarApplyResult` | `domain/resources/models.py` | 작업표시줄 dry-run/적용 응답 |
| `ResourceValidationResult` | `domain/resources/models.py` | 리소스 검증 결과 |
| `PcInfo`, `PcNetworkInfo`, `DiskInfo` | `domain/pc/models.py` | PC 정보 snapshot과 PC 정보 탭 표시용 대표 네트워크 정보 |
| `NetworkAdapterInfo`, `StaticIpConfig` | `domain/network/models.py` | 네트워크 adapter와 입력 모델 |

## SafetyGuard 계약

파일: `src/skhu_pc_management/application/safety.py`

| 메서드 | 계약 |
| --- | --- |
| `blocked_message(action)` | 테스트 모드이면 공통 차단 메시지를 반환한다. 아니면 `None` |
| `blocked_taskbar_apply_message(dry_run)` | dry-run은 허용한다. 실제 적용은 테스트 모드에서 차단한다. 운영 모드에서는 `allow_real_taskbar_apply`에 따른다. |

`create_safety_guard()`는 테스트 모드가 아니면 `allow_real_taskbar_apply=True`로 생성한다. 따라서 운영 UI에서 `set_taskbar_icons`는 실제 적용 경로를 요청할 수 있다.

## Use Case 계약

| Use case | 입력 | 출력 | side effect | SafetyGuard |
| --- | --- | --- | --- | --- |
| `LoadPcInfo` | 없음 | `PcInfo` | 읽기 | 없음 |
| `OpenPcNameSettings` | 없음 | `ApplyResult` | Windows 설정 화면 열기 | 테스트 모드 차단 |
| `RenamePc` | 새 이름 | `ApplyResult` | PC 이름 변경 | 테스트 모드 차단, 현재 UI 미사용 |
| `CheckSettingsStatus` | setting ids | `list[SettingStatus]` | 읽기 | 허용 |
| `ApplySettings` | setting ids | `ApplySettingsResult` | registry/action/taskbar 변경 | 테스트 모드 차단 |
| `ValidateTaskbarResources` | 없음 | `ResourceValidationResult` | 읽기 | 허용 |
| `ApplyTaskbarLayout` | `dry_run` | `TaskbarApplyResult` | dry-run 또는 실제 작업표시줄 적용 | dry-run 허용, 실제 적용은 guard |
| `ActivateWindows` | edition | `ActivationResult` | 제품키 복사, `slui.exe` 실행 | 테스트 모드 차단 |
| `ActivateOffice` | version | `ActivationResult` | 제품키 복사, Excel 실행 | 테스트 모드 차단 |
| `ListNetworkAdapters` | 없음 | adapters | 읽기 | 허용 |
| `ApplyStaticIp` | `StaticIpConfig` | `NetworkConfigResult` | IP/DNS 변경 | 테스트 모드 차단 |
| `SetDhcp` | adapter name | `NetworkConfigResult` | DHCP/DNS 변경 | 테스트 모드 차단 |
| `RunPcChecks` | 없음 | `list[CheckResult]` | 읽기 중심 | 허용 |
| `RunPcMaintenance` | method별 | `ApplyResult` | 삭제/전원/스케줄 변경 | 테스트 모드 차단 |
| `LaunchProgram` | program id | `ApplyResult` | 프로세스 실행 | 테스트 모드 차단 |
| `SystemSettingsActions` | setting id, label | `ApplyResult` | 배경/shortcut/계정 정책 변경 | 테스트 모드 차단 |

특수 계약:

- `ApplySettings`의 `set_taskbar_icons`는 `ApplyTaskbarLayout.execute(dry_run=False)`를 호출한다.
- `ApplySettings` post command 실패는 개별 `ApplyResult`나 상태 table detail에 전파하지 않는다.
- `SettingsViewModel.apply_selected()`는 적용 후 `display_setting_ids` 전체를 다시 상태 확인한다.
- `PcCheckViewModel`은 `office_install` 결과를 summary에는 쓰지만 table row에서는 제외한다.
- `LoadPcInfo`의 `PcInfo.network_info`는 PC 정보 탭 표시용 대표 IP/MAC이다. 후보는 현재 Up 상태인 실제 물리 Ethernet 또는 Wi-Fi, 유효한 IPv4 주소, 기본 게이트웨이를 모두 만족해야 한다.
- 대표 네트워크 선택은 Ethernet을 Wi-Fi보다 우선하고, 가상/VM/VPN/Docker/WSL/Bluetooth/Loopback/Tunnel 계열은 제외한다. 조건을 만족하는 후보가 없으면 `network_info=None`으로 반환한다.
- 이 대표 네트워크 선택은 `ListNetworkAdapters`와 `NetshNetworkConfigurator.list_adapters()`의 어댑터 목록/정적 IP 설정 계약을 변경하지 않는다.
- `WmiPcInfoReader`는 OS/CPU registry fast path, WMI namespace client cache, RAM module 우선 + fast total fallback, TPM WMI 우선 + registry fallback, Storage WMI + `Win32_DiskDrive` fallback을 사용한다.
- RAM 클럭 표시 source는 `Win32_PhysicalMemory.Speed`뿐이다. `ConfiguredClockSpeed`는 표시/계산/fallback에 사용하지 않는다.
- TPM registry fallback은 `Services\TPM\Start`로 disabled 상태나 version을 추론하지 않는다.
- 네트워크 adapter fast path는 `GetAdaptersAddresses`와 registry TCP/IP interface 보강을 사용한다. gateway/DHCP/DNS/subnet 값이 일부 비었다는 이유만으로 PowerShell fallback을 강제하지 않는다.

## Port 계약

| Port | 메서드 | 구현체 | 비고 |
| --- | --- | --- | --- |
| `Registry` | `read_value`, `list_subkeys`, `write_value` | `WinregRegistry` | registry 읽기/쓰기 |
| `CommandRunner` | `run(command)` | `SubprocessCommandRunner` | Windows에서는 hidden subprocess 옵션 사용 |
| `NetworkConfigurator` | `list_adapters`, `apply_static_ip`, `set_dhcp` | `NetshNetworkConfigurator` | PowerShell JSON 우선, netsh fallback |
| `ProcessLauncher` | `launch(executable, args)` | `WindowsProcessLauncher` | 사용자가 보는 앱 실행은 숨기지 않음 |
| `WindowsSettingsLauncher` | `open_pc_name_settings()` | `WindowsSettingsAppLauncher` | `cmd /c start "" ms-settings:about` |
| `ProductKeyProvider` | `get_windows_product_key`, `get_office_product_key` | `EmbeddedProductKeyProvider` | local module dynamic import |
| `Clipboard` | `set_text` | `WindowsClipboard` | 제품키 값 노출 금지 |
| `OfficeLauncher` | `launch_office_activation` | `WindowsOfficeLauncher` | Excel resolver 사용 |
| `ProgramLauncher` | `launch_program` | `WindowsProgramLauncher` | Chrome/Edge/PotPlayer/Bandizip |
| `ResourceResolver` | `resolve`, `resources_root` | `PyInstallerResourceResolver` | 개발/PyInstaller 경로 지원 |
| `TaskbarConfigurator` | `validate_resources`, `apply_taskbar_layout` | `WindowsTaskbarConfigurator` | Chrome 동적 shortcut 정책 |
| `SystemMaintenance` | `empty_recycle_bin`, `delete_browser_history`, `set_power_never`, `set_auto_shutdown_at_23` | `WindowsSystemMaintenance` | User Data reset, powercfg, ScheduledTasks |
| `AutoShutdownCancelShortcut` | `install`, `check` | `WindowsAutoShutdownCancelShortcut` | 리소스와 바탕화면 shortcut 동일성 |
| `ScheduledTaskReader` | `get_task` | `WindowsScheduledTaskReader` | 작업 없음과 조회 실패 구분 |
| `SettingStatusProvider` | `check(setting_id)` | Windows providers | action-only 상태 확인 |
| reader ports | 설치 프로그램, 최신 버전, 브라우저 데이터, 전원, 휴지통 | Windows adapters | 읽기 전용 점검 |

## Infrastructure 계약

- `windows_taskbar_configurator.py`
  - Chrome target 파일명은 `Google Chrome.lnk`.
  - `chrome.exe` 기반 shortcut 생성이 시작 메뉴 shortcut 복사보다 우선.
  - `TaskBar.reg` import 실패는 실패.
  - Explorer 재시작 실패는 실패가 아님.
- `windows_setting_status_providers.py`
  - 작업표시줄 expected/target shortcut 이름을 Chrome 기준으로 정규화.
  - `Google Chrome.lnk` TargetPath가 존재하지 않으면 설정됨으로 보지 않음.
- `windows_scheduled_task_reader.py`
  - 작업 없음은 `exists=False, error=None`.
  - 조회 실패/JSON 파싱 실패는 `error`를 채움.
- `windows_system_maintenance.py`
  - Chrome/Edge 초기화는 `User Data` root 전체 삭제.
  - 23시 자동종료 task 등록 후 취소 shortcut 복사.
  - 23시 자동종료 task는 22:55에 `shutdown.exe -s -t 300`을 실행해 23:00 종료를 목표로 한다.
  - Scheduled Task reader는 `schtasks` CSV fast path를 우선하고, 한국어 오전/오후 시간 파싱을 지원하며, 불완전하면 PowerShell fallback을 사용한다.
- `windows_settings_launcher.py`
  - Windows 설정 시스템 정보 화면만 열고 이름 변경 자체는 수행하지 않음.

## ViewModel 계약

| ViewModel | 주요 state | result row |
| --- | --- | --- |
| `PcInfoViewModel` | PC/OS/hardware/security field, representative network field, `open_pc_name_settings()` | PC 정보 rows, network rows, disk rows |
| `SettingsViewModel` | `status_message`, `result_rows`, `warning_count`, `summary_text` | `list[tuple[설정 항목, 현재 상태, 상세]]` |
| `PcCheckViewModel` | warning/error/unknown count, Office/power/auto shutdown summary | `list[tuple[항목, 상태, 상세]]`, Office row 제외 |
| `NetworkViewModel` | adapters, selected adapter, form/status text | `current_network_info_rows` |
| `ActivationViewModel` | 선택 Windows/Office version, status message | 없음 |

## Bootstrap 계약

`bootstrap.py`는 다음 factory를 제공한다.

- `is_test_mode_enabled()`
- `create_safety_guard()`
- `create_infrastructure()`
- `create_use_cases()`
- `create_view_models()`
- `create_startup_coordinator()`
- `create_main_window()`

새 Windows 기능은 `ports`를 먼저 만들고 `infrastructure/windows` adapter와 use case를 wiring한다.

## 변경 원칙

- public method 변경 시 ViewModel, UI, 테스트를 함께 갱신한다.
- Windows side effect는 fake로 테스트한다.
- 제품키/비밀값은 결과 모델, 로그, UI, 문서에 포함하지 않는다.
- 위험 작업은 `SafetyGuard`와 UI confirmation 정책을 모두 고려한다.
- 문서 변경 시 README, RELEASE_CHECKLIST, 이 계약 문서가 서로 충돌하지 않아야 한다.
