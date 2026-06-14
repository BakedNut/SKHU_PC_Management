# SKHU PC Management

기존 C# WPF `SKHU_PC_Management` 앱을 Python + PySide6로 다시 작성하기 위한 스캐폴드입니다.

## 범위

이 저장소에는 기존 데스크톱 도구를 Python + PySide6로 다시 작성한 코드가 포함되어 있습니다. Windows 상태를 변경하는 작업은 포트/어댑터 뒤로 격리하며, Windows 장비에서 통합 시나리오를 명시적으로 실행하는 경우가 아니라면 fake로 테스트해야 합니다.

## 아키텍처

- `domain`: 프레임워크나 Windows 의존성이 없는 dataclass 모델과 정의입니다.
- `application`: 작은 단위의 의존성 주입 기반 유스케이스입니다.
- `ports`: 외부 시스템을 위한 `typing.Protocol` 계약입니다.
- `infrastructure`: Windows 및 라이선스 어댑터입니다.
- `presentation`: 얇은 PySide6 GUI입니다.

## 개발

```powershell
python -m pip install -e .
python -m pytest
python -m skhu_pc_management.main
```

`python`은 Python 3.12 이상을 가리켜야 합니다. 모든 릴리스 후보 전에 테스트를 실행하고, Windows 상태를 변경하는 검사는 Windows 테스트 PC에서 수동 통합 테스트를 의도적으로 실행하는 경우가 아니라면 fake 뒤에 두세요.

## 안전 UI 테스트 모드

Computer Use, UI 자동화, 실제 PC에서의 탐색 테스트를 사용할 때는 앱 실행 전에 `SKHU_PC_MANAGEMENT_TEST_MODE=1`을 설정하세요. 이 모드에서는 읽기 전용 검사는 계속 사용할 수 있지만, Windows 상태를 변경할 수 있는 버튼은 비활성화됩니다.

PowerShell:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

패키징된 exe의 경우:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
.\dist\SKHU_PC_Management\SKHU_PC_Management.exe
```

테스트 모드에서 비활성화되는 항목:

- 기본 설정 적용.
- 고정 IP 적용.
- DHCP 전환.
- Windows 정품 인증 준비.
- Office 정품 인증 준비.
- 작업 표시줄 레이아웃 적용.

테스트 모드에서 허용되는 항목:

- PC 정보 로드.
- 설정 상태 확인.
- 네트워크 어댑터 로드.
- 브라우저 기록, 전원 설정, 예약 종료 상태를 포함한 PC 검사.
- 리소스 검증 및 작업 표시줄 dry-run 검사.

UI는 `테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.`를 표시하며, 보호된 유스케이스를 직접 호출해도 같은 메시지를 반환합니다.

## 제품 키

실제 제품 키를 커밋해서는 안 됩니다. 실제 공급자가 필요한 경우에만 로컬 빌드 또는 배포 머신에서 `src/skhu_pc_management/infrastructure/license/local_product_keys.example.py`를 `src/skhu_pc_management/infrastructure/license/local_product_keys.py`로 복사하세요. `local_product_keys.py`는 Git에서 무시됩니다.

정품 인증 탭은 먼저 버전별 상수인 `WINDOWS_11_PRODUCT_KEY`, `WINDOWS_10_PRODUCT_KEY`, `OFFICE_2024_PRODUCT_KEY`, `OFFICE_2021_PRODUCT_KEY`를 읽습니다. `WINDOWS_PRODUCT_KEY`와 `OFFICE_PRODUCT_KEY`는 fallback 값으로 유지됩니다.

이전 `secrets/product_keys.py` 구조는 Python 표준 라이브러리 `secrets` 모듈과 충돌할 수 있으므로 더 이상 사용하지 않습니다.

로그, 테스트 출력, README 파일, 빌드 스크립트에 제품 키를 출력하지 마세요.

## PyInstaller 빌드

이 앱은 Windows 전용이며 여러 기능이 시스템 설정을 구성하므로 관리자 권한으로 실행해야 합니다. 빌드 스크립트는 PyInstaller의 `--uac-admin` 옵션으로 UAC 권한 상승 메타데이터를 요청하고, 콘솔 창이 없는 GUI 실행 파일을 빌드합니다.

먼저 의존성을 설치하세요:

```powershell
python -m pip install -e .
python -m PyInstaller --version
```

`python -m PyInstaller --version`이 실패하면 패키징 환경이 준비되지 않은 것입니다. 빌드 스크립트를 실행하기 전에 프로젝트 의존성을 설치하세요.

기본 onedir 빌드:

```powershell
.\scripts\build.ps1
```

체크인된 spec 파일을 사용할 때의 동일한 명령:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller SKHU_PC_Management.spec --noconfirm
```

예상 출력:

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

`scripts/build.ps1`이 공식 빌드 진입점입니다. 기본 onedir 빌드는 커밋된 `SKHU_PC_Management.spec` 파일을 사용하므로 hidden import, UAC 메타데이터, 리소스 포함 방식이 안정적으로 유지됩니다.

빌드 후에는 배포 폴더를 검증하세요:

```powershell
.\scripts\check_dist.ps1
```

선택적 onefile 빌드:

```powershell
.\scripts\build.ps1 -OneFile
```

동일한 onefile 명령:

```powershell
python -m PyInstaller --name SKHU_PC_Management --onefile --windowed --uac-admin --clean --noconfirm --icon ".\resources\images\skhu_logo.ico" --paths .\src --add-data ".\resources;resources" --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --hidden-import wmi --hidden-import win32com --hidden-import win32com.client --hidden-import pythoncom --hidden-import pywintypes .\src\skhu_pc_management\main.py
```

`resources/`는 `--add-data ".\resources;resources"`로 포함됩니다. PyInstaller onedir 빌드에서는 데이터 파일이 일반적으로 `_internal\resources` 아래에 배치됩니다. 런타임 resolver는 PyInstaller 추출 경로, `_internal`, 실행 파일 경로, 개발 경로를 확인하므로 같은 코드가 패키징된 리소스와 로컬 리소스를 모두 찾을 수 있습니다.

`resources/images/skhu_logo.ico`는 PySide6 창 아이콘과 헤더 로고에 사용됩니다. `resources/TaskBar.reg`와 `resources/TaskBar/*.lnk`는 작업 표시줄 리소스 검사기가 검증하며, 패키징된 리소스 디렉터리에 포함됩니다.

작업 표시줄 레이아웃 버튼은 현재 기본적으로 dry-run 계획을 수행합니다. `TaskBar.reg`를 검증하고, 복사될 `.lnk` 바로 가기를 나열하며, 필요한 레지스트리/import 및 Explorer 재시작 단계를 보여줍니다. 향후 명시적인 구현이 확인 흐름 뒤에 해당 동작을 추가하지 않는 한, 고정된 작업 표시줄 파일을 삭제하거나 `regedit`를 실행하거나 Explorer를 재시작하지 않습니다.

실행 파일에 제품 키를 내장해야 한다면 `scripts/build.ps1`을 실행하기 전에 로컬 빌드 머신에서 `src/skhu_pc_management/infrastructure/license/local_product_keys.py`를 만드세요. `local_product_keys.example.py`를 `local_product_keys.py`로 복사하고 실제 키를 로컬에서 채운 뒤, 해당 파일은 커밋하지 마세요. 빌드 스크립트와 spec은 해당 로컬 모듈 파일이 존재할 때만 hidden import에 추가합니다.

생성된 `build/`, `dist/`, 임시 `*.spec` 파일은 무시됩니다. `SKHU_PC_Management.spec`은 고정된 onedir 패키징 설정이므로 의도적으로 커밋됩니다.

onedir 빌드는 전체 `dist\SKHU_PC_Management\` 디렉터리를 배포하세요. 배포 정책이 대상 머신에 명시적으로 요구하지 않는 한 로컬 전용 비밀 파일은 포함하지 마세요.

## Windows 테스트 PC 절차

전체 onedir 폴더를 복사한 뒤 실제 Windows 테스트 PC에서 다음 순서를 사용하세요:

1. `SKHU_PC_Management.exe`를 실행하고 UAC 프롬프트가 나타나는지 확인합니다.
2. 시작 초기화 상태를 확인합니다. 관리자 경고, PC 정보, 설정 상태, PC 검사가 앱 충돌 없이 로드되어야 합니다.
3. PC 정보에 CPU, RAM, OS, 디스크 실제/표기 용량, BusType, TPM, Secure Boot, 부팅 모드가 표시되는지 확인합니다.
4. 설정 상태를 확인할 수 있고, 설정 적용이 변경 전에 확인을 요청하는지 확인합니다.
5. 네트워크 어댑터가 로드되고 물리 Ethernet/Wi-Fi 어댑터가 연결 해제되었거나 관련성이 낮은 어댑터보다 먼저 표시되는지 확인합니다.
6. DHCP/고정 IP는 폐기 가능한 테스트 네트워크 프로필에서만 테스트합니다.
7. PC 검사에서 브라우저 기록, 전원 설정, 예약 종료, 프로그램 버전에 대한 한국어 메시지가 표시되는지 확인합니다.
8. 정품 인증 버튼이 제품 키를 절대 표시하지 않는지 확인합니다. `local_product_keys.py`가 없으면 한국어 누락 파일 메시지가 나타나야 합니다.
9. 작업 표시줄 리소스 검증/dry-run이 수행될 작업을 보여주고 작업 표시줄을 수정하지 않는지 확인합니다.
10. 앱을 닫았다가 다시 열어 반복 시작 동작을 검증합니다.

## 릴리스 체크리스트

앱을 패키징하거나 테스트 PC에 전달하기 전에 `RELEASE_CHECKLIST.md`를 사용하세요. 체크리스트는 시작 초기화, 설정, 네트워크, PC 정보, PC 검사, 정품 인증, 리소스/작업 표시줄 동작, busy-state guard, pytest, PyInstaller를 다룹니다.

다음 작업은 실제 Windows 테스트 PC가 필요하며 기본 단위 테스트에서 실행해서는 안 됩니다:

- 기본 설정에 대한 레지스트리 쓰기.
- netsh를 통한 IP/DHCP 변경.
- 정품 인증을 위한 클립보드/프로세스 실행.
- powercfg 및 ScheduledTasks 통합 동작.
- 작업 표시줄 레이아웃 변경, regedit, Explorer 재시작.

작업 표시줄 레이아웃 지원은 현재 리소스를 검증하고 dry-run 계획을 반환합니다. 실제 작업 표시줄 수정은 아직 TODO이며, 명시적인 사용자 확인과 롤백/백업 정책이 있을 때만 구현해야 합니다.

## 저장소 공개 상태

`legacy/csharp/`는 마이그레이션 결정을 위한 읽기 전용 참고 자료이며 Python 작업 중 수정해서는 안 됩니다. Codex와 GitHub 도구가 저장소 규칙을 볼 수 있도록 `AGENTS.md`를 Git에 유지하세요. 로컬 `.git/info/exclude`가 `legacy/` 또는 `AGENTS.md`를 숨기고 있다면, 해당 파일은 로컬에서 untracked 파일로 나타나지 않습니다. 의도적으로 스테이징하기 전에 그런 로컬 전용 exclude 항목을 제거하세요.
