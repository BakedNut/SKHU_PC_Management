# SKHU PC Management

## 개요

SKHU PC Management는 성공회대학교 강의실 Windows PC의 기본 설정, 네트워크 설정, 인증 준비, PC 점검, 유지보수 작업을 한 화면에서 수행하기 위한 PySide6 기반 데스크톱 관리 도구입니다.

이 저장소의 현재 앱은 Python 3.12+와 PySide6로 동작합니다. 과거 C# 버전의 동작은 참고 자료로만 남아 있으며, 실제 실행 코드는 `src/skhu_pc_management` 아래의 Python 구현을 기준으로 합니다.

## 주요 기능

- PC 정보 조회: PC 이름, 사용자, Windows 버전, CPU/RAM/GPU, 디스크, 네트워크, TPM, Secure Boot, 부팅 모드.
- PC 이름 변경: 앱 내부에서 이름을 직접 바꾸지 않고 Windows 설정의 시스템 정보 화면을 열어 OS 기본 UI에서 변경.
- Windows/Office 인증 준비: 제품키를 화면에 표시하지 않고 클립보드에 복사한 뒤 Windows 인증 창 또는 Excel 실행.
- 시스템 설정 적용: 탐색기, 바탕화면 아이콘, Edge 바로가기, 작업표시줄, 암호 입력 생략, 빠른 시작, 암호 만료 정책, Windows 11 시작 메뉴 설정.
- 작업표시줄 아이콘 설정: `resources/TaskBar`와 `TaskBar.reg`를 사용하며, Chrome은 `Google Chrome.lnk` 이름과 실제 `chrome.exe` 대상 검증을 기준으로 처리.
- 네트워크 관리: 어댑터 조회, 현재 IP 상태 표시, 고정 IP 적용, DHCP 전환.
- PC 점검: 설치 프로그램/버전, 브라우저 사용자 데이터, 전원 옵션, 23시 자동종료 스케줄, 휴지통 상태.
- 강의실 PC 작업: 전원 옵션 `안 함` 적용, 23시 자동종료 스케줄 등록, 자동종료 취소 바로가기 배치.
- 즉시 실행 도구: Chrome, Edge, PotPlayer, Bandizip 실행과 Chrome/Edge 사용자 데이터 초기화.

## 실행 환경

- Windows 전용 GUI 앱입니다.
- 시스템 설정, 네트워크 변경, 작업 스케줄러 등록, 인증 준비 작업은 관리자 권한이 필요할 수 있습니다.
- 개발 환경은 Python 3.12 이상을 사용합니다.
- 주요 의존성은 `pyproject.toml` 기준으로 PySide6, pywin32, WMI, PyInstaller, pytest입니다.
- PyInstaller onedir 배포본은 UAC 관리자 권한 요청 메타데이터를 포함합니다.

## 빠른 시작

개발 환경 설치와 실행:

```powershell
python -m pip install -e .
python -m pytest
python -m skhu_pc_management.main
```

테스트 모드 실행:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

배포본 실행:

```powershell
.\dist\SKHU_PC_Management\SKHU_PC_Management.exe
```

## 화면별 사용법

앱은 시작 속도를 위해 PC 기본 정보만 먼저 자동 로드합니다. 작업 센터와 네트워크 정보는 각 탭에 처음 진입할 때 한 번 자동으로 불러오며, 이후에는 사용자가 새로고침 버튼을 눌렀을 때 다시 조회합니다.

### PC 정보

`PC 정보` 화면은 현재 장비의 기본 정보와 보안/호환 상태를 표시합니다.

- `새로고침`은 PC 정보를 다시 조회합니다.
- OS/CPU는 registry fast path를 먼저 사용하고, 정보가 부족하면 WMI fallback을 사용합니다. Windows 11 build(`22000+`)인데 registry `ProductName`이 Windows 10으로 남아 있으면 Windows 11로 보정합니다.
- WMI client는 namespace별로 재사용합니다. `SKHU_PC_MANAGEMENT_PROFILE_STARTUP=1`일 때 WMI class별 소요 시간과 실패 class/namespace가 짧게 출력됩니다.
- RAM 총량은 WMI module capacity 합계를 우선하며, WMI module 정보가 비어 있을 때만 `GlobalMemoryStatusEx` fast total을 fallback으로 사용합니다. RAM 클럭 표시는 `Win32_PhysicalMemory.Speed`만 사용하고 `ConfiguredClockSpeed`는 사용하지 않습니다. `Speed`가 없으면 `클럭 알 수 없음`으로 표시합니다.
- TPM은 `Win32_Tpm.SpecVersion` WMI 값을 우선 사용합니다. registry `Services\TPM\Start`는 설치 여부 fallback에만 쓰며 `disabled` 또는 `2.0 (disabled)`로 표시하지 않습니다.
- 디스크는 Storage WMI 보강 정보를 사용하되, Storage WMI가 비거나 실패해도 `Win32_DiskDrive` 기반으로 model, actual GiB, rated size, NVMe/SSD/HDD summary를 표시합니다. USB/removable disk는 제외합니다.
- IP 주소와 MAC 주소는 임의의 첫 번째 어댑터가 아니라 현재 인터넷 연결 조건을 만족하는 실제 물리 Ethernet 또는 Wi-Fi 어댑터 기준으로 표시합니다.
- Ethernet과 Wi-Fi가 동시에 조건을 만족하면 Ethernet을 우선하며, Ethernet이 IPv4 주소와 기본 게이트웨이를 갖지 못하고 Wi-Fi만 조건을 만족하면 Wi-Fi를 표시합니다.
- 가상 어댑터, VM/VPN, Docker/WSL, Bluetooth, Loopback/Tunnel 계열은 PC 정보 탭의 대표 IP/MAC 표시 대상에서 제외합니다.
- 조건을 만족하는 어댑터가 없으면 IP 주소와 MAC 주소는 `알 수 없음`으로 표시합니다.
- `PC 이름 변경`은 Windows 설정의 시스템 정보 화면을 엽니다. 실제 이름 변경과 재부팅 안내는 Windows 설정 UI에서 처리합니다.
- 성공 시 별도 완료 팝업은 띄우지 않고 Windows 설정 화면이 열리는 것으로 결과를 확인합니다.
- Windows 설정 화면은 `ms-settings:about` URI를 직접 열며, `cmd` 또는 PowerShell 콘솔 창을 띄우지 않습니다.
- 앱은 더 이상 `QInputDialog`로 새 PC 이름을 입력받거나 `Rename-Computer`를 UI에서 직접 실행하지 않습니다.

### 작업 센터

`작업 센터`는 인증, 시스템 설정, PC 점검, 즉시 실행 도구, 강의실 PC 작업을 모은 화면입니다.

- `인증` 카드에서 Windows 11/10 또는 Office 2024/2021을 선택하고 버튼을 누르면 제품키가 클립보드에 복사되고 인증 준비 화면이 열립니다.
- `시스템 설정 선택`에서 설정을 선택한 뒤 `선택한 설정 적용`을 누르면 실제 변경을 요청하고, 이후 표시 대상 전체의 현재 상태를 다시 확인합니다.
- `작업 센터` 탭 첫 진입 시 설정 상태와 PC 점검을 한 번 자동으로 불러옵니다.
- `상태 새로고침`은 설정 상태 확인과 PC 점검을 병렬로 실행한 뒤 한 번만 화면을 갱신합니다. 설정 provider 내부도 가능한 범위에서 병렬 실행하며, 개별 실패는 해당 항목의 unknown/error 상태로 격리합니다.
- 외부 프로세스 호출은 줄였습니다. 전원 옵션은 `powercfg /q SCHEME_CURRENT` 단일 조회를 우선하고, Scheduled Task는 `schtasks` CSV fast path 후 PowerShell fallback을 사용합니다. 암호 만료는 `net accounts` fast path를 우선하며, 작업표시줄 shortcut target 상세 확인은 기본 상태 확인에서 생략합니다.
- 설정 상태 표는 `설정 항목 | 현재 상태 | 상세` 3개 열로 표시됩니다. 실행 로그가 아니라 최종 상태 provider 결과를 보여줍니다.
- Windows 10 선택 상태에서는 Windows 11 전용 시작 메뉴 항목이 선택/표시 대상에서 제외됩니다.
- Explorer 재시작은 변경 사항 반영을 위한 best-effort 후처리입니다. Explorer 실행 결과는 설정 상태 판정 기준이 아닙니다.
- `PC 점검 결과` 표에서는 Office 설치 확인 행을 표시하지 않습니다. Office 감지 결과는 인증 카드의 Office row에만 표시됩니다.
- Chrome/Edge/PotPlayer/Bandizip 실행은 성공 시 완료 팝업을 띄우지 않고, 실패 시에만 경고 팝업을 표시합니다.
- Chrome/Edge/PotPlayer/Bandizip 실행은 외부 프로그램 실행만 수행하며 전체 설정 상태/PC 점검을 다시 실행하지 않습니다.

### 네트워크

`네트워크` 화면은 어댑터 목록과 현재 네트워크 상태 표를 표시합니다.

- `새로고침`은 네트워크 어댑터를 다시 조회합니다.
- `네트워크` 탭 첫 진입 시 어댑터 정보를 한 번 자동으로 불러옵니다.
- 어댑터 목록은 `GetAdaptersAddresses` fast path를 우선 사용합니다. 실제 Ethernet/Wi-Fi를 우선하고 가상/VPN/VM/Docker/WSL/Bluetooth/Loopback/Tunnel 계열은 제외합니다.
- gateway, DHCP 여부, DNS, subnet mask는 가능한 경우 registry TCP/IP interface 값으로 보강합니다. 일부 값이 비어 있어도 그것만으로 PowerShell fallback을 강제하지 않습니다.
- PC 정보 탭의 대표 IP/MAC 선택 기준은 표시용 로직이며, 이 화면의 어댑터 목록 조회와 고정 IP/DHCP 설정 동작을 변경하지 않습니다.
- `학교 기본 대역 입력`은 고정 IP 입력 폼에 기본 대역 값을 채웁니다.
- `IP 설정 적용`과 `DHCP 전환`은 실제 네트워크 설정을 변경하므로 확인 대화상자를 거칩니다.
- 적용 성공 후 같은 어댑터를 다시 선택하고 현재 네트워크 상태 표를 다시 불러옵니다.

## 안전 모드 / 테스트 모드

Computer Use, UI 자동화, 수동 탐색 테스트에서는 반드시 테스트 모드를 사용하세요.

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

테스트 모드에서는 읽기 전용 기능은 유지하고 실제 변경성 작업은 UI와 use case에서 차단합니다. 공통 메시지는 다음과 같습니다.

```text
테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.
```

차단되는 대표 작업:

- 시스템 설정 적용과 레지스트리 변경.
- 작업표시줄 실제 적용.
- 고정 IP 적용, DHCP 전환.
- Windows/Office 인증 준비와 제품키 클립보드 복사.
- Chrome/Edge 사용자 데이터 초기화.
- 휴지통 비우기.
- 전원 옵션 변경, 23시 자동종료 등록.
- 프로그램 실행.
- Windows 설정의 PC 이름 변경 화면 열기.

허용되는 대표 작업:

- PC 정보 조회.
- 설정 상태 확인.
- 네트워크 어댑터 조회.
- PC 점검.
- 작업표시줄 리소스 검증과 dry-run 계획 확인.

## 제품키 설정

실제 제품키는 커밋하지 않습니다.

1. `src/skhu_pc_management/infrastructure/license/local_product_keys.example.py`를 같은 폴더의 `local_product_keys.py`로 복사합니다.
2. 로컬 빌드/배포 담당자가 실제 값을 채웁니다.
3. `local_product_keys.py`는 Git에 포함하지 않습니다.

지원하는 이름:

- `WINDOWS_11_PRODUCT_KEY`
- `WINDOWS_10_PRODUCT_KEY`
- `OFFICE_2024_PRODUCT_KEY`
- `OFFICE_2021_PRODUCT_KEY`
- `WINDOWS_PRODUCT_KEY`, `OFFICE_PRODUCT_KEY` fallback

UI는 제품키 값을 화면에 표시하지 않습니다. 버튼 실행 시에만 클립보드에 복사합니다.

## 작업표시줄 리소스

작업표시줄 설정은 다음 리소스를 사용합니다.

```text
resources\
  TaskBar.reg
  TaskBar\
    File Explorer.lnk
    Google Chrome.lnk
```

정책:

- `resources/TaskBar/*.lnk` 중 Chrome 관련 항목은 target에서 항상 `Google Chrome.lnk`로 취급합니다.
- Chrome은 패키징된 shortcut을 그대로 복사하는 대신 현재 PC의 실제 `chrome.exe`를 찾아 `Google Chrome.lnk`를 생성하는 경로를 우선 사용합니다.
- 시작 메뉴 shortcut 복사는 fallback이며, 내부 TargetPath가 실제 파일일 때만 사용합니다.
- Chrome shortcut 생성/검증에 실패해도 전체 작업표시줄 적용은 실패하지 않고 Chrome 고정만 건너뜁니다.
- `TaskBar.reg` import 실패와 일반 shortcut 삭제/복사 실패는 실제 실패로 처리합니다.
- Explorer 재시작 실패는 적용 실패가 아니라 후처리 실패로 취급합니다.
- 상태 확인 provider는 target shortcut 이름과 `Google Chrome.lnk`의 TargetPath 유효성을 확인합니다.

작업표시줄 실제 적용은 현재 사용자 TaskBar pinned 폴더의 기존 `.lnk` 삭제, 리소스 복사/동적 생성, `TaskBar.reg` import, Explorer 재시작을 수행할 수 있습니다. 실제 Windows Shell pin 상태는 Windows 정책과 캐시의 영향을 받을 수 있으므로 테스트 PC에서 확인해야 합니다.

## 빌드 및 배포

공식 onedir 빌드:

```powershell
.\scripts\build.ps1
```

직접 빌드:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller SKHU_PC_Management.spec --noconfirm
```

배포본 검증:

```powershell
.\scripts\check_dist.ps1
```

선택적 onefile 빌드:

```powershell
.\scripts\build.ps1 -OneFile
```

예상 onedir 산출물:

```text
dist\SKHU_PC_Management\
  SKHU_PC_Management.exe
  _internal\
    resources\
      images\skhu_logo.ico
      TaskBar.reg
      TaskBar\*.lnk
  README_RELEASE.txt
```

배포 전 확인:

- `resources/`가 배포본에 포함되어야 합니다.
- `resources/23시 자동종료 취소.lnk`가 포함되어야 합니다.
- `resources/TaskBar.reg`와 `resources/TaskBar/*.lnk`가 포함되어야 합니다.
- 제품키를 내장해야 하는 배포 정책이라면 빌드 머신에만 `local_product_keys.py`를 준비합니다.

## 배포 후 확인

- 관리자 권한 실행과 UAC 프롬프트 확인.
- PC 정보 자동 로드 확인.
- PC 정보 탭의 IP/MAC이 현재 인터넷 연결 조건을 만족하는 물리 Ethernet 또는 Wi-Fi 기준으로 표시되는지 확인.
- 설정 상태 확인과 `설정 항목 | 현재 상태 | 상세` 표 확인.
- Windows 10 선택 시 Win11 전용 시작 메뉴 항목 미표시 확인.
- Windows 다크 테마에서 앱 팝업의 본문과 버튼 텍스트가 읽히는지 확인.
- 제품키가 화면에 표시되지 않는지 확인.
- Windows 인증 창과 Excel 실행 확인.
- 네트워크 어댑터 조회 확인.
- 테스트 PC에서만 고정 IP/DHCP 적용 확인.
- 23시 자동종료 스케줄 점검: 작업 없음은 `주의`, 조회 실패는 `알 수 없음`.
- 23시 자동종료 적용 후 바탕화면의 `23시 자동종료 취소.lnk`가 리소스 원본과 같은지 확인.
- 작업표시줄 적용 후 `Google Chrome.lnk`가 실제 `chrome.exe`를 가리키는지 확인.
- Chrome/Edge 사용자 데이터 초기화는 폐기 가능한 테스트 계정에서만 확인.

## 프로젝트 구조

```text
src/skhu_pc_management/
  domain/                 순수 모델과 설정/점검 정의
  application/            use case, SafetyGuard, orchestration
  ports/                  외부 시스템 Protocol
  infrastructure/
    windows/              Windows registry, PowerShell, WMI, filesystem adapter
    license/              제품키 provider와 로컬 템플릿
  presentation/
    qt/                   PySide6 UI, ViewModel, startup coordinator
resources/                아이콘, TaskBar.reg, 바로가기 리소스
scripts/                  빌드와 dist 검증 스크립트
tests/                    fake 기반 단위 테스트
docs/                     상세 설계/정책 문서
```

아키텍처 경계:

- `domain`과 `application`은 PySide6, winreg, ctypes, WMI, netsh, powercfg, subprocess를 직접 import하지 않습니다.
- Windows 동작은 `ports`와 `infrastructure/windows` adapter 뒤에 둡니다.
- PySide6 GUI는 표시, 사용자 확인, ViewModel 호출에 집중합니다.
- 실제 Windows 상태 변경은 단위 테스트에서 실행하지 않고 fake로 검증합니다.

## 개발/테스트

프로파일링:

```powershell
$env:SKHU_PC_MANAGEMENT_PROFILE_STARTUP = "1"
$env:SKHU_PC_MANAGEMENT_PROFILE_TABS = "1"
python -m skhu_pc_management
```

`SKHU_PC_MANAGEMENT_PROFILE_STARTUP=1`은 PC 정보 단계와 WMI class별 시간을 출력합니다. `SKHU_PC_MANAGEMENT_PROFILE_TABS=1`은 네트워크 탭, 작업 센터, 전원/예약 작업/provider 구간 시간을 출력합니다.

전체 테스트:

```powershell
python -m pytest
```

UI helper 테스트:

```powershell
python -m pytest tests/test_ui_helpers.py
```

PyInstaller 빌드:

```powershell
python -m PyInstaller SKHU_PC_Management.spec --noconfirm
```

개발 원칙:

- 위험 작업은 `SafetyGuard`와 UI 확인 흐름을 모두 고려합니다.
- 실제 Windows 통합 테스트는 전용 테스트 PC에서만 수행합니다.
- 제품키, 사용자 경로, 민감 로그를 문서/테스트 출력에 남기지 않습니다.

## 보안 및 운영 주의사항

- 실제 제품키를 코드, 문서, 로그, 테스트 출력에 남기지 마세요.
- Chrome/Edge 사용자 데이터 초기화는 `User Data` 폴더 전체 삭제입니다. 방문 기록만 삭제하는 기능이 아닙니다.
- 작업표시줄 적용은 registry import와 Explorer 재시작을 포함할 수 있습니다.
- 네트워크 변경은 원격 접속 또는 수업 환경을 끊을 수 있습니다.
- 테스트 모드에서 UI 자동화를 수행하세요.

상세 설계와 정책은 `docs/` 문서를 참고하세요.
