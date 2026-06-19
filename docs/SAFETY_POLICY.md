# Safety Policy

## 1. 목적

학교 PC 관리 도구에서 실수로 시스템 상태를 망가뜨리지 않기 위한 정책이다. 이 프로젝트는 실제 Windows 설정 변경 기능을 포함하므로, 위험 작업은 UI 확인과 use case guard 양쪽에서 방어해야 한다.

원칙:

- 제품키/비밀값은 코드, 문서, 로그, 테스트 출력, UI에 노출하지 않는다.
- `domain`/`application`은 PySide6, winreg, subprocess, WMI, netsh, powercfg를 직접 import하지 않는다.
- Windows 동작은 `ports` + `infrastructure/windows` adapter로 처리한다.
- GUI는 얇게 유지하고 confirmation/status 표시만 담당한다.

## 2. 현재 SafetyGuard 구현

파일: `src/skhu_pc_management/application/safety.py`

| 항목 | 최신 구현 |
| --- | --- |
| 필드 | `test_mode: bool = False`, `allow_real_taskbar_apply: bool = False` |
| `TEST_MODE_DISABLED_MESSAGE` | `테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.` |
| `REAL_TASKBAR_APPLY_DISABLED_MESSAGE` | `작업표시줄 실제 적용은 기본적으로 비활성화되어 있습니다. 리소스 검증/dry-run만 수행하세요.` |
| `blocked_message(action)` | test mode이면 공통 차단 메시지 반환. action별 위험도 판정은 하지 않음 |
| `blocked_taskbar_apply_message(dry_run)` | dry-run 허용. real apply는 test mode 또는 `allow_real_taskbar_apply=False`에서 차단 |

현재 `SafetyGuard`는 OperationRisk enum 기반 일반 정책이 아니다. test mode 차단과 작업표시줄 real apply 특수 차단을 제공한다. UI confirmation은 “사용자가 의도했는지 확인”하는 역할이고, use case guard는 “우회 호출도 차단”하는 역할이다.

## 3. 위험도 분류

| 위험도 | 설명 | 예시 | confirmation | test mode | 현재 구현 지원 |
| --- | --- | --- | --- | --- | --- |
| `read_only` | 시스템 상태 조회 | PC 정보, 상태 확인, PC 점검 | 보통 불필요 | 허용 | 지원 |
| `user_scope_change` | 사용자 범위 설정 변경 | HKCU registry, wallpaper | 필요 | 차단 | 개별 use case guard |
| `device_scope_change` | 장치/시스템 범위 변경 | HKLM, 전원, 예약 작업 | 필요 | 차단 | 개별 use case guard |
| `network_change` | 네트워크 연결 영향 | static IP, DHCP | 필수 | 차단 | 지원 |
| `destructive_delete` | 데이터 삭제/초기화 | User Data, 휴지통 | 필수 | 차단 | 지원 |
| `shell_restart` | Explorer/shell 영향 | Explorer 재시작 | 필수 | 차단 | 일부 post command |
| `reboot_required` | 재부팅 필요 가능 | PC 이름 변경 | 필수 | 차단 | 부분 |
| `credential_or_product_key_sensitive` | 민감값 처리 | 제품키 clipboard | 권장/필수 | 차단 | 지원 |

## 4. 기능별 위험도 매핑

| 기능 ID | 위험도 | confirmation | test mode 차단 | 관리자 권한 | dry-run | 백업 | rollback | 현재 구현 | 테스트 고정 | 후속 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `settings.taskbar.plan` | read_only | 아니오 | 아니오 | 아니오 | 예 | 불필요 | 해당 없음 | 구현 | 있음 | `.lnk` 리소스 확인 |
| `settings.taskbar.real_apply` | device/shell | 필수 | 예 | 예 가능 | 아니오 | 필요 | 부분 | 기본 차단 | 있음 | 승인된 별도 흐름 |
| `maintenance.chrome_user_data.reset` | destructive_delete | 예 | 예 | 아니오 | 아니오 | 강력 권장 | 백업 없이는 어려움 | 구현 | 있음 | 백업 정책 |
| `maintenance.edge_user_data.reset` | destructive_delete | 예 | 예 | 아니오 | 아니오 | 강력 권장 | 백업 없이는 어려움 | 구현 | 있음 | 백업 정책 |
| `maintenance.recycle_bin.empty` | destructive_delete | 예 | 예 | 상황별 | 아니오 | 권장 | 어려움 | 구현 | 있음 | 메시지 강화 |
| `network.static_ip.apply` | network_change | 예 | 예 | 예 | 아니오 | 권장 | 수동 가능 | 구현 | 있음 | 변경 전 snapshot |
| `network.dhcp.apply` | network_change | 예 | 예 | 예 | 아니오 | 권장 | 수동 가능 | 구현 | 있음 | 변경 전 snapshot |
| `maintenance.power.never` | device_scope_change | 예 | 예 | 예 가능 | 아니오 | 권장 | 수동 가능 | 구현 | 부분 | 기존값 백업 |
| `maintenance.auto_shutdown_23.apply` | device_scope_change | 예 | 예 | 예 가능 | 아니오 | 권장 | 가능 | 구현 | 부분 | 기존 task export |
| `pc.rename.manual` | device/reboot | 확인 필요 | 예 | 예 | 아니오 | 기존 이름 기록 | 가능 | 구현 | 부분 | confirmation 추가 |
| `activation.windows.prepare` | product_key_sensitive | 권장 | 예 | 상황별 | 아니오 | 해당 없음 | clipboard clear 가능 | 구현 | 있음 | clipboard clear |
| `activation.office.prepare` | product_key_sensitive | 권장 | 예 | 상황별 | 아니오 | 해당 없음 | clipboard clear 가능 | 구현 | 있음 | clipboard clear |
| `clipboard.product_key.copy` | product_key_sensitive | 권장 | 예 | 아니오 | 아니오 | 해당 없음 | clear 가능 | 구현 | 있음 | 노출 시간 최소화 |
| `explorer.restart` | shell_restart | 필수 | 예 | 아니오 | 아니오 | 해당 없음 | 어려움 | post command 구조 | 간접 | 사용자 확인 분리 |
| `registry.write` | user/device | 필수 | 예 | HKLM은 예 | 아니오 | reg export 권장 | export 있으면 가능 | 구현 | fake tests | export 정책 |
| `program.launch` | process | 보통 불필요 | 예 | 아니오 | 아니오 | 해당 없음 | 종료 가능 | 구현 | 있음 | test mode 유지 |

## 5. test mode 정책

허용:

- 읽기 전용 조회
- 설정 상태 확인
- PC 점검
- 네트워크 adapter 조회
- 작업표시줄 dry-run
- 리소스 검증

차단:

- 실제 Windows 상태 변경
- 레지스트리 write
- 네트워크 변경
- 삭제/초기화
- 클립보드 제품키 복사
- 프로세스 실행
- Explorer 재시작
- 재부팅 유발 작업

| 방어 위치 | 현재 구현 |
| --- | --- |
| UI disabled | `MainWindow`, `PcInfoPanel`, `ActionCenterPanel`, `NetworkPanel`에서 위험 버튼 disabled/tooltip |
| use case guard | `ApplySettings`, `ApplyStaticIp`, `SetDhcp`, `RenamePc`, `Activate*`, `RunPcMaintenance`, `LaunchProgram`, `SystemSettingsActions`, `ApplyTaskbarLayout` |
| 테스트 | `tests/test_test_mode_safety.py`, `tests/test_operation_safety_policy.py` |

## 6. confirmation dialog 정책

최신 `presentation/qt/maintenance_confirmations.py` 기준:

| 작업 | 제목 | 실제 메시지 |
| --- | --- | --- |
| 휴지통 비우기 | `휴지통 비우기` | `휴지통의 항목을 삭제합니다. 계속하시겠습니까?` |
| Chrome User Data 초기화 | `Chrome 사용자 데이터 초기화` | `Chrome의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?` |
| Edge User Data 초기화 | `Edge 사용자 데이터 초기화` | `Edge의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?` |
| 전원 옵션 적용 | `전원 옵션 적용` | `전원 절전/화면 꺼짐 옵션을 '안 함'으로 변경합니다. 계속하시겠습니까?` |
| 23시 자동종료 적용 | `23시 자동종료 적용` | `매일 22:55에 300초 후 종료 예약 작업을 등록합니다. 계속하시겠습니까?` |

추가 확인:

| 항목 | 현재 confirmation |
| --- | --- |
| 고정 IP 적용 | `NetworkPanel`에서 `QMessageBox.question` 있음 |
| DHCP 전환 | `NetworkPanel`에서 `QMessageBox.question` 있음 |
| PC 이름 변경 | 입력 dialog와 재부팅 안내는 있으나 별도 위험 confirmation은 확인 필요 |
| 작업표시줄 실제 적용 | 기본 UI 경로는 비활성/차단. real apply confirmation 별도 필요 |
| Windows/Office 인증 준비 | 버튼 의도 기반. 제품키 클립보드 복사 confirmation은 확인 필요 |

## 7. 백업/롤백 정책

| 대상 | 현재 구현 | 목표/권장 |
| --- | --- | --- |
| 작업표시줄 바로가기 | real apply 기본 차단, dry-run 중심 | 대상 폴더 백업, reg export, 실패 rollback |
| 네트워크 설정 | 적용 후 reload. 변경 전 백업 확인 필요 | 기존 IP/DNS/DHCP snapshot 저장 |
| 레지스트리 export | 확인 필요 | HKCU/HKLM 변경 전 export |
| 브라우저 User Data 초기화 | User Data root 삭제. 백업 없음 | 별도 백업 없이는 복구 불가 명시 |
| PC 이름 변경 | 기존 이름은 UI에 표시되지만 rollback 절차 없음 | 기존 이름 기록/재부팅 안내 강화 |
| Scheduled task 변경 | 등록 구현 있음. 기존 task 백업 확인 필요 | 기존 task export/diff |

## 8. 로그/비밀값 정책

금지:

- 제품키/비밀값 로그
- `local_product_keys.py` 내용 출력
- 클립보드에 복사한 민감 문자열 표시
- exception full traceback을 사용자 UI에 그대로 노출

허용:

- 작업명
- 성공/실패 여부
- 오류 요약
- dry-run planned actions
- 리소스 누락 경고

주의:

- 사용자 경로와 삭제 대상 경로에는 개인 정보가 포함될 수 있다.
- 제품키는 UI에 표시하지 않고 clipboard 사용 후 주의 메시지를 제공해야 한다.

## 9. 안전 정책 감사 결과

| 정책 항목 | 현재 구현 | UI 방어 | use case 방어 | 테스트 고정 | 불일치/취약점 | 후속 작업 |
| --- | --- | --- | --- | --- | --- | --- |
| test mode 양방향 차단 | 구현됨 | 버튼 disabled/tooltip | guard 다수 | 있음 | 일부 새 기능 추가 시 guard 누락 위험 | checklist 유지 |
| Chrome/Edge User Data confirmation | 구현됨 | confirmation | use case test mode guard | 있음 | use case 직접 호출은 confirmation 없음 | service layer confirmation은 UI 책임으로 명시 |
| 작업표시줄 real apply 기본 차단 | 구현됨 | 기본 UI dry-run | `blocked_taskbar_apply_message` | 있음 | allow flag 사용 시 백업 정책 필요 | 승인 흐름 설계 |
| IP/DHCP confirmation | 구현됨 | `QMessageBox.question` | test mode guard | 있음 | 백업/rollback 없음 | snapshot 저장 |
| 인증 제품키 노출 금지 | 구현됨 | placeholder/masked | provider/use case 결과에 키 없음 | 있음 | clipboard clear 없음 | clear 정책 |
| PC 이름 변경 confirmation | 부분 | 입력 dialog/재부팅 안내 | test mode guard | 부분 | 명시 위험 confirmation 부족 가능 | confirmation 추가 |
| registry write | 구현됨 | 설정 적용 버튼 | test mode guard | 있음 | reg export 없음 | 백업 정책 |
| Explorer restart | post command 구조 | 설정 적용 흐름 | test mode guard | 간접 | 사용자에게 restart 실행 고지 확인 필요 | 후처리 분리 |
