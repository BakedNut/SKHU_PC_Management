# SKHU PC Management 기능 명세서

## 1. 제품 목적

`SKHU PC Management`는 성공회대학교 강의실/학교 PC의 초기 설정, 점검, 유지보수, 인증 준비, 네트워크 설정을 돕는 Windows 전용 관리 도구다. 최신 `develop` 기준 구현은 Python 3.12+와 PySide6 기반 데스크톱 앱이며, PyInstaller exe 배포를 전제로 한다.

이 앱에는 레지스트리 변경, IP/DHCP 변경, PC 이름 변경, 전원 옵션 변경, 예약 작업 등록, 작업표시줄 설정, Chrome/Edge 사용자 데이터 초기화, 제품키 클립보드 복사처럼 실제 PC 상태에 영향을 주는 기능이 있다. 따라서 실제 Windows 상태 변경 작업은 `ports`와 `infrastructure/windows` adapter 뒤로 격리되어야 하며, `domain`/`application` 계층에서 PySide6, winreg, subprocess, WMI, netsh, powercfg 같은 Windows/API 세부 구현을 직접 import하면 안 된다.

테스트 모드(`SKHU_PC_MANAGEMENT_TEST_MODE=1`)에서는 위험 작업이 UI와 use case 양쪽에서 차단되어야 한다. 제품키/비밀값은 코드, 문서, 로그, 테스트 출력, UI 메시지에 노출하지 않는다.

## 2. 현재 구현 요약

| 항목 | 최신 코드 기준 실제 구현 | 관련 파일 |
| --- | --- | --- |
| 메인 UI 구조 | QTabWidget이 아니라 top bar + left navigation + `QStackedWidget` 구조 | `src/skhu_pc_management/presentation/qt/main_window.py` |
| 주요 화면 | `PC 정보`, `작업 센터`, `네트워크` 3개 stack page | `main_window.py` |
| 작업 센터 | summary cards, recommended actions, 인증 card, 설정 card, 유지보수 도구, 설정 상태 table, PC 점검 table, 강의실 작업 card 보유 | `presentation/qt/panels/action_center_panel.py` |
| SafetyGuard | `test_mode`, `allow_real_taskbar_apply` 두 필드. 위험도 enum 기반 일반 정책은 아직 아님 | `application/safety.py` |
| 작업표시줄 실제 적용 | `ApplyTaskbarLayout(dry_run=False)`는 기본 `allow_real_taskbar_apply=False`에서 차단 | `application/use_cases/apply_taskbar_layout.py`, `tests/test_taskbar_configurator.py` |
| `set_taskbar_icons` | 설정 적용 경로에서 `apply_taskbar_layout_use_case.execute(dry_run=True)`만 호출 | `application/use_cases/apply_settings.py`, `tests/test_apply_settings.py` |
| Chrome/Edge 초기화 | 방문 기록 파일만 삭제가 아니라 브라우저 `User Data` root 전체 초기화 정책 | `application/use_cases/run_pc_maintenance.py`, `infrastructure/windows/windows_system_maintenance.py`, `tests/test_browser_user_data_reset.py` |
| Chrome/Edge UI 문구 | 버튼은 `Chrome 사용자 데이터 초기화`, `Edge 사용자 데이터 초기화`; 보조 문구는 `User Data 전체 삭제` | `action_center_panel.py` |
| 위험 유지보수 확인 | 유지보수 작업은 `maintenance_confirmation_for()`로 확인 dialog를 거침 | `presentation/qt/maintenance_confirmations.py`, `action_center_panel.py` |
| 설정 적용 후 재검증 | `SettingsViewModel.apply_selected()`가 apply 후 같은 setting id로 `check_settings_status_use_case.execute()` 호출 | `presentation/qt/viewmodels/settings_viewmodel.py`, `tests/test_qt_viewmodels.py` |
| action-only 상태 확인 | wallpaper, Edge shortcut, taskbar layout, password expiration provider 존재 | `ports/setting_status_provider.py`, `infrastructure/windows/windows_setting_status_providers.py` |
| 네트워크 적용 후 reload | static IP/DHCP 성공 후 `_reload_after_network_change()`로 adapter list 재조회 | `presentation/qt/viewmodels/network_viewmodel.py`, `tests/test_network_settings.py` |
| bootstrap 조립 | `InfrastructureContainer`, `UseCaseContainer`, `ViewModelContainer`와 factory 함수로 분리 | `src/skhu_pc_management/bootstrap.py`, `tests/test_bootstrap_wiring.py` |

## 3. 주요 사용자

| 사용자 | 주요 작업 |
| --- | --- |
| 학교/강의실 PC 관리자 | 다수 PC의 초기 설정, 네트워크, 전원, 자동 종료 상태 확인/조정 |
| PC 초기 세팅 담당자 | 기본 설정 적용, PC 이름 변경, Windows/Office 인증 준비 |
| PC 점검/유지보수 담당자 | 설치 프로그램/버전, 브라우저 사용자 데이터, 휴지통, 전원, 예약 작업 점검 |

## 4. 실행 환경

| 항목 | 내용 |
| --- | --- |
| OS | Windows 전용 |
| Python | 3.12+ (`pyproject.toml`) |
| GUI | PySide6 |
| 배포 | PyInstaller |
| 권한 | 관리자 권한 권장/일부 작업 필수 |
| 테스트 모드 | `SKHU_PC_MANAGEMENT_TEST_MODE=1` |
| 제품키 | `src/skhu_pc_management/infrastructure/license/local_product_keys.py` 로컬 전용, Git 커밋 금지 |

## 5. 아키텍처 요약

| 계층/디렉터리 | 역할 | 금지/주의 |
| --- | --- | --- |
| `domain` | 순수 dataclass/model/definition. 예: `PcInfo`, `DiskInfo`, `SettingStatus`, `CheckResult` | PySide6, winreg, subprocess, WMI, netsh, powercfg 금지 |
| `application` | use case orchestration, `SafetyGuard`, port 호출 | Windows API 직접 호출 금지. PySide6 import 금지 |
| `ports` | 외부 시스템 계약 `Protocol` | 구현 세부사항 금지 |
| `infrastructure/windows` | 실제 Windows adapter. registry, PowerShell, netsh, WMI, ctypes 등은 여기서만 사용 | 단위 테스트에서는 fake/monkeypatch로 대체 |
| `presentation/qt` | PySide6 UI, ViewModel, 사용자 확인 dialog | GUI는 얇게 유지. Windows 직접 호출 금지 |
| `resources` | 이미지, TaskBar.reg, TaskBar 바로가기 리소스 | 배포 포함 여부 확인 필요 |
| `tests` | fake 기반 단위 테스트 | 실제 registry/netsh/powercfg/WMI/clipboard/process 호출 금지 |

## 6. 화면 구성

### PC 정보

| 항목 | 내용 |
| --- | --- |
| 목적 | 현재 PC/OS/하드웨어/보안 상태 조회와 PC 이름 변경 |
| 주요 데이터 | PC 이름, 사용자, Windows, CPU/RAM/GPU, 디스크, TPM, Secure Boot, Boot Mode |
| 주요 버튼 | 새로고침, PC 이름 변경, PC 이름 사용자 이름과 맞추기 |
| ViewModel | `PcInfoViewModel` |
| Use case | `LoadPcInfo`, `RenamePc` |
| 위험 작업 | PC 이름 변경/자동 변경 |
| test mode | 이름 변경 버튼 비활성화 및 use case guard |

### 작업 센터

| 영역 | 현재 구현 |
| --- | --- |
| summary cards | 설정 상태, PC 점검, Office, 강의실 정책 |
| recommended actions | 설정 warning count, PC 점검 warning/error, 전원/자동종료 상태 기반 안내 |
| 인증 | Windows 10/11, Office 2021/2024 선택. 제품키 값은 표시하지 않음 |
| 시스템 설정 선택 | checkbox 기반 설정 선택, 전체 선택/해제, 선택 개수 표시 |
| 유지보수 도구 | 휴지통 비우기, 프로그램 실행, Chrome/Edge 사용자 데이터 초기화 |
| 설정 상태 table | 4열: 설정 항목, 적용 결과, 현재 상태, 상세 |
| PC 점검 table | 3열: 항목, 상태, 상세 내용 |
| 강의실 PC 작업 | 전원 옵션 안 함 적용, 23시 자동종료 적용 |
| test mode | 설정 적용, 인증, 위험 유지보수/강의실 작업 버튼 비활성화 |

### 네트워크

| 항목 | 내용 |
| --- | --- |
| 목적 | adapter 조회, 현재 상태 표시, static IP/DHCP 전환 |
| 주요 데이터 | adapter name/description/status/MAC, IP, subnet, gateway, DNS, DHCP 여부 |
| 주요 버튼 | 새로고침, 학교 기본 대역 입력, 정적 IP 적용, DHCP 전환 |
| ViewModel | `NetworkViewModel` |
| Use case | `ListNetworkAdapters`, `ApplyStaticIp`, `SetDhcp` |
| 위험 작업 | static IP/DHCP |
| test mode | apply/DHCP 버튼 비활성화 및 use case guard |

## 7. 기능 매트릭스

| 기능 ID | 기능명 | 화면 | 현재 구현 상태 | 관련 파일 | 읽기/쓰기 | 위험도 | 관리자 권한 | test mode 차단 | dry-run | 상태 확인 | confirmation | 테스트 고정 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pc_info.load` | PC 정보 조회 | PC 정보 | 구현됨 | `load_pc_info.py`, `wmi_pc_info_reader.py` | 읽기 | 낮음 | 일부 조회 필요 가능 | 아니오 | 해당 없음 | 해당 없음 | 아니오 | `tests/test_load_pc_info.py` | WMI 실패 fallback |
| `pc.rename.manual` | PC 이름 변경 | PC 정보 | 구현됨 | `rename_pc.py`, `windows_pc_renamer.py`, `pc_info_panel.py` | 쓰기 | 높음 | 예 | 예 | 아니오 | 부분 | 확인 필요 | `tests/test_test_mode_safety.py` | UI는 입력 dialog 후 실행, 명시 confirmation은 확인 필요 |
| `pc.rename.auto` | 사용자 이름 기반 이름 변경 | PC 정보 | 구현됨 | `pc_info_viewmodel.py`, `pc_info_panel.py` | 쓰기 | 높음 | 예 | 예 | 아니오 | 부분 | 확인 필요 | 부분 | 재부팅 안내 있음 |
| `activation.windows.prepare` | Windows 인증 준비 | 작업 센터 | 구현됨 | `activate_windows.py`, `activation_viewmodel.py` | 클립보드/프로세스 | 민감 | 상황별 | 예 | 아니오 | 결과만 | 버튼 의도 기반 | `tests/test_activation.py`, `tests/test_test_mode_safety.py` | 키 값 미표시 |
| `activation.office.prepare` | Office 인증 준비 | 작업 센터 | 구현됨 | `activate_office.py`, `activation_viewmodel.py` | 클립보드/프로세스 | 민감 | 상황별 | 예 | 아니오 | 결과만 | 버튼 의도 기반 | `tests/test_activation.py` | Excel 경로는 `excel.exe` fallback |
| `settings.apply` | 기본 설정 적용 | 작업 센터 | 구현됨 | `apply_settings.py`, `settings_viewmodel.py` | 쓰기 | 높음 | 일부 예 | 예 | 일부 | 적용 후 verify | 확인 필요 | `tests/test_apply_settings.py`, `tests/test_qt_viewmodels.py` | ActionCenter에 별도 confirmation은 코드상 확인 필요 |
| `settings.status.check` | 설정 상태 확인 | 작업 센터 | 구현됨 | `check_settings_status.py` | 읽기 | 낮음 | 일부 | 아니오 | 해당 없음 | 예 | 아니오 | `tests/test_check_settings_status.py` | registry + provider |
| `settings.wallpaper.default` | 기본 배경화면 | 작업 센터 | 구현됨 | `system_settings_actions.py`, `windows_setting_status_providers.py` | 쓰기/읽기 | 중간 | 상황별 | 예 | 아니오 | provider | 설정 적용 확인 필요 | `tests/test_setting_status_providers.py` | action-only |
| `settings.edge_shortcut.delete` | Edge shortcut 삭제 | 작업 센터 | 구현됨 | `system_settings_actions.py`, `windows_setting_status_providers.py` | 삭제/정책 | 중간 | 일부 예 | 예 | 아니오 | provider | 설정 적용 확인 필요 | `tests/test_setting_status_providers.py` | action-only |
| `settings.taskbar.plan` | 작업표시줄 dry-run/검증 | 작업 센터 | 구현됨 | `apply_taskbar_layout.py`, `windows_taskbar_configurator.py` | 읽기/계획 | 낮음 | 아니오 | 아니오 | 예 | provider | 아니오 | `tests/test_taskbar_configurator.py` | default path |
| `settings.taskbar.real_apply` | 작업표시줄 실제 적용 | 작업 센터 | 구조 있음, 기본 차단 | `apply_taskbar_layout.py`, `SafetyGuard` | 쓰기 | 매우 높음 | 예 가능 | 예 | 아니오 | 부분 | 필수 | `tests/test_taskbar_configurator.py`, `tests/test_operation_safety_policy.py` | 명시 허용 전 금지 |
| `maintenance.recycle_bin.empty` | 휴지통 비우기 | 작업 센터 | 구현됨 | `run_pc_maintenance.py`, `maintenance_confirmations.py` | 삭제 | 중간 | 상황별 | 예 | 아니오 | PC 점검 | 예 | `tests/test_operation_safety_policy.py` | 확인 dialog 있음 |
| `maintenance.chrome_user_data.reset` | Chrome User Data 초기화 | 작업 센터 | 구현됨 | `run_pc_maintenance.py`, `windows_system_maintenance.py` | 삭제 | 매우 높음 | 아니오 | 예 | 아니오 | PC 점검 | 예 | `tests/test_browser_user_data_reset.py` | 방문 기록만 삭제 아님 |
| `maintenance.edge_user_data.reset` | Edge User Data 초기화 | 작업 센터 | 구현됨 | 동일 | 삭제 | 매우 높음 | 아니오 | 예 | 아니오 | PC 점검 | 예 | `tests/test_browser_user_data_reset.py` | User Data 전체 |
| `maintenance.power.never` | 전원 옵션 안 함 | 작업 센터 | 구현됨 | `run_pc_maintenance.py`, `windows_system_maintenance.py` | 쓰기 | 중간 | 예 가능 | 예 | 아니오 | PC 점검 | 예 | `tests/test_operation_safety_policy.py` | powercfg 변경 |
| `maintenance.auto_shutdown_23.apply` | 23시 자동종료 등록 | 작업 센터 | 구현됨 | `run_pc_maintenance.py`, `windows_system_maintenance.py` | 쓰기 | 중간 | 예 가능 | 예 | 아니오 | PC 점검 | 예 | `tests/test_pc_checks.py` | ScheduledTasks |
| `program.chrome.launch` | Chrome 실행 | 작업 센터 | 구현됨 | `launch_program.py`, `windows_program_launcher.py` | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 | 아니오 | `tests/test_test_mode_safety.py` | test mode 차단 |
| `program.edge.launch` | Edge 실행 | 작업 센터 | 구현됨 | 동일 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 | 아니오 | 부분 |  |
| `program.potplayer.launch` | PotPlayer 실행 | 작업 센터 | 구현됨 | 동일 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 | 아니오 | 부분 |  |
| `program.bandizip.launch` | Bandizip 실행 | 작업 센터 | 구현됨 | 동일 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 | 아니오 | 부분 |  |
| `network.adapters.list` | adapter 조회 | 네트워크 | 구현됨 | `list_network_adapters.py`, `netsh_network_configurator.py` | 읽기 | 낮음 | 아니오 | 아니오 | 해당 없음 | 해당 없음 | 아니오 | `tests/test_network_settings.py` | PowerShell JSON 우선 |
| `network.static_ip.apply` | static IP 적용 | 네트워크 | 구현됨 | `apply_static_ip.py`, `network_panel.py` | 쓰기 | 높음 | 예 | 예 | 아니오 | reload | 예 | `tests/test_network_settings.py` | UI confirmation 있음 |
| `network.dhcp.apply` | DHCP 전환 | 네트워크 | 구현됨 | `set_dhcp.py`, `network_panel.py` | 쓰기 | 높음 | 예 | 예 | 아니오 | reload | 예 | `tests/test_network_settings.py` | UI confirmation 있음 |
| `pc_check.run` | PC 점검 | 작업 센터 | 구현됨 | `run_pc_checks.py`, `pc_check_viewmodel.py` | 읽기 | 낮음 | 일부 조회 | 아니오 | 해당 없음 | 예 | 아니오 | `tests/test_pc_checks.py` | 한국어 메시지 일부 ViewModel 변환 |

## 8. 위험 기능 목록

| 기능 | 변경 대상 | 위험 이유 | confirmation | test mode 차단 | dry-run | 백업/롤백 | 현재 구현 | 테스트 고정 | 후속 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 작업표시줄 실제 적용 | TaskBar 폴더, TaskBar.reg, Explorer | 사용자 고정 항목 손상 | 필수 | 예 | dry-run 별도 | 백업 필요 | use case 기본 차단 | 있음 | real apply 승인 경로 별도 설계 |
| 작업표시줄 dry-run | 리소스/대상 비교 | 낮음 | 아니오 | 아니오 | 예 | 불필요 | 구현됨 | 있음 | `.lnk` 리소스 실제 확보 확인 |
| Chrome User Data 초기화 | Chrome User Data root | 세션/확장/설정 삭제 | 예 | 예 | 아니오 | 백업 없으면 복구 어려움 | 구현됨 | 있음 | 백업 정책 검토 |
| Edge User Data 초기화 | Edge User Data root | 동일 | 예 | 예 | 아니오 | 백업 없으면 복구 어려움 | 구현됨 | 있음 | 백업 정책 검토 |
| 고정 IP 적용 | adapter IP/DNS | 네트워크 단절 | 예 | 예 | 아니오 | 기존 설정 백업 권장 | 구현됨 | 있음 | 변경 전 snapshot 저장 검토 |
| DHCP 전환 | adapter IP/DNS | 네트워크 단절 | 예 | 예 | 아니오 | 기존 설정 백업 권장 | 구현됨 | 있음 | rollback UX 검토 |
| PC 이름 변경 | computer name | 재부팅/정책 영향 | 확인 필요 | 예 | 아니오 | 기존 이름 기록 | 구현됨 | 부분 | 명시 확인 dialog 추가 검토 |
| 전원 옵션 변경 | powercfg timeout | 정책 변경 | 예 | 예 | 아니오 | 기존값 백업 권장 | 구현됨 | 부분 | 기존값 저장 |
| 23시 자동 종료 등록 | ScheduledTask | 원치 않는 종료 | 예 | 예 | 아니오 | 기존 task export 권장 | 구현됨 | 부분 | 등록/수정 diff 표시 |
| 제품키 클립보드 복사 | clipboard | 민감값 유출 | 권장 | 예 | 아니오 | 해당 없음 | 구현됨 | 있음 | clipboard clear 정책 |
| Explorer 재시작 | shell process | 작업 세션 영향 | 필수 | 예 | 아니오 | 롤백 불가 | 설정 post command에 있음 | 간접 | 사용자 확인/후처리 분리 검토 |
| 레지스트리 변경 | HKCU/HKLM | 설정 손상 | 필수 | 예 | 아니오 | reg export 권장 | 구현됨 | fake 테스트 | export/rollback 정책 |
| 휴지통 비우기 | Recycle Bin | 삭제 복구 어려움 | 예 | 예 | 아니오 | 어려움 | 구현됨 | 있음 | 메시지 강화 가능 |

## 9. 상태 모델

| 표시 상태 | 내부 예 | 의미 | 현재 구현 |
| --- | --- | --- | --- |
| 정상 | `ok`, `configured` | 원하는 상태 | `CheckStatus.OK`, `SettingStatus.status_text` |
| 주의 | `warning`, `not_configured` | 조치 필요 | PC 점검/설정 상태 |
| 오류 | `error`, `failed` | 실행 실패 | PC 점검/적용 결과 |
| 확인 불가 | `unknown`, `read_failed` | 권한/파싱/조회 실패 | 설정/PC 점검 |
| 미구현 | `status_provider_missing` | 상태 provider 없음 | `CheckSettingsStatus` |
| 미적용 | `not_configured` | 기대값과 불일치 | 설정 상태 |
| 적용됨 | `applied` | 적용 요청 성공 | `ApplyResult.status` |
| 건너뜀 | `skipped` | test mode/policy 차단 | `ApplyResult.status` |

설정 적용의 “명령 실행 성공”과 “현재 상태 검증 성공”은 다르다. 최신 구현은 `SettingsViewModel.apply_selected()`에서 적용 후 재검증을 수행한다. action-only 설정은 registry check만으로 검증할 수 없으므로 `SettingStatusProvider`를 사용한다. provider가 없으면 `상태 확인 미구현` 또는 `확인 불가`로 표시되어야 한다.

## 10. 테스트 모드 정책 요약

| 구분 | 기능 | 코드 기준 |
| --- | --- | --- |
| 허용 | PC 정보 조회 | use case guard 없음 |
| 허용 | 설정 상태 확인 | 읽기 전용 |
| 허용 | PC 점검 | 읽기 전용 check 중심 |
| 허용 | 네트워크 adapter 조회 | `ListNetworkAdapters` guard 없음 |
| 허용 | 작업표시줄 dry-run/리소스 검증 | `blocked_taskbar_apply_message(dry_run=True)` 허용 |
| 차단 | 레지스트리 변경/기본 설정 적용 | `ApplySettings` guard |
| 차단 | PC 이름 변경 | `RenamePc` guard |
| 차단 | IP/DHCP 변경 | `ApplyStaticIp`, `SetDhcp` guard |
| 차단 | 제품키 클립보드 복사 | `ActivateWindows`, `ActivateOffice` guard |
| 차단 | 프로그램 실행 | `LaunchProgram` guard |
| 차단 | Chrome/Edge User Data 초기화 | `RunPcMaintenance.delete_browser_history` guard |
| 차단 | 휴지통 비우기 | `RunPcMaintenance.empty_recycle_bin` guard |
| 차단 | 전원 옵션 변경 | `RunPcMaintenance.set_power_never` guard |
| 차단 | 자동 종료 작업 등록 | `RunPcMaintenance.set_auto_shutdown_at_23` guard |
| 차단 | 작업표시줄 실제 적용 | `ApplyTaskbarLayout(dry_run=False)` guard |

UI 버튼 비활성화도 구현되어 있지만, 문서 기준 안전 보장은 use case guard가 핵심이다.

## 11. 현재 구현/문서/테스트 불일치 감사

| 항목 | 코드 기준 실제 동작 | README 설명 | RELEASE_CHECKLIST 설명 | 테스트 고정 | 불일치/확인 필요 | 후속 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| 작업표시줄 dry-run/real apply | dry-run 기본, real apply 기본 차단 | 일치 | 일치 | 있음 | 없음 | real apply 정책 별도 설계 |
| Chrome/Edge User Data 초기화 | User Data root 전체 초기화 | 일치 | 일치 | 있음 | 없음 | 백업 정책 확인 |
| 위험 작업 confirmation | 유지보수/네트워크는 확인. PC 이름/설정 적용 confirmation은 경로별 확인 필요 | 일부 일반 설명 | 적용 전 확인 명시 | 일부 | PC 이름/설정 적용 confirmation 코드 감사 필요 | UI 확인 테스트 추가 |
| 설정 적용 후 재검증 | ViewModel에서 apply 후 check 호출 | 일치 | 일치 | 있음 | 없음 | result row dataclass 검토 |
| action-only status provider | 4개 provider 존재 | 일치 | 일치 | 있음 | 없음 | provider 범위 확장 |
| 네트워크 적용 후 reload | ViewModel reload | 일치 | 일치 | 있음 | 없음 | 비동기 reload 검토 |
| test mode button/use case guard | UI disabled + use case guard | 일치 | 일치 | 있음 | 없음 | 위험도 정책 일반화 |
| 제품키 화면/로그 노출 금지 | UI placeholder/masked, result message에 키 없음 | 일치 | 일치 | 있음 | 실제 로그 체계는 확인 필요 | logging 정책 명시 |
| UI 구조 | left navigation + stacked content | 일치 | 일치 | 부분 | 없음 | UI screenshot 수동 검증 |
| bootstrap container/factory | 분리됨 | 일치 | 일치 | 있음 | 없음 | container 타입 과도성 검토 |
| PC 점검 메시지 한국어화 | use case 일부 + ViewModel mapping | 일치 | 일치 | 있음 | 내부 예외 원문 노출 가능 | 메시지 audit |
| README 화면 설명 | 최신 구조 반영 | 해당 없음 | 일치 | 문서 검증 없음 | 없음 | 스크린샷 기반 검증 |
| RELEASE_CHECKLIST 현재 상태 | 코드와 대체로 일치 | README와 일치 | 해당 없음 | 일부 | `SettingsPanel` 언급은 실제 통합 UI가 ActionCenter 중심이라 혼동 가능 | 문서 문구 세분화 |

## 12. 후속 작업 후보

| 후보 | 이유 | 우선순위 |
| --- | --- | --- |
| `SafetyGuard`를 위험도 기반 `OperationPolicy`로 확장 | 현재는 test mode + taskbar 특수 정책 중심 | P1 |
| Chrome/Edge User Data 초기화 백업/복구 정책 | 삭제 범위가 매우 큼 | P0/P1 |
| 작업표시줄 실제 적용 승인 기능 별도 설계 | 기본 차단 유지, 백업/롤백 필요 | P1 |
| `SettingsViewModel.result_rows` tuple을 dataclass로 변경 | 4-tuple 의미가 암묵적 | P2 |
| `ActionCenterPanel` 비대화 완화 | 인증/설정/점검/유지보수가 한 파일에 집중 | P2 |
| 제품키 clipboard 자동 clear 정책 | 민감값 노출 시간 최소화 | P2 |
| 실제 Windows 통합 테스트 절차 강화 | fake 테스트만으로 권한/로캘/장치 차이 보장 불가 | P1 |
| 최신 버전 provider 네트워크 실패/캐시 정책 | PC 점검 품질 및 오프라인 UX | P2 |
