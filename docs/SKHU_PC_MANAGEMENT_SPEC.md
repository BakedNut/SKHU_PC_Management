# SKHU PC Management 기능 명세

## 목적

SKHU PC Management는 성공회대학교 강의실 Windows PC의 정보 조회, 기본 설정 적용, 네트워크 설정, 인증 준비, PC 점검, 유지보수 작업을 지원하는 Windows 전용 PySide6 데스크톱 앱이다.

실제 Windows 동작은 `ports`와 `infrastructure/windows` adapter를 통해 수행한다. `domain`과 `application` 계층은 PySide6, winreg, subprocess, WMI, netsh, powercfg 같은 구현 세부사항을 직접 알지 않는다.

## 실행 환경

| 항목 | 기준 |
| --- | --- |
| OS | Windows |
| Python | 3.12 이상 |
| GUI | PySide6 |
| 배포 | PyInstaller onedir 권장 |
| 권한 | 관리자 권한 권장, 일부 작업 필수 |
| 테스트 모드 | `SKHU_PC_MANAGEMENT_TEST_MODE=1` |
| 제품키 | `local_product_keys.py` 로컬 전용, Git 제외 |

## 화면

앱 시작 시에는 관리자 권한 확인과 PC 기본 정보 조회만 자동 실행한다. 설정 상태 확인/PC 점검은 작업 센터 탭 첫 진입 시, 네트워크 어댑터 조회는 네트워크 탭 첫 진입 시 각각 자동으로 1회 실행한다. 이후 같은 탭 재진입에서는 자동 재조회하지 않고, 사용자가 각 화면의 새로고침 버튼을 눌렀을 때 다시 실행한다.

### PC 정보

- PC 이름, 사용자, Windows 버전, CPU, RAM, GPU, 디스크, 네트워크, TPM, Secure Boot, Boot Mode 표시.
- `PC 이름 변경` 버튼은 Windows 설정 `ms-settings:about` 화면을 연다.
- 앱 UI는 새 이름을 직접 입력받지 않고 `Rename-Computer`를 직접 호출하지 않는다.
- `PC 이름 변경` 버튼은 Windows 설정 화면만 열며 PC 정보 전체 refresh를 자동 실행하지 않는다.

### 작업 센터

- 상단 요약: `설정 상태`, `PC 점검`, `강의실 정책`.
- 인증: Windows 11/10, Office 2024/2021 선택 후 제품키 복사와 인증 준비 실행. 제품키는 화면에 표시하지 않는다.
- 시스템 설정 선택: checkbox로 설정 선택 후 적용.
- 설정 상태 표: `설정 항목 | 현재 상태 | 상세`.
- PC 점검 결과 표: Office 설치 확인 행은 숨기고, Office 감지 결과는 인증 카드 내부 Office row에 표시.
- 즉시 실행 도구: 휴지통, Chrome/Edge User Data 초기화, Chrome/Edge/PotPlayer/Bandizip 실행.
- Chrome/Edge/PotPlayer/Bandizip 실행과 PC 이름 변경 화면 열기는 성공 시 완료 팝업을 표시하지 않고, 실패 시에만 경고 팝업을 표시한다.
- Chrome/Edge/PotPlayer/Bandizip 실행은 실행 후 설정 상태 확인이나 PC 점검 전체 재조회를 수행하지 않는다.
- 작업 센터 탭 첫 진입 시 설정 상태 확인과 PC 점검을 자동으로 1회 실행한다.
- `상태 새로고침`은 설정 상태 확인과 PC 점검을 함께 실행한다.
- 강의실 PC 작업: 전원 옵션 `안 함`, 23시 자동종료 등록.

### 네트워크

- 네트워크 어댑터 조회.
- 현재 네트워크 상태 표 표시.
- 고정 IP 적용, DHCP 전환.
- 적용 후 어댑터 목록을 다시 조회하고 같은 어댑터를 재선택한다.
- 앱 시작 시 자동 조회하지 않고, 네트워크 탭 첫 진입 시 자동으로 1회 조회한다. 이후에는 `어댑터 새로고침` 버튼을 눌렀을 때 다시 조회한다.

## 시스템 설정 항목

| 영역 | 항목 |
| --- | --- |
| 기본 환경 | 기본 배경화면 설정, 바탕화면 `내 PC` 아이콘 표시, 바탕화면 `제어판` 아이콘 표시, 바탕화면 Edge 바로가기 삭제, 작업표시줄 아이콘 설정, 부팅 시 암호 입력 생략 설정 활성화, 빠른 시작 켜기 비활성화, 사용자 계정 암호 만료 비활성화 |
| 탐색기/작업 표시줄 | 자주 사용하는 폴더 숨김, 최근 사용한 항목 숨김, 탐색기 실행 시 `내 PC`로, 파일 선택 확인란 비활성화, 파일 확장자 표시, 작업 보기 버튼 숨김, 검색 아이콘만 표시 |
| 시작 메뉴 | 시작 메뉴: 고정된 항목 더 보기, 시작 메뉴: 최근 추가 앱 숨김, 시작 메뉴: 자주 사용 앱 숨김, 시작 메뉴: 추천 파일 숨김, 시작 메뉴: 팁/권장 사항 숨김, 시작 메뉴: 계정 알림 숨김 |

Windows 10 선택 상태에서는 Windows 11 전용 시작 메뉴 항목을 선택/표시/상태 확인 대상에서 제외한다.

## 상태 확인 정책

- 설정 적용 요청의 성공 여부는 최종 상태 판정 기준이 아니다.
- 설정 상태 표는 registry 값, 파일 대조, PowerShell provider, scheduled task reader 같은 실제 상태 조회 결과만 표시한다.
- Explorer 재시작은 Shell/UI 반영을 위한 best-effort 후처리이며 상태 판정 기준이 아니다.
- provider가 없는 항목은 `상태 확인 미구현` 또는 `확인 불가`로 표시할 수 있다.

action-only provider:

- 기본 배경화면: 현재 wallpaper 경로 확인.
- Edge 바로가기 삭제: Public/User Desktop shortcut과 EdgeUpdate 정책 확인.
- 작업표시줄 아이콘: source/target shortcut 이름과 Chrome shortcut target 확인.
- 사용자 계정 암호 만료 비활성화: `Get-LocalUser` 결과 확인.

## 작업표시줄 정책

- `ApplySettings`의 `set_taskbar_icons`는 `ApplyTaskbarLayout(dry_run=False)` 경로로 실제 적용을 요청한다.
- 테스트 모드에서는 실제 적용을 차단한다.
- dry-run과 리소스 검증 기능은 별도 유지한다.
- 적용은 target TaskBar `.lnk` 삭제, static shortcut 복사, Chrome shortcut 동적 생성, `TaskBar.reg` import, Explorer 재시작 후처리를 포함할 수 있다.
- Chrome target 이름은 항상 `Google Chrome.lnk`다.
- Chrome shortcut은 실제 `chrome.exe` 기반 생성이 우선이고 시작 메뉴 shortcut 복사는 fallback이다.
- Chrome을 찾지 못해도 전체 적용은 실패하지 않고 Chrome 고정을 건너뛴다.
- `TaskBar.reg` import 실패와 일반 shortcut 삭제/복사 실패는 실패다.

## 자동종료 정책

- 적용 버튼은 `23시 자동 종료` Scheduled Task를 등록한다.
- shutdown action은 `shutdown.exe`와 `-s -t 300` 의미를 유지한다.
- 적용 성공 후 `resources/23시 자동종료 취소.lnk`를 현재 사용자 바탕화면에 복사한다.
- 점검은 Scheduled Task 조건과 바탕화면 취소 shortcut 동일성을 함께 확인한다.
- 작업이 없으면 `주의`.
- ScheduledTasks 조회 자체가 실패하면 `알 수 없음`.
- task와 shortcut이 모두 정상일 때만 정상이다.

## 브라우저 사용자 데이터 초기화

Chrome/Edge 초기화는 방문 기록만 삭제하지 않는다. 각 브라우저의 `User Data` root 전체를 삭제하는 정책이다.

- Chrome: `%LOCALAPPDATA%\Google\Chrome\User Data`
- Edge: `%LOCALAPPDATA%\Microsoft\Edge\User Data`

로그인 세션, 확장 프로그램 설정, 브라우저 설정이 삭제될 수 있으므로 확인 대화상자와 테스트 모드 차단이 필요하다.

## 제품키 정책

- 실제 제품키는 `local_product_keys.py` 로컬 파일에서만 읽는다.
- `local_product_keys.example.py`는 빈 템플릿이다.
- 제품키는 UI, 로그, 문서, 테스트 출력에 표시하지 않는다.
- Windows/Office 인증 준비는 제품키 클립보드 복사 후 Windows 인증 창 또는 Excel 실행을 시도한다.

## 테스트 기준

- 단위 테스트는 fake port와 monkeypatch를 사용한다.
- 실제 registry/netsh/powercfg/ScheduledTasks/clipboard/process launch는 단위 테스트에서 실행하지 않는다.
- 실제 Windows 통합 검증은 `RELEASE_CHECKLIST.md`의 수동 체크리스트를 따른다.
