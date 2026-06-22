# Safety Policy

## 목적

SKHU PC Management는 실제 Windows 설정과 사용자 데이터를 변경할 수 있다. 안전 정책은 사용자의 의도 없는 변경, 제품키 노출, 테스트 자동화 중 시스템 변경을 막기 위한 기준이다.

## 기본 원칙

- 제품키와 비밀값은 코드, 문서, 로그, 테스트 출력, UI에 표시하지 않는다.
- 실제 Windows 동작은 `ports`와 `infrastructure/windows` adapter 뒤에서 수행한다.
- `domain`과 `application` 계층은 PySide6, winreg, subprocess, WMI, netsh, powercfg를 직접 import하지 않는다.
- 위험 작업은 UI confirmation과 use case guard를 함께 고려한다.
- 단위 테스트는 fake/monkeypatch를 사용하고 실제 Windows 변경을 실행하지 않는다.

## SafetyGuard

파일: `src/skhu_pc_management/application/safety.py`

| 항목 | 현재 계약 |
| --- | --- |
| `TEST_MODE_DISABLED_MESSAGE` | `테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.` |
| `blocked_message(action)` | 테스트 모드이면 공통 차단 메시지 반환 |
| `blocked_taskbar_apply_message(dry_run)` | dry-run은 허용, 실제 적용은 테스트 모드에서 차단 |
| `allow_real_taskbar_apply` | 운영 모드에서는 bootstrap에서 true로 생성 |

테스트 모드는 안전한 UI 자동화용이다. 운영 모드에서 실제 적용 버튼을 누르면 사용자 확인과 각 use case 정책에 따라 변경을 수행할 수 있다.

## 테스트 모드

활성화:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

허용:

- PC 정보 조회.
- 설정 상태 확인.
- PC 점검.
- 네트워크 어댑터 조회.
- 작업표시줄 리소스 검증.
- 작업표시줄 dry-run 계획 확인.

차단:

- 레지스트리/시스템 설정 적용.
- 작업표시줄 실제 적용.
- 고정 IP 적용, DHCP 전환.
- Windows/Office 인증 준비와 제품키 클립보드 복사.
- Chrome/Edge 사용자 데이터 초기화.
- 휴지통 비우기.
- 전원 옵션 변경.
- 23시 자동종료 등록.
- 프로그램 실행.
- Windows 설정의 PC 이름 변경 화면 열기.

## 위험 작업 매핑

| 기능 | 변경 대상 | UI 확인 | test mode | 비고 |
| --- | --- | --- | --- | --- |
| 시스템 설정 적용 | HKCU/HKLM, 파일, 계정 정책 | 필요 | 차단 | 설정 적용 후 상태 provider로 재검증 |
| 작업표시줄 아이콘 설정 | TaskBar pinned 폴더, `TaskBar.reg`, Explorer | 필요 | 차단 | Chrome은 `Google Chrome.lnk` 동적 생성/검증 |
| 고정 IP/DHCP | adapter IP/DNS | 필수 | 차단 | 적용 후 adapter reload |
| Windows/Office 인증 준비 | 클립보드, 인증 창/Excel 실행 | 버튼 의도 기반 | 차단 | 제품키 미표시 |
| Chrome/Edge User Data 초기화 | 브라우저 `User Data` root | 필수 | 차단 | 방문 기록만 삭제가 아님 |
| 휴지통 비우기 | Recycle Bin | 필수 | 차단 | 복구 어려움 |
| 전원 옵션 `안 함` | powercfg | 필수 | 차단 | 강의실 정책 |
| 23시 자동종료 등록 | Scheduled Task, 바탕화면 shortcut | 필수 | 차단 | 취소 shortcut 포함 |
| PC 이름 변경 화면 열기 | Windows 설정 앱 실행 | 버튼 의도 기반 | 차단 | 이름 변경은 OS UI에서 수행 |
| 프로그램 실행 | Chrome/Edge/PotPlayer/Bandizip | 보통 없음 | 차단 | UI 자동화 안전 목적 |

## 브라우저 사용자 데이터 초기화

Chrome/Edge 초기화는 `User Data` root 전체 삭제 정책이다.

- 로그인 세션이 삭제될 수 있다.
- 확장 프로그램 설정이 삭제될 수 있다.
- 브라우저 설정과 프로필 데이터가 삭제될 수 있다.
- 폐기 가능한 테스트 계정에서만 수동 검증한다.

## 작업표시줄 안전 정책

- dry-run은 읽기/계획 확인으로 유지한다.
- 실제 적용은 기존 target `.lnk` 삭제와 registry import를 수행할 수 있으므로 UI confirmation이 필요하다.
- Explorer 재시작은 best-effort 후처리이며 적용 성공/실패의 핵심 기준이 아니다.
- `TaskBar.reg` import 실패와 shortcut 삭제/복사 실패는 실패다.
- Chrome shortcut이 유효하지 않으면 상태 provider가 `설정됨`으로 보지 않는다.

## 자동종료 안전 정책

- 등록되는 작업 이름은 `23시 자동 종료`다.
- 22:55에 시작해 300초 후 종료되는 의미를 유지한다.
- 적용 후 `23시 자동종료 취소.lnk`를 현재 사용자 바탕화면에 복사한다.
- 점검은 task와 취소 shortcut 동일성을 모두 확인한다.
- task 없음은 `주의`, 조회 실패는 `알 수 없음`이다.

## 제품키 정책

- `local_product_keys.py`는 로컬 전용이며 Git에 포함하지 않는다.
- 제품키 값은 화면, 로그, 문서, 테스트 출력에 표시하지 않는다.
- 인증 결과 메시지는 키 값을 포함하지 않는다.
- 클립보드에 복사된 제품키는 운영 절차에 따라 다른 값으로 덮어쓰기 권장.

## 백업/롤백 권장

| 대상 | 권장 |
| --- | --- |
| 작업표시줄 | 적용 전 target 폴더와 관련 registry export |
| 네트워크 | 기존 IP/DNS/DHCP snapshot |
| 레지스트리 설정 | 변경 전 reg export |
| 브라우저 User Data | 필요한 경우 프로필 백업 |
| Scheduled Task | 기존 task export |

현재 단위 테스트는 백업/롤백을 실행하지 않는다. 실제 운영 절차에서 별도 관리한다.
