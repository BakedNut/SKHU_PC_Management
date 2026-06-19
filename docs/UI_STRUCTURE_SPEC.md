# UI Structure Spec

## 1. UI 목표

최신 구현의 UI 목표는 Windows 11 Settings / PowerToys / Microsoft Defender 스타일의 관리 앱이다. 기능을 단순히 나열하기보다 현재 상태를 요약하고, 권장 조치와 위험 작업을 명확히 구분하는 상태 기반 dashboard를 지향한다.

원칙:

- 사용자-facing UI는 한국어.
- 위험 작업은 색상, 문구, 확인 dialog로 구분.
- 제품키는 화면에 표시하지 않음.
- test mode 상태를 상단/상태 영역에 명확히 표시.
- PySide6 GUI는 얇게 유지하고 ViewModel/use case에 작업을 위임.

## 2. 전체 레이아웃

| 요소 | 현재 구현 | 파일 | objectName/속성 |
| --- | --- | --- | --- |
| top bar | 앱 제목, subtitle, Windows/PC/test mode badge | `presentation/qt/main_window.py` | `topBar`, `appTitle`, `appSubtitle` |
| left navigation | `PC 정보`, `작업 센터`, `네트워크` 버튼 | `main_window.py` | `buttonRole="nav"`, `selected` |
| stacked content | `QStackedWidget`에 3개 panel 추가 | `main_window.py` | `contentSurface` |
| busy/info banner | 전역 busy message 표시, stack/nav disable | `main_window.py`, `busy_coordinator.py` | `infoBanner` |
| test mode banner | test mode 안내 문구 표시 | `main_window.py` | `warningBanner` |
| Windows/PC/test badge | header 상태 표시 | `main_window.py`, `widgets/badges.py` | `statusBadge`, `tone` |

현재 구현은 QTabWidget이 아니다. 좌측 navigation + `QStackedWidget` 구조다.

## 3. 공통 컴포넌트 명세

| 컴포넌트 | 현재 구현 | 목적 | objectName/property | 사용 위치 |
| --- | --- | --- | --- | --- |
| `Card` | 구현됨 | 제목/부제/본문 카드 | `card` | 모든 주요 panel |
| `SectionCard` | 구현됨 | 카드 내부 section | `sectionCard` | 설정 section |
| `SummaryCard` | 구현됨 | dashboard 요약 값 | `summaryTitle`, `summaryValue`, `summarySubtitle` | PC 정보, 작업 센터 |
| `InfoBanner` | helper 구현 | 안내/경고 banner | `infoBanner`/`warningBanner` | test/busy/validation |
| `StatusBadge` | 구현됨 | 상태 pill | `statusBadge`, `tone` | header, 상태 row |
| `PrimaryButton` | helper | 주요 권장 작업 | `buttonRole=primary` | 새로고침/적용 |
| `SecondaryButton` | helper | 일반 작업 | `buttonRole=secondary` | 프로그램 실행 |
| `SubtleButton` | helper | 보조 작업 | `buttonRole=subtle` | 전체 선택/기본값 |
| `WarningButton` | helper | 주의 작업 | `buttonRole=warning` | 전원/자동종료/휴지통 |
| `DangerButton` | helper | 삭제/초기화 | `buttonRole=danger` | User Data 초기화 |
| `NavButton` | helper | 화면 이동 | `buttonRole=nav` | left nav |
| `FormField` | `FieldRow`, `FormGrid` | label/input 배치 | `fieldLabel`, `mutedText` | PC/Network |
| `ReadOnlyField` | 구현됨 | 읽기 전용 값 | `readOnlyField` | PC/Network |
| `DataTable` | `configure_table` | 상태/상세 표 | QTableWidget 설정 | 설정/점검/디스크 |

## 4. 버튼 역할 규칙

| role | 의미 | 색상 방향 | 사용 예 | confirmation |
| --- | --- | --- | --- | --- |
| `primary` | 핵심 권장 작업 | 강조 | 상태 새로고침, 선택한 설정 적용, 정적 IP 적용 | 작업별 |
| `secondary` | 일반 작업 | 중립 | 프로그램 실행, DHCP 전환 일부 | 작업별 |
| `subtle` | 보조 작업 | 낮은 강조 | 모두 선택/해제, 기본 대역 입력 | 보통 없음 |
| `warning` | 시스템 설정 변경/주의 | 주황/경고 | 휴지통, 전원 옵션, 자동종료, PC 이름 자동 변경 | 필요 |
| `danger` | 삭제/초기화 | 빨강/위험 | Chrome/Edge User Data 초기화 | 필수 |
| `nav` | 화면 이동 | 선택 표시 | left navigation | 없음 |

기능별 매핑:

| 기능 | 현재/권장 role | 비고 |
| --- | --- | --- |
| PC 정보 새로고침 | primary/secondary | 현재 PC 정보 panel 확인 필요 |
| PC 이름 변경 | secondary | 재부팅 안내 필요 |
| PC 이름 사용자 이름과 맞추기 | warning | 위험도 높음 |
| 선택한 설정 적용 | primary | test mode disabled |
| 모두 선택/해제 | subtle |  |
| Windows 인증 준비 | primary | 제품키 미표시 |
| Office 인증 준비 | primary | 제품키 미표시 |
| Chrome/Edge 실행 | secondary | test mode 차단 |
| PotPlayer/Bandizip 실행 | secondary | test mode 차단 |
| Chrome/Edge User Data 초기화 | danger | confirmation 필수 |
| 휴지통 비우기 | warning | confirmation 필수 |
| 전원 옵션 적용 | warning | confirmation 필수 |
| 23시 자동종료 적용 | warning | confirmation 필수 |
| IP 설정 적용 | primary | confirmation 있음 |
| DHCP 전환 | secondary/warning | confirmation 있음 |
| 기본 대역 입력 | subtle | 안전 |

## 5. PC 정보 화면 명세

| 항목 | 현재 구현 |
| --- | --- |
| 목적 | PC 정보 자동/수동 조회, PC 이름 변경 |
| 표시 데이터 | PC 이름, 사용자, Windows, CPU, RAM, GPU, disk rows, TPM, Secure Boot, Boot Mode |
| summary card | PC 이름 등 summary card 사용 |
| 시스템 정보 card | PC/Windows 사용자 정보 |
| 하드웨어 정보 card | CPU/RAM/GPU |
| 디스크 table | model/type/rated/actual 표시 |
| PC 작업 card | PC 이름 변경, 사용자 이름 기반 자동 변경 |
| 보안/호환 상태 card | TPM/Secure Boot/Boot Mode |
| 위험 작업 | PC 이름 변경/자동 변경 |
| test mode | 변경 버튼 disabled, tooltip/message |
| 확인 필요 | 이름 변경 전 별도 “정말 변경” confirmation은 코드상 명시적이지 않음. 재부팅 안내는 있음 |

## 6. 작업 센터 화면 명세

| 영역 | 현재 구현 |
| --- | --- |
| 목적 | 인증 준비, 설정 적용/상태, PC 점검, 유지보수, 강의실 정책 작업 통합 |
| summary row | 설정 상태, PC 점검, Office, 강의실 정책 |
| recommended actions | warning/error count와 전원/자동종료 문구 기반 안내 |
| 인증 card | Windows 10/11, Office 2021/2024 선택. 제품키 placeholder/masked |
| 시스템 설정 card | checkbox list, 전체 선택/해제, 선택 개수, 선택한 설정 적용 |
| 유지보수 도구 card | 휴지통, 프로그램 실행, Chrome/Edge User Data 초기화 |
| 설정 상태 table | 4열: 설정 항목, 적용 결과, 현재 상태, 상세. detail tooltip 보존 |
| PC 점검 table | 3열: 항목, 상태, 상세 내용. cell tooltip 보존 |
| 강의실 PC 작업 | 전원 옵션 안 함 적용, 23시 자동종료 적용 |
| test mode | 위험 버튼 disabled, tooltip에 test mode 메시지 |

중요:

- Chrome/Edge 버튼은 “사용자 데이터 초기화”로 표시하며 `danger` role이다.
- confirmation dialog는 `maintenance_confirmations.py`에서 가져온다.
- 제품키 값은 화면에 표시하지 않는다.
- 설정 table detail은 버리지 않는다.

## 7. 네트워크 화면 명세

| 항목 | 현재 구현 |
| --- | --- |
| 목적 | adapter 조회, 현재 상태 확인, static IP/DHCP 적용 |
| adapter selector | adapter list combo |
| adapter summary | name/description/status/MAC 등 |
| IP config form | IP, subnet, gateway, DNS1, DNS2 |
| validation message | incomplete IP 등 한국어 안내 |
| current network status table | adapter, DHCP, IP, subnet, gateway, DNS |
| apply/DHCP/default buttons | 정적 IP 적용, DHCP 전환, 학교 기본 대역 입력 |
| 위험 작업 | static IP, DHCP |
| 적용 후 reload | ViewModel에서 성공 후 adapter list 재조회 |
| invalid IP | `192.168.` 같은 prefix는 validation으로 차단 |
| confirmation | static IP/DHCP 모두 `QMessageBox.question` 있음 |

## 8. 상태 표시 규칙

최신 `widgets/badges.py` 기준:

| 상태 문자열 | tone |
| --- | --- |
| 정상, 적용됨, 설치됨, 완료, 최신 | success |
| 주의, 미적용, 미설정, 값 없음, 필요, 존재, 설치되지 | warning |
| 진행 중, 확인 중 | info |
| 확인 불가, 알 수 없음, 미구현 | neutral |
| 실패, 오류, 불가 | danger |
| ok/applied/success | success |
| warning/missing/unknown | warning |
| error/failed | danger |

주의: 코드 순서상 `확인 불가`는 neutral 분기 전에 `"불가"` danger 분기가 있으면 위험하다. 최신 코드에서는 neutral 분기를 danger보다 먼저 두는지 계속 유지해야 한다.

## 9. 테이블 규칙

| 규칙 | 현재 구현 |
| --- | --- |
| detail 보존 | 설정 table 4열, PC 점검 table tooltip |
| 긴 detail tooltip | `table_item().setToolTip()` 사용 |
| 상태 column tone | `status_item()` 사용 |
| edit disabled | `configure_table()`에서 적용 |
| row selection | `SelectRows` |
| alternating rows | `setAlternatingRowColors(True)` |
| 한국어 header | 설정/PC 점검 table 적용 |

## 10. 사용자 메시지 규칙

- 사용자-facing 메시지는 한국어로 표시한다.
- 내부 예외는 한국어 prefix와 함께 제한적으로 표시한다.
- 제품키 값은 절대 표시하지 않는다.
- destructive action은 정확히 무엇이 삭제되는지 표시한다.
- `Chrome/Edge 기록 삭제`가 아니라 `Chrome/Edge 사용자 데이터 초기화`라고 표현한다.
- test mode에서는 “테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.”를 tooltip/status로 표시한다.

## 11. UI 감사 결과

| UI 항목 | 현재 구현 | 명세/README 일치 | 테스트 고정 | 남은 확인 필요 | 후속 작업 |
| --- | --- | --- | --- | --- | --- |
| 좌측 navigation | 구현됨 | 일치 | 부분 | 실제 focus/keyboard UX | 접근성 점검 |
| busy banner | 구현됨, stack/nav disabled | 일치 | `test_busy_coordinator.py` | 장시간 작업 중 repaint | async 검토 |
| test mode banner | 구현됨 | 일치 | `test_test_mode_safety.py` | 실제 exe 표시 | UI 수동 테스트 |
| 작업 센터 summary | 구현됨 | 일치 | ViewModel summary tests | 실제 데이터 반영 | screenshot 검증 |
| recommended action text | 구현됨 | 체크리스트와 일치 | 부분 | 문구 과다/누락 | UX copy 개선 |
| dangerous button role | User Data danger, 휴지통/전원 warning | 일치 | safety tests 간접 | 스타일 육안 확인 | UI test 가능 |
| Chrome/Edge confirmation | 구현됨 | 일치 | 있음 | 우회 호출 경로 | use case guard 유지 |
| 설정 table 4열 | 구현됨 | 일치 | 있음 | 열 너비 | resize 정책 개선 |
| 네트워크 validation | 구현됨 | 일치 | 있음 | 실제 입력 중 UX | disabled 상태 실측 |
| 제품키 masking | placeholder/password echo | 일치 | activation tests | clipboard clear 없음 | 정책 검토 |
| 화면 크기/scroll | scroll area/content surface 사용 | 부분 | 없음 | 작은 해상도 | Playwright/Computer Use 수동 확인 |
