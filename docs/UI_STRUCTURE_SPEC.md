# UI Structure Spec

## 1. UI 목표

- Windows 11 Settings / PowerToys / Microsoft Defender 스타일의 관리 앱
- 기능 나열이 아니라 상태 기반 dashboard
- 위험 작업을 색상, 문구, 확인 dialog로 명확히 구분
- 사용자-facing UI는 한국어
- 제품키는 화면에 표시하지 않음
- GUI는 얇게 유지하고 use case/ViewModel에 작업을 위임

## 2. 전체 레이아웃

목표 및 현재 구조:

| 영역 | 역할 | 관련 파일 |
| --- | --- | --- |
| top bar | 앱 제목, Windows/PC 상태 badge, test mode badge | `presentation/qt/main_window.py` |
| left navigation | PC 정보, 작업 센터, 네트워크 이동 | `presentation/qt/main_window.py` |
| stacked content | 선택 화면 표시 | `QStackedWidget` in `MainWindow` |
| busy/info banner | startup/장시간 작업 진행 메시지 | `BusyCoordinator`, `MainWindow` |
| content panels | 실제 화면 구성 | `presentation/qt/panels/*.py` |

현재 화면:

- `PC 정보`
- `작업 센터`
- `네트워크`

이전 placeholder 패널(`activation_panel.py`, `settings_panel.py`, `pc_check_panel.py`)이 남아 있을 수 있으나, 현재 통합 UI 중심은 `ActionCenterPanel`이다. 이후 정리 시 실제 사용 여부를 확인해야 한다.

## 3. 공통 컴포넌트

| 컴포넌트 | 역할 | 사용 위치 | 파일 |
| --- | --- | --- | --- |
| `Card` | 제목/부제/본문이 있는 기본 표면 | 모든 패널 | `widgets/surfaces.py` |
| `SectionCard` | 카드 내부의 소그룹 | 작업 센터 설정 목록 | `widgets/surfaces.py` |
| `SummaryCard` | dashboard 요약 값 | PC 정보/작업 센터/네트워크 | `widgets/surfaces.py` |
| `InfoBanner` | 안내/경고 메시지 | test mode, validation | `widgets/surfaces.py` 또는 panel local |
| `StatusBadge` | 상태 tone 표시 | header, check/status | `widgets/badges.py` |
| `PrimaryButton` | 주요 권장 작업 | 상태 새로고침, 설정 적용 등 | `widgets/buttons.py` |
| `SecondaryButton` | 일반 작업 | 프로그램 실행, 보조 실행 | `widgets/buttons.py` |
| `SubtleButton` | 보조 선택/초기 입력 | 전체 선택/해제, 기본 대역 입력 | `widgets/buttons.py` |
| `WarningButton` | 시스템 설정 변경/주의 작업 | 전원/자동종료/휴지통/DHCP 등 | `widgets/buttons.py` |
| `DangerButton` | 삭제/초기화 | Chrome/Edge User Data 초기화 | `widgets/buttons.py` |
| `NavButton` | 화면 이동 | left navigation | `widgets/buttons.py` |
| `FormField` | label+input 행 | 네트워크/PC 정보 | `widgets/forms.py` |
| `ReadOnlyField` | 읽기 전용 값 표시 | PC 정보/네트워크 current status | `widgets/forms.py` |
| `DataTable` | 상태/상세 테이블 | settings status, PC check, disk table | `widgets/tables.py` |

## 4. 버튼 역할 규칙

| role | 용도 | 색상 의미 |
| --- | --- | --- |
| `primary` | 주요 권장 작업 | 사용자가 가장 먼저 누를 정상 흐름 |
| `secondary` | 일반 작업 | 상태 조회, 프로그램 실행 등 |
| `subtle` | 보조 작업 | 전체 선택/해제, 기본값 입력 |
| `warning` | 되돌리기 어렵거나 시스템 설정 변경 | 신중히 실행 |
| `danger` | 삭제/초기화 | 데이터 손실 가능 |
| `nav` | 화면 이동 | 선택 상태 표시 |

기능별 버튼 role 매핑:

| 기능 | role |
| --- | --- |
| PC 정보 새로고침 | primary 또는 secondary |
| PC 이름 변경 | secondary 또는 warning |
| PC 이름 사용자 이름과 맞추기 | warning |
| 선택한 설정 적용 | primary |
| 모두 선택/해제 | subtle |
| Chrome/Edge 실행 | secondary |
| PotPlayer/Bandizip 실행 | secondary |
| Chrome/Edge User Data 초기화 | danger |
| 휴지통 비우기 | warning |
| 전원 옵션 적용 | warning |
| 23시 자동종료 적용 | warning |
| IP 설정 적용 | primary |
| DHCP 전환 | warning 또는 secondary |
| 기본 대역 입력 | subtle |

## 5. PC 정보 화면

목표 구조:

- title/subtitle
- summary cards
- system info
- hardware info
- disk table
- PC actions
- security compatibility

표시 대상:

| 영역 | 표시 항목 |
| --- | --- |
| 시스템 | PC 이름, 사용자, Windows, build, architecture |
| 하드웨어 | CPU, RAM, GPU |
| 디스크 | model, display type, rated size, actual GiB |
| 보안/부팅 | TPM, Secure Boot, Boot Mode |
| PC 작업 | 이름 변경, 사용자 이름 기반 자동 변경 |

주의:

- PC 이름 변경은 위험 작업이다. test mode에서 차단되어야 한다.
- WMI 실패 시 앱이 죽지 않고 `알 수 없음`으로 표시해야 한다.

## 6. 작업 센터 화면

목표 구조:

- summary row
- recommended actions
- activation
- settings
- maintenance tools
- settings status table
- PC check table
- classroom PC actions

현재 요약 카드:

| 카드 | 값 |
| --- | --- |
| 설정 상태 | `SettingsViewModel.summary_text` |
| PC 점검 | `PcCheckViewModel.summary_text` |
| Office | `installed_office_status_text` |
| 강의실 정책 | 전원 옵션 + 자동 종료 상태 |

위험 작업 confirmation 문구:

| 작업 | 제목 | 핵심 문구 |
| --- | --- | --- |
| Chrome User Data 초기화 | `Chrome 사용자 데이터 초기화` | User Data 폴더 삭제, 방문 기록/로그인 세션/확장 프로그램 설정/브라우저 설정 삭제 가능 |
| Edge User Data 초기화 | `Edge 사용자 데이터 초기화` | Edge User Data 폴더 전체 삭제 가능 |
| 휴지통 비우기 | `휴지통 비우기` | 삭제된 항목 복구 어려움 |
| 전원 옵션 적용 | `전원 옵션 '안 함' 적용` | 화면 끄기/절전/최대 절전 timeout 변경 |
| 23시 자동종료 적용 | `23시 자동종료 적용` | 22:55 시작, 300초 후 종료 예약 |

설정 상태 표 규칙:

- `설정 항목`
- `적용 결과`
- `현재 상태`
- `상세`
- detail은 버리지 않고 tooltip에 보존한다.

PC 점검 표 규칙:

- `항목`
- `상태`
- `상세 내용`
- status는 badge tone 또는 table tone으로 표시한다.

## 7. 네트워크 화면

목표 구조:

- adapter summary
- IP config form
- current network status table
- validation message
- apply/DHCP/default buttons

표시/입력:

| 영역 | 항목 |
| --- | --- |
| adapter | 이름, 설명, status, MAC |
| current table | IP 할당 방식, IP 주소, subnet mask, gateway, DNS |
| form | IP, subnet mask, gateway, DNS1, DNS2 |
| helper | 학교 기본 대역 입력, IP 입력 기반 gateway 자동 계산 |

주의:

- `192.168.`처럼 마지막 octet이 없는 prefix 상태에서는 적용을 막고 한국어 validation message를 표시한다.
- static IP/DHCP 성공 후 adapter list를 다시 불러와 현재 상태를 갱신한다.
- 실제 netsh/PowerShell 호출은 adapter 뒤에서만 수행한다.

## 8. 상태 표시 규칙

| status text | badge tone |
| --- | --- |
| 정상, 적용됨, 설정됨, 설치됨, 완료, 최신 | success |
| 주의, 미적용, 미설정, 값 없음, 필요, 설치되지 않음 | warning |
| 실패, 오류 | danger |
| 확인 불가, 알 수 없음, 미구현 | neutral |
| 진행 중, 확인 중 | info |

주의:

- “확인 불가”는 danger가 아니라 neutral에 가깝다.
- 내부 status enum 값은 유지하되 UI 표시 문자열은 한국어로 변환한다.

## 9. 테이블 규칙

- detail은 버리지 않는다.
- 긴 detail은 tooltip에 보존한다.
- 상태 column은 badge 또는 tone을 적용한다.
- edit disabled.
- row selection.
- alternating rows.
- 폭이 좁아도 핵심 상태가 가려지지 않게 column resize 정책을 확인한다.

## 10. 사용자 메시지 규칙

- 사용자-facing 메시지는 한국어.
- 내부 예외 메시지는 그대로 단독 노출하지 말고 한국어 prefix와 함께 표시한다.
- 제품키 값은 절대 표시하지 않는다.
- destructive action은 구체적으로 무엇이 삭제되는지 표시한다.
- “방문 기록 삭제”라고 쓰지 말고, 현재 정책에 맞게 “Chrome/Edge 사용자 데이터 초기화”라고 쓴다.
- 작업이 “적용 요청 성공”인지 “현재 상태 검증 성공”인지 구분한다.
