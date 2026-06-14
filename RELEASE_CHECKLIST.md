# RELEASE_CHECKLIST

이 문서는 Python/PySide6 마이그레이션 현재 구현을 기준으로 한 배포 전 통합 점검표다. 실제 Windows 설정 변경, 레지스트리 변경, IP 변경, 작업표시줄 변경, 인증 프로세스 실행은 테스트에서 수행하지 않는다.

## 1. 앱 시작/초기화

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| 관리자 권한 확인 | `AdminPrivilegeChecker` port와 Windows adapter로 분리됨. 관리자 권한이 없어도 앱은 계속 실행하고 경고를 표시함 | `tests/test_startup_coordinator.py` | 일반 권한/관리자 권한으로 실제 exe 실행 |
| PC 정보 자동 로드 | `StartupCoordinator`가 시작 시 `LoadPcInfoUseCase`를 호출함 | fake use case 기반 startup 테스트 | 실제 WMI 조회 성공/실패 화면 |
| 기본 설정 상태 자동 확인 | `StartupCoordinator`가 시작 시 설정 상태 확인을 호출함 | startup 테스트, settings tests | 실제 레지스트리 읽기 권한 부족 시 메시지 |
| PC 점검 자동 실행 | `StartupCoordinator`가 시작 시 PC 점검을 호출함 | startup 테스트 | 실제 Windows PC에서 점검 소요 시간 |
| 초기화 실패 격리 | 한 영역 실패가 전체 초기화를 중단하지 않도록 결과에 error를 누적함 | startup 실패 테스트 | 실제 WMI/powercfg 실패 환경 |

## 2. 기본 설정

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| 상태 확인 | 체크 여부와 무관하게 전체 설정 상태를 확인함 | settings viewmodel/use case tests | 실제 레지스트리 값 표시 |
| 전체 선택/해제 | `SettingsPanel`에 전체 선택/전체 해제 버튼 있음 | settings panel/viewmodel tests | 실제 UI 클릭 |
| 적용 전 확인 | 선택 항목 적용 전 `QMessageBox` 확인을 요구함 | 코드 점검 | 실제 UI 확인 흐름 |
| 선택 없음 안내 | 선택된 항목이 없으면 적용하지 않고 안내 메시지를 표시함 | settings tests | 실제 UI 메시지 |
| 실패 항목 메시지 | setting id별 결과와 실패 메시지를 표시함 | apply settings tests | 권한 부족 HKLM 항목 메시지 |
| 테스트 격리 | registry는 `Registry` port/fake로 테스트함 | tests 전체 | 없음 |

## 3. 네트워크

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| 어댑터 목록 로드 | PowerShell `Get-NetAdapter | ConvertTo-Json` 우선, netsh fallback | `tests/test_network_settings.py` | 실제 한국어 Windows 출력 |
| 물리 Ethernet/Wi-Fi 표시 | Realtek Ethernet, Wi-Fi 예시가 포함되도록 필터 완화됨 | PowerShell JSON fake tests | 실제 장치명 다양성 |
| 가상 어댑터 제외 | bluetooth, virtualbox, vmware, hyper-v, vpn, tailscale, loopback, isatap, teredo 등 제외 | filter tests | 회사 VPN 정책에 따라 예외 필요 여부 |
| DHCP 전환 | `NetworkConfigurator` port 뒤에서 netsh 명령 구성 | fake command runner tests | 관리자 권한 실제 적용 |
| 정적 IP 적용 | IP/subnet/gateway/DNS validation 후 port 호출 | network tests | 실제 적용 전 사용자 확인 |
| 실제 명령 격리 | unit test는 fake command runner만 사용 | tests 전체 | 통합 테스트는 별도 PC 필요 |

## 4. PC 정보

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| CPU/RAM/OS 표시 | `PcInfoReader` port와 `WmiPcInfoReader` adapter로 분리 | `tests/test_load_pc_info.py` | 실제 Windows 버전/빌드 표시 |
| 디스크 확장 정보 | 실제 GiB, 정격 용량, BusType, display type 표시 모델 지원 | disk tests | NVMe/SATA/USB 실장 PC |
| WMI fallback | WMI 값 누락/실패 시 Unknown/None 기반 fallback | fake WMI tests | WMI 서비스 비정상 환경 |

## 5. PC 점검

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| Chrome/Edge/PotPlayer/Bandizip 설치/버전 | 설치 여부, 로컬/최신 버전 비교 구조와 provider 분리 | pc check tests | 실제 최신 버전 provider 네트워크 경로 |
| 브라우저 기록 확인 | Default, Profile *, Guest Profile과 5MiB threshold 조기 종료 | browser data tests | 실제 사용자 프로필 권한 |
| 전원 설정 상세 메시지 | 화면 끄기/절전/최대 절전 값을 한국어로 표시 | power settings tests | 실제 powercfg 한국어 출력 |
| 23시 자동종료 스케줄 | ScheduledTasks JSON 조회 port와 판정 로직 구현 | scheduled task tests | 실제 작업 스케줄러 상태 |
| 메시지 한국어 | ViewModel/presentation에서 상태와 주요 메시지 한국어 변환 | pc check viewmodel tests | UI 전체 문구 검수 |

## 6. 인증

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| Windows 10/11 선택 | 인증 탭에서 버전 선택 후 해당 key id 요청 | activation tests | 실제 local key 파일이 있는 PC |
| Office 2021/2024 선택 | 인증 탭에서 버전 선택 후 해당 key id 요청 | activation tests | Excel 설치/미설치 환경 |
| 제품키 화면 노출 금지 | 결과 메시지에 제품키 문자열을 포함하지 않음 | activation tests | UI 육안 확인 |
| key 파일 누락 안내 | `local_product_keys.py` 누락 시 한국어 오류 | activation tests | 실제 배포 PC |
| clipboard/process 격리 | 테스트는 fake clipboard/process launcher 사용 | activation tests | 실제 클립보드/프로세스 실행 |
| secret Git 제외 | `local_product_keys.py`는 `.gitignore`에 포함됨 | `.gitignore` 점검 | release artifact 포함 정책 |

## 7. 리소스/작업표시줄/로고

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| 앱 아이콘/로고 | `resources/images/skhu_logo.ico`를 MainWindow 아이콘/상단 로고로 사용 | 코드 점검 | 실제 exe 아이콘 표시 |
| ResourceResolver | 개발 경로와 PyInstaller `_MEIPASS`/실행 경로를 확인 | resource resolver tests | onedir/onefile 실제 실행 |
| resources 포함 | spec/build script가 `resources;resources` 포함 | spec/build script 점검 | dist 폴더 내부 확인 |
| 작업표시줄 validation | `TaskBar.reg`, `TaskBar/*.lnk` 존재를 검증 | taskbar tests | 실제 `.lnk` 리소스 준비 |
| 작업표시줄 적용 | 현재 dry-run plan만 수행하고 실제 적용은 TODO로 차단 | taskbar tests | 실제 적용 구현 전 별도 승인 필요 |
| destructive 테스트 금지 | regedit, Explorer 재시작, TaskBar 폴더 변경 없음 | taskbar tests | 없음 |

## 8. Busy/중복 실행 방지

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| startup 중복 방지 | `BusyCoordinator.try_begin()`으로 중복 초기화 방지 | busy/startup tests | 빠른 연속 클릭 UI |
| 장시간 작업 guard | 주요 패널 버튼이 전역 busy를 확인함 | busy tests, 코드 점검 | 실제 작업 중 버튼 disabled 체감 |
| 예외 후 해제 | panel 작업은 `try/finally`로 busy 해제 | busy tests | 예외 발생 UI |
| 진행 메시지 | MainWindow 상태 영역에 busy message 표시 | 코드 점검 | 실제 화면 표시 |

## 8-1. 안전한 UI 테스트 모드

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| 환경변수 | `SKHU_PC_MANAGEMENT_TEST_MODE=1`이면 테스트 모드 활성화 | `tests/test_test_mode_safety.py` | 패키지 exe 실행 |
| 위험 버튼 비활성화 | 기본 설정 적용, 정적 IP, DHCP, 인증 준비, 작업표시줄 적용 버튼 비활성화 | 코드 점검 | 실제 UI 표시 |
| 직접 use case 호출 차단 | 위험 use case가 port 호출 전 차단 메시지를 반환 | `tests/test_test_mode_safety.py` | 없음 |
| 허용 기능 유지 | PC 정보, 설정 상태, 어댑터 조회, PC 점검, 리소스 검증, dry-run 허용 | 기존 테스트 | 실제 UI 탐색 |
| 안내 메시지 | UI 상단/상태에 테스트 모드 안내 표시 | 코드 점검 | 실제 UI 표시 |

UI 자동화 또는 Computer Use 테스트 실행 예:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

## 9. 테스트

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| pytest 전체 실행 | 배포 전 매번 `python -m pytest` 실행 | 명령 실행 결과 | Python PATH 구성 |
| 실제 Windows API 격리 | unit test는 fake/monkeypatch 기반 | architecture/tests 점검 | 별도 통합 테스트 marker 필요 |
| fake adapter 테스트 | registry, command runner, product key, network, taskbar 모두 fake 테스트 보유 | tests 폴더 | 커버리지 정량 측정은 미구성 |

## 10. PyInstaller

| 항목 | 현재 상태 | 확인 방법 | 남은 수동 검증 |
| --- | --- | --- | --- |
| onedir 빌드 | 공식 빌드: `.\scripts\build.ps1` | script/spec 점검 | 실제 빌드 실행 |
| onefile 빌드 | 참고 빌드: `.\scripts\build.ps1 -OneFile` | README/script 점검 | onefile 실행 속도/리소스 경로 |
| UAC 관리자 권한 | spec의 `uac_admin=True`, CLI의 `--uac-admin` | spec/script 점검 | exe 실행 시 UAC prompt |
| GUI no console | spec의 `console=False`, CLI의 `--windowed` | spec/script 점검 | 콘솔 창 미표시 |
| hidden imports | wmi, win32com, pythoncom, pywintypes 및 local key 조건부 포함 | spec/script 점검 | WMI runtime import |
| resources 포함 | `resources/` 전체 포함 | spec/script 점검 | `dist\SKHU_PC_Management\_internal\resources` 확인 |
| spec Git 정책 | `*.spec` ignore + `!SKHU_PC_Management.spec` 예외 | `.gitignore` 점검 | staging 확인 |

## 11. 릴리즈 빌드/배포 패키지

| 항목 | 확인 내용 | 명령/경로 | 판정 기준 |
| --- | --- | --- | --- |
| spec 존재 | 고정 spec 파일이 Git 대상인지 확인 | `SKHU_PC_Management.spec` | 존재해야 함 |
| 관리자 권한 | exe metadata에 UAC 요청 포함 | spec `uac_admin=True` | 설정되어야 함 |
| 콘솔 숨김 | GUI 앱으로 콘솔 미표시 | spec `console=False` | 설정되어야 함 |
| 앱 아이콘 | exe 아이콘 포함 | spec `icon=resources/images/skhu_logo.ico` | 설정되어야 함 |
| PySide6 | QtCore/QtGui/QtWidgets hidden import와 PyInstaller hook 사용 | spec hiddenimports | 빌드 후 실행 확인 |
| WMI/pywin32 | 동적 import 누락 방지 | `wmi`, `win32com`, `pythoncom`, `pywintypes` | hiddenimports 포함 |
| resources | 배포본 resources 포함 | `dist\SKHU_PC_Management\_internal\resources` | 폴더 존재 |
| 배포 안내 | 배포본 root에 안내 파일 포함 | `README_RELEASE.txt` | 존재 |
| dist 검증 | 필수 파일 확인 | `.\scripts\check_dist.ps1` | exit code 0 |
| 민감 파일 | local key 파일 Git 제외 | `.gitignore` | `local_product_keys.py` 포함 |

권장 릴리즈 빌드 순서:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m PyInstaller SKHU_PC_Management.spec --noconfirm
.\scripts\check_dist.ps1
```

공식 스크립트 사용 시:

```powershell
.\scripts\build.ps1
.\scripts\check_dist.ps1
```

선택적 onefile 빌드:

```powershell
.\scripts\build.ps1 -OneFile
```

배포 대상 폴더 구조:

```text
dist\
  SKHU_PC_Management\
    SKHU_PC_Management.exe
    _internal\
      resources\
        images\
          skhu_logo.ico
        TaskBar.reg
        TaskBar\
          *.lnk
    README_RELEASE.txt
```

`resources\TaskBar\*.lnk`가 없으면 작업표시줄 리소스 검증은 경고를 표시한다. 이 상태에서도 앱 자체 배포는 가능하지만 작업표시줄 레이아웃 리소스가 완성된 것은 아니다.

## 현재 통합 점검 기록

2026-06-14 기준 Codex 환경에서 확인한 결과:

- `python -m pytest`: 실패. 현재 셸 PATH에 `python` 명령이 없음.
- 번들 Python + `.test_deps` 기반 pytest: `147 passed`.
- `python -m PyInstaller --version`: 현재 테스트 런타임에는 PyInstaller 모듈이 설치되어 있지 않아 실패. 패키징 PC에서는 먼저 `python -m pip install -e .` 또는 동등한 의존성 설치를 수행해야 한다.
- `src/skhu_pc_management/infrastructure/license/local_product_keys.py`: 없음. 정상 상태이며 Git에 포함하면 안 된다.
- `resources/images/skhu_logo.ico`: 있음.
- `resources/TaskBar.reg`: 있음.
- `resources/TaskBar/*.lnk`: 없음. 현재 작업표시줄 리소스 검증은 `.lnk` 누락 경고를 표시하는 상태가 정상이다.

## 배포 전 실행 명령

```powershell
python -m pytest
python -m PyInstaller --version
.\scripts\build.ps1
```

선택적으로 onefile 결과도 확인한다.

```powershell
.\scripts\build.ps1 -OneFile
```

## 실제 Windows 테스트 PC에서 확인할 항목

- 관리자 권한이 없는 상태와 있는 상태에서 시작 경고/초기화 흐름.
- 실제 WMI 기반 PC 정보와 디스크 BusType/정격 용량 표시.
- 실제 PowerShell Get-NetAdapter 결과에서 물리 Ethernet/Wi-Fi 표시와 가상 어댑터 제외.
- 정적 IP/DHCP 적용 전 확인 대화상자와 관리자 권한 실패 메시지.
- powercfg, ScheduledTasks, 브라우저 기록, 설치 프로그램 버전 점검 메시지.
- `local_product_keys.py`가 없는 경우 인증 탭 안내 메시지.
- 로컬 빌드 머신에만 `local_product_keys.py`를 둔 상태의 PyInstaller 패키징.
- 작업표시줄 리소스 validation/dry-run 결과와 실제 적용 차단 상태.
- onedir/onefile exe에서 resources, 아이콘, 로고 표시.
