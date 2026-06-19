# Safety Policy

## 1. 목적

이 문서는 학교 PC 관리 도구에서 실수로 시스템 상태를 망가뜨리지 않기 위한 정책이다. 이 앱은 레지스트리, 네트워크, 브라우저 사용자 데이터, 예약 작업, 전원 설정, 제품키 클립보드 복사 등 실제 PC 상태를 바꿀 수 있는 기능을 포함한다.

원칙:

- 위험 작업은 UI 버튼 비활성화만으로 보호하지 않는다. use case 레벨에서도 `SafetyGuard` 또는 명시적 정책으로 차단한다.
- `domain`/`application` 계층은 PySide6, winreg, subprocess, WMI, netsh, powercfg를 직접 import하지 않는다.
- Windows 동작은 `ports` + `infrastructure/windows` adapter로 처리한다.
- GUI는 얇게 유지하고, 사용자 확인 dialog와 상태 표시만 담당한다.
- 실제 제품키/비밀값은 코드, 문서, 로그, 테스트 출력에 포함하지 않는다.

## 2. 위험도 분류

| 위험도 | 설명 | 예시 |
| --- | --- | --- |
| `read_only` | 시스템 상태를 읽기만 함 | PC 정보 조회, 설정 상태 확인, PC 점검, adapter list |
| `user_scope_change` | 현재 사용자 설정 변경 | HKCU registry, wallpaper, desktop shortcut |
| `device_scope_change` | 장치/시스템 전체 설정 변경 | HKLM registry, PC 이름, 전원 옵션 |
| `network_change` | 네트워크 연결에 영향 | static IP, DHCP, DNS |
| `destructive_delete` | 사용자 데이터 또는 파일 삭제 | Chrome/Edge User Data 초기화, 휴지통 비우기 |
| `shell_restart` | Explorer/shell 재시작 | 작업표시줄 적용 후 Explorer restart |
| `reboot_required` | 재부팅 필요 가능 | PC 이름 변경, 일부 registry/system setting |
| `credential_or_product_key_sensitive` | 민감값 취급 | Windows/Office 제품키, clipboard |

## 3. 기능별 위험도 매핑

| 기능 ID | 위험도 | confirmation 필요 | test mode 차단 | 관리자 권한 필요 | dry-run | 백업 필요 | rollback 가능 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `settings.taskbar.real_apply` | `device_scope_change`, `shell_restart` | 예 | 예 | 예 가능 | 예 | 예 | 부분 가능 |
| `settings.taskbar.dry_run` | `read_only` | 아니오 | 아니오 | 아니오 | 예 | 아니오 | 해당 없음 |
| `maintenance.chrome_user_data.reset` | `destructive_delete` | 예 | 예 | 아니오 | 아니오 | 강력 권장 | 백업 없이는 어려움 |
| `maintenance.edge_user_data.reset` | `destructive_delete` | 예 | 예 | 아니오 | 아니오 | 강력 권장 | 백업 없이는 어려움 |
| `maintenance.recycle_bin.empty` | `destructive_delete` | 예 | 예 | 상황별 | 아니오 | 권장 | 어려움 |
| `network.static_ip.apply` | `network_change` | 예 | 예 | 예 | 아니오 | 기존 설정 백업 권장 | 수동 복구 가능 |
| `network.dhcp.apply` | `network_change` | 예 | 예 | 예 | 아니오 | 기존 설정 백업 권장 | 수동 복구 가능 |
| `maintenance.power.never` | `device_scope_change` | 예 | 예 | 예 가능 | 아니오 | 기존 powercfg 백업 권장 | 수동 복구 가능 |
| `maintenance.auto_shutdown_23.apply` | `device_scope_change` | 예 | 예 | 예 가능 | 아니오 | 기존 task 백업 권장 | 삭제/수정 가능 |
| `pc.rename.manual` | `device_scope_change`, `reboot_required` | 예 | 예 | 예 | 아니오 | 기존 PC 이름 기록 | 재변경 가능 |
| `activation.windows.prepare` | `credential_or_product_key_sensitive` | 권장 | 예 | 아니오 또는 상황별 | 아니오 | 해당 없음 | clipboard clear 필요 가능 |
| `activation.office.prepare` | `credential_or_product_key_sensitive` | 권장 | 예 | 아니오 또는 상황별 | 아니오 | 해당 없음 | clipboard clear 필요 가능 |
| `clipboard.product_key.copy` | `credential_or_product_key_sensitive` | 권장 | 예 | 아니오 | 아니오 | 해당 없음 | clipboard clear 필요 가능 |
| `explorer.restart` | `shell_restart` | 예 | 예 | 아니오 | 아니오 | 해당 없음 | 자동 복구 가능하나 세션 영향 |
| `registry.write` | `user_scope_change` 또는 `device_scope_change` | 예 | 예 | HKLM은 예 | 아니오 | reg export 권장 | export 있으면 가능 |

## 4. test mode 정책

환경변수:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
```

허용:

- PC 정보 조회
- 설정 상태 확인
- 네트워크 어댑터 조회
- PC 점검
- 브라우저 사용자 데이터 상태 조회
- 전원 설정 조회
- 자동종료 스케줄 조회
- 리소스 검증
- 작업표시줄 dry-run

차단:

- 기본 설정 적용
- 레지스트리 변경
- 정적 IP 적용
- DHCP 전환
- Windows 인증 준비
- Office 인증 준비
- 제품키 클립보드 복사
- 프로그램 실행
- 23시 자동종료 등록
- 작업표시줄 실제 적용
- Explorer 재시작
- PC 이름 변경
- Chrome/Edge User Data 초기화
- 휴지통 비우기
- 전원 옵션 변경

## 5. confirmation dialog 정책

| 작업 | 제목 | 내용 |
| --- | --- | --- |
| Chrome User Data 초기화 | `Chrome 사용자 데이터 초기화` | `Chrome의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?` |
| Edge User Data 초기화 | `Edge 사용자 데이터 초기화` | `Edge의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?` |
| 휴지통 비우기 | `휴지통 비우기` | `휴지통의 항목을 비웁니다. 삭제된 항목은 복구하기 어려울 수 있습니다. 계속하시겠습니까?` |
| 전원 옵션 적용 | `전원 옵션 '안 함' 적용` | `화면 끄기, 절전, 최대 절전 시간 제한을 변경합니다. 계속하시겠습니까?` |
| 23시 자동종료 적용 | `23시 자동종료 적용` | `22:55에 시작해 300초 후 종료하는 예약 작업을 등록합니다. 계속하시겠습니까?` |
| 고정 IP 적용 | `정적 IP 적용` | `선택한 어댑터의 IP/DNS 설정을 변경합니다. 네트워크 연결이 끊길 수 있습니다. 계속하시겠습니까?` |
| DHCP 전환 | `DHCP 전환` | `선택한 어댑터를 DHCP로 전환합니다. 네트워크 연결이 일시적으로 끊길 수 있습니다. 계속하시겠습니까?` |
| PC 이름 변경 | `PC 이름 변경` | `PC 이름을 변경합니다. 재부팅이 필요할 수 있습니다. 계속하시겠습니까?` |
| 작업표시줄 실제 적용 | `작업표시줄 설정 적용` | 기본 UI 경로에서는 비활성화. 실제 적용은 명시적 허용, 백업, 확인 dialog, 실패 처리 필요 |

## 6. 백업/롤백 정책

현재 구현 여부와 목표를 구분한다.

| 대상 | 현재 구현 | 목표/권장 |
| --- | --- | --- |
| 작업표시줄 바로가기 | 기본 UI 경로는 dry-run/검증 중심. real apply 기본 차단 | 적용 전 대상 TaskBar 폴더 백업, reg export, Explorer restart 실패 처리 |
| 네트워크 설정 | 적용 후 adapter reload. 백업은 확인 필요 | 변경 전 IP/DNS/DHCP 상태 저장 후 복구 버튼 또는 안내 제공 |
| 레지스트리 | 설정 상태 확인과 적용 분리. export는 확인 필요 | HKCU/HKLM 변경 전 reg export 또는 변경값 log |
| 브라우저 User Data 초기화 | User Data root 전체 삭제 정책. test mode 차단 및 확인 dialog | 기본적으로 롤백 불가. 별도 백업 없이는 복구 불가라고 UI에 명시 |
| 휴지통 비우기 | 확인 dialog 필요 | 롤백 어려움. 실행 전 명확한 고지 |
| 전원 옵션 | powercfg 적용. 기존값 백업 확인 필요 | 변경 전 timeout 값 저장 |
| 자동종료 작업 | 등록 use case 있음. 기존 작업 백업 확인 필요 | 기존 task 정의 export 또는 변경 전 상태 표시 |
| 제품키 clipboard | 키 값 표시 금지 | 필요 시 클립보드 clear 안내. 실제 키 로그 금지 |

## 7. 로그 정책

허용:

- 실행한 작업명
- 성공/실패 여부
- 오류 요약
- dry-run planned actions
- 리소스 누락 경고

금지:

- Windows/Office 제품키
- `local_product_keys.py` 내용
- 비밀값/라이선스 값
- 클립보드에 복사한 민감 문자열

주의:

- 삭제 대상 경로에는 사용자 이름 등 개인정보가 포함될 수 있다. 전체 경로를 로그/화면에 표시할 때는 필요성과 노출 범위를 검토한다.
- 내부 예외 메시지는 개발에는 유용하지만 사용자 화면에는 한국어 설명과 함께 제한적으로 표시한다.
