# SKHU PC Management 기능 명세서

## 1. 목적

`SKHU PC Management`는 성공회대학교 강의실/학교 PC의 초기 설정, 점검, 유지보수, 인증 준비, 네트워크 설정을 돕는 Windows 전용 관리 도구다. 현재 Python 3.12+와 PySide6 기반 데스크톱 앱으로 구현되어 있으며, PyInstaller exe 배포를 목표로 한다.

이 앱은 레지스트리, 네트워크, 예약 작업, 전원 설정, 브라우저 사용자 데이터, 제품키 클립보드 복사처럼 관리자 권한이나 명확한 사용자 확인이 필요한 작업을 포함한다. 실제 Windows 상태 변경은 반드시 `ports`와 `infrastructure/windows` adapter 뒤로 격리해야 하며, `domain`/`application` 계층이 PySide6, winreg, subprocess, WMI, netsh, powercfg 같은 구현 세부사항을 직접 import해서는 안 된다.

GUI는 얇게 유지한다. 화면은 ViewModel 상태 표시와 사용자 확인 흐름만 담당하고, 실제 판단과 실행은 use case와 port/adapter로 위임한다.

## 2. 주요 사용자

| 사용자 | 목적 |
| --- | --- |
| 학교/강의실 PC 관리자 | 다수 PC의 초기 설정, 네트워크, 전원, 예약 종료 상태를 빠르게 확인하고 조정 |
| PC 초기 세팅 담당자 | Windows/Office 인증 준비, 기본 설정 적용, PC 이름 설정 |
| 점검/유지보수 담당자 | 설치 프로그램, 브라우저 사용자 데이터, 휴지통, 전원 설정, 자동 종료 스케줄 점검 |

## 3. 실행 환경

| 항목 | 내용 |
| --- | --- |
| OS | Windows 전용 |
| 런타임 | Python 3.12+ |
| GUI | PySide6 |
| 배포 | PyInstaller onedir 기본, onefile 선택 |
| 권한 | 관리자 권한 권장. 레지스트리 HKLM, netsh, powercfg, ScheduledTasks, PC 이름 변경은 관리자 권한이 필요할 수 있음 |
| 테스트 모드 | `SKHU_PC_MANAGEMENT_TEST_MODE=1` |
| 제품키 | `src/skhu_pc_management/infrastructure/license/local_product_keys.py`는 로컬 전용. Git 커밋 금지 |

## 4. 화면 구성

현재 PySide6 UI는 `MainWindow`의 top bar, left navigation, stacked content 구조를 사용한다. 주요 화면은 `PC 정보`, `작업 센터`, `네트워크`다.

### PC 정보

역할:

- PC 이름, 사용자 이름, Windows 버전/빌드/아키텍처 표시
- CPU, RAM, GPU 표시
- 디스크 모델, 실제 GiB, 정격 용량, BusType/display type 표시
- TPM, Secure Boot, Boot Mode 표시
- PC 이름 수동 변경
- 사용자 이름 기반 PC 이름 자동 변경

관련 파일:

- `src/skhu_pc_management/presentation/qt/panels/pc_info_panel.py`
- `src/skhu_pc_management/presentation/qt/viewmodels/pc_info_viewmodel.py`
- `src/skhu_pc_management/application/use_cases/load_pc_info.py`
- `src/skhu_pc_management/application/use_cases/rename_pc.py`
- `src/skhu_pc_management/infrastructure/windows/wmi_pc_info_reader.py`

### 작업 센터

역할:

- Windows/Office 인증 준비
- 시스템 설정 선택/적용
- 설정 상태 확인
- PC 점검 결과 표시
- 유지보수 작업
- 프로그램 실행
- 강의실 PC 전용 작업
- 설정/PC 점검/Office/강의실 정책 요약 및 권장 조치 표시

관련 파일:

- `src/skhu_pc_management/presentation/qt/panels/action_center_panel.py`
- `src/skhu_pc_management/presentation/qt/viewmodels/settings_viewmodel.py`
- `src/skhu_pc_management/presentation/qt/viewmodels/pc_check_viewmodel.py`
- `src/skhu_pc_management/presentation/qt/viewmodels/activation_viewmodel.py`
- `src/skhu_pc_management/presentation/qt/maintenance_confirmations.py`

### 네트워크

역할:

- 네트워크 어댑터 조회
- 현재 네트워크 상태 확인
- 학교 기본 대역 입력
- 고정 IP 적용
- DHCP 전환
- 적용 후 어댑터 상태 재조회

관련 파일:

- `src/skhu_pc_management/presentation/qt/panels/network_panel.py`
- `src/skhu_pc_management/presentation/qt/viewmodels/network_viewmodel.py`
- `src/skhu_pc_management/application/use_cases/list_network_adapters.py`
- `src/skhu_pc_management/application/use_cases/apply_static_ip.py`
- `src/skhu_pc_management/application/use_cases/set_dhcp.py`
- `src/skhu_pc_management/infrastructure/windows/netsh_network_configurator.py`

## 5. 기능 매트릭스

상태 표기:

- 구현됨: 현재 Python 코드에 해당 use case/UI/adapter 구조가 있음
- 부분 구현: 구조는 있으나 실제 Windows 통합, 리소스, 백업/롤백 등이 확인 필요
- 확인 필요: 코드상 존재 여부 또는 실제 런타임 동작 검증 필요

| 기능 ID | 기능명 | 화면 | 현재 구현 상태 | 읽기/쓰기 | 위험도 | 관리자 권한 필요 | test mode 차단 | dry-run | 상태 확인 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pc_info.load` | PC 정보 조회 | PC 정보 | 구현됨 | 읽기 | 낮음 | 일부 WMI/보안 정보는 필요할 수 있음 | 아니오 | 해당 없음 | 해당 없음 | WMI/registry/command adapter 뒤 |
| `pc.rename.manual` | PC 이름 수동 변경 | PC 정보 | 구현됨 | 쓰기 | 높음 | 예 | 예 | 아니오 | 부분 | 재부팅 필요 가능 |
| `pc.rename.auto` | 사용자 이름 기반 PC 이름 변경 | PC 정보 | 구현됨 | 쓰기 | 높음 | 예 | 예 | 아니오 | 부분 | ViewModel에서 user name 기반 |
| `activation.windows.prepare` | Windows 인증 준비 | 작업 센터 | 구현됨 | 쓰기성 준비 | 민감 | 아니오 또는 상황별 | 예 | 아니오 | 결과만 | 제품키 복사 + `slui.exe` 실행 |
| `activation.office.prepare` | Office 인증 준비 | 작업 센터 | 구현됨 | 쓰기성 준비 | 민감 | 아니오 또는 상황별 | 예 | 아니오 | 결과만 | 제품키 복사 + `excel.exe` 실행 |
| `settings.apply` | 기본 설정 적용 | 작업 센터 | 구현됨 | 쓰기 | 높음 | 일부 예 | 예 | 일부 | 적용 후 재검증 | registry/action/taskbar dry-run 포함 |
| `settings.status.check` | 기본 설정 상태 확인 | 작업 센터 | 구현됨 | 읽기 | 낮음 | 일부 읽기 권한 | 아니오 | 해당 없음 | 예 | registry + action-only provider |
| `settings.wallpaper.default` | 기본 배경화면 설정 | 작업 센터 | 구현됨 | 쓰기 | 중간 | 상황별 | 예 | 아니오 | provider 있음 | 실제 설정은 `SystemSettingsActions` |
| `settings.edge_shortcut.delete` | Edge 바로가기 삭제 | 작업 센터 | 구현됨 | 쓰기/삭제 | 중간 | 일부 예 | 예 | 아니오 | provider 있음 | 바탕화면 shortcut/policy |
| `settings.taskbar.plan` | 작업표시줄 리소스 검증/계획 | 작업 센터 | 구현됨 | 읽기/dry-run | 낮음 | 아니오 | 아니오 | 예 | provider 있음 | 기본 설정 적용 경로는 dry-run |
| `maintenance.recycle_bin.empty` | 휴지통 비우기 | 작업 센터 | 구현됨 | 삭제 | 중간 | 상황별 | 예 | 아니오 | PC 점검 | 확인 dialog 필요 |
| `maintenance.chrome_user_data.reset` | Chrome User Data 초기화 | 작업 센터 | 구현됨 | 삭제 | 매우 높음 | 아니오 | 예 | 아니오 | PC 점검 | 방문 기록만이 아니라 User Data 전체 삭제 정책 |
| `maintenance.edge_user_data.reset` | Edge User Data 초기화 | 작업 센터 | 구현됨 | 삭제 | 매우 높음 | 아니오 | 예 | 아니오 | PC 점검 | 방문 기록만이 아니라 User Data 전체 삭제 정책 |
| `maintenance.power.never` | 전원 옵션 안 함 적용 | 작업 센터 | 구현됨 | 쓰기 | 중간 | 예 가능 | 예 | 아니오 | PC 점검 | powercfg 변경 |
| `maintenance.auto_shutdown_23.apply` | 23시 자동 종료 등록 | 작업 센터 | 구현됨 | 쓰기 | 중간 | 예 가능 | 예 | 아니오 | PC 점검 | ScheduledTasks 등록 |
| `program.chrome.launch` | Chrome 실행 | 작업 센터 | 구현됨 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 | test mode에서 프로그램 실행 차단 |
| `program.edge.launch` | Edge 실행 | 작업 센터 | 구현됨 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 |  |
| `program.potplayer.launch` | PotPlayer 실행 | 작업 센터 | 구현됨 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 |  |
| `program.bandizip.launch` | Bandizip 실행 | 작업 센터 | 구현됨 | 실행 | 낮음 | 아니오 | 예 | 아니오 | 아니오 |  |
| `network.adapters.list` | 네트워크 어댑터 조회 | 네트워크 | 구현됨 | 읽기 | 낮음 | 아니오 | 아니오 | 해당 없음 | 해당 없음 | PowerShell JSON 우선, netsh fallback |
| `network.static_ip.apply` | 고정 IP 적용 | 네트워크 | 구현됨 | 쓰기 | 높음 | 예 | 예 | 아니오 | 적용 후 reload | netsh adapter 뒤 |
| `network.dhcp.apply` | DHCP 전환 | 네트워크 | 구현됨 | 쓰기 | 높음 | 예 | 예 | 아니오 | 적용 후 reload | netsh adapter 뒤 |
| `pc_check.run` | PC 점검 실행 | 작업 센터 | 구현됨 | 읽기 | 낮음 | 일부 조회 권한 | 아니오 | 해당 없음 | 예 | 프로그램/브라우저/전원/스케줄/휴지통 |

## 6. 위험 기능 설명

| 위험 기능 | 무엇을 변경하는가 | 왜 위험한가 | 확인 dialog | test mode 차단 | 백업/롤백 | 상태 확인 방법 |
| --- | --- | --- | --- | --- | --- | --- |
| 작업표시줄 실제 적용 | TaskBar 바로가기, reg import, Explorer 재시작 가능 | 사용자 pinned taskbar 손상 가능 | 필수. 현재 기본 UI 경로는 실제 적용 비활성화 | 예 | 백업 필요. 현재 기본 정책은 dry-run | 리소스/대상 바로가기 파일명 비교 |
| Chrome User Data 초기화 | `%LOCALAPPDATA%\Google\Chrome\User Data` 전체 삭제 | 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 삭제 가능 | 필수 | 예 | 별도 백업 없으면 롤백 불가 | BrowserDataReader로 상태 조회 |
| Edge User Data 초기화 | `%LOCALAPPDATA%\Microsoft\Edge\User Data` 전체 삭제 | Chrome과 동일 | 필수 | 예 | 별도 백업 없으면 롤백 불가 | BrowserDataReader로 상태 조회 |
| 고정 IP/DHCP 변경 | 네트워크 어댑터 IP/DNS 정책 변경 | 원격 접속 끊김, 네트워크 장애 가능 | 필수 | 예 | 기존 IP 설정 백업 권장. 현재 확인 필요 | 적용 후 adapter reload |
| PC 이름 변경 | 로컬 컴퓨터 이름 변경 | 재부팅 필요, 도메인/관리 정책 영향 가능 | 필수 | 예 | 기존 이름 기록 필요 | PC 정보 재조회 |
| 전원 옵션 변경 | 화면 끄기/절전/최대 절전 timeout 변경 | 전원 정책 변경 | 필수 | 예 | 기존 powercfg 값 백업 권장 | PowerSettingsReader |
| 23시 자동 종료 작업 등록 | 예약 작업 등록/수정 | 원치 않는 자동 종료 가능 | 필수 | 예 | 기존 작업 백업/비교 권장 | ScheduledTaskReader |
| 제품키 클립보드 복사 | 제품키를 클립보드에 복사 | 민감 정보 유출 가능 | 버튼 실행 의도 확인 권장 | 예 | 클립보드 clear 정책 확인 필요 | 결과 메시지. 키 값 표시 금지 |
| Explorer 재시작 | Explorer 프로세스 종료/재시작 | 작업 중인 셸 상태 영향 | 필수 | 예 | 롤백 불가. 실행 전 고지 | 적용 후 UI 상태 확인 |
| 레지스트리 변경 | HKCU/HKLM 값 쓰기 | 시스템/사용자 설정 손상 가능 | 필수 | 예 | reg export 권장 | CheckSettingsStatus |

## 7. 상태 모델

설정/점검 상태는 UI 표시와 내부 status를 분리한다.

| 사용자 표시 | 내부 예시 | 의미 |
| --- | --- | --- |
| 정상 | `ok`, `configured` | 원하는 상태와 일치 |
| 주의 | `warning`, `not_configured` | 동작 가능하지만 조치 필요 |
| 오류 | `error`, `failed` | 실행/조회 실패 |
| 확인 불가 | `unknown`, `read_failed` | 권한/파싱/외부 실패로 판단 불가 |
| 미구현 | `status_provider_missing` | 상태 확인 provider 없음 |
| 미적용 | `not_configured` | 기대값과 현재값 불일치 |
| 적용됨 | `applied` | 적용 요청 성공 |
| 건너뜀 | `skipped` | test mode 또는 policy로 실행 차단 |

중요 원칙:

- 설정 적용의 “명령 실행 성공”과 “현재 상태 검증 성공”은 별개다.
- `SettingsViewModel.apply_selected()`는 적용 요청 후 같은 setting id 목록을 상태 확인해 현재 상태를 다시 표시한다.
- action-only 설정은 registry 값만으로 판단할 수 없으므로 `SettingStatusProvider`가 필요하다.

## 8. 테스트 모드 정책

환경변수:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
```

허용:

- PC 정보 조회
- 설정 상태 확인
- PC 점검
- 네트워크 어댑터 조회
- 작업표시줄 dry-run / 리소스 검증

차단:

- 레지스트리 변경
- PC 이름 변경
- IP/DHCP 변경
- 제품키 클립보드 복사
- 프로그램 실행
- 브라우저 User Data 초기화
- 휴지통 비우기
- 전원 옵션 변경
- 자동 종료 작업 등록
- 작업표시줄 실제 적용

## 9. 현재 알려진 주의점

| 항목 | 현재 분석 기준 |
| --- | --- |
| 작업표시줄 dry-run/real apply | `ApplyTaskbarLayout`은 dry-run은 허용하지만 real apply는 `SafetyGuard.allow_real_taskbar_apply=False` 기본 정책에서 차단한다. 실제 적용 경로를 열려면 백업/확인/롤백 정책이 먼저 필요하다. |
| 브라우저 User Data 초기화 표현 | 유지보수 기능은 “방문 기록 삭제”가 아니라 Chrome/Edge `User Data` 전체 초기화로 문서화해야 한다. |
| 설정 적용 후 상태 재검증 | `SettingsViewModel`은 적용 후 `CheckSettingsStatus`를 다시 호출한다. 이후 수정 시 이 흐름을 깨지 말아야 한다. |
| action-only 설정 상태 확인 | 기본 배경화면, Edge 바로가기, 작업표시줄, 암호 만료 provider가 존재한다. provider 없는 설정은 한국어로 상태 확인 미구현을 표시해야 한다. |
| 네트워크 적용 후 reload | `NetworkViewModel`은 static IP/DHCP 성공 후 adapter list를 재조회한다. UI freeze 가능성은 추후 비동기화 검토 대상이다. |
| 한국어 메시지 통일 | 주요 ViewModel/use case 메시지는 한국어화되어 있으나, 내부 예외 문자열은 원문이 포함될 수 있다. 사용자-facing 메시지 검수 필요. |
