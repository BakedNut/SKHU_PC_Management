# 최종 C# 대비 Python 마이그레이션 갭 분석

## 범위

- 비교 기준: `legacy/csharp_final/SKHU_PC_Management` 및 `legacy/csharp_final/SKHU_PC_Management.Tests`
- 비교 대상: 현재 Python `src/skhu_pc_management`
- 이 문서는 분석 문서이며, 코드 수정은 포함하지 않는다.
- `legacy/csharp_final/`은 참조 전용으로만 확인했다.

## 요약

현재 Python 구현은 초기 `legacy/csharp/` 기준의 핵심 scaffold와 일부 기능을 반영했지만, 최종 C# WPF의 staging/main 이후 개선 사항은 상당 부분 빠져 있다. 특히 `InitializeAsync` 기반 초기화 흐름, PC 점검의 최신 버전 조회와 23시 자동종료 점검, 브라우저 기록 상세 판단, 디스크 정격/실제 용량 및 BusType 판별, 작업표시줄 리소스 적용은 Python에 아직 반영되지 않았다.

최근 Python 쪽에서 보강한 제품키 provider와 PowerShell 기반 네트워크 어댑터 조회는 최종 C#과 같은 방향의 문제를 일부 해결했지만, 최종 C#의 전체 UX/상태 모델과는 아직 차이가 있다.

## 기능별 갭 표

| 영역 | 최종 C# 동작 | 현재 Python 상태 | 반영 상태 | 빠진 기능/잘못 포팅된 기능 | Python 버그 원인 | 우선순위 | 관련 C# 파일 | 관련 Python 파일 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 초기 로딩/InitializeAsync | `MainWindow_Loaded`에서 `MainViewModel.InitializeAsync()` 호출. 관리자 권한 검사 실패 시 종료. `RefreshCurrentWindowsVersion`, `RefreshPcInfoAsync`, `RefreshSettingsStatusAsync(runPcCheck: true)`를 초기 로딩에서 실행. Busy overlay와 `SelectedMainTabIndex = 0` 처리. 탭 변경 시 설정/네트워크 상태 갱신. | `main.py`는 QApplication 생성 후 `create_main_window()`와 `show()`만 수행. 각 panel이 `QTimer.singleShot`으로 PC 정보/네트워크를 일부 자동 로드. 관리자 권한 검사, 통합 초기화, 설정 상태/PC 점검 자동 초기화 없음. | 부분 반영 | 관리자 권한 preflight, 통합 초기화 use case, 시작 시 설정 상태/PC 점검 동시 로딩, 탭 선택 기반 lazy refresh, 초기 탭 reset 미반영. | 초기화 책임이 panel별 이벤트로 흩어져 있고 MainWindow/Application bootstrap 레벨의 startup orchestration이 없음. | P0 | `MainWindow.xaml.cs`, `ViewModels/MainViewModel.Initialization.cs`, `MainViewModel.cs`, `MainViewModelTests.cs` | `main.py`, `bootstrap.py`, `presentation/qt/main_window.py`, `panels/*` |
| 2. 네트워크 어댑터 조회 | `NetworkInterface.GetAllNetworkInterfaces()` 사용. Ethernet/Wireless80211 타입 중 이름에 이더넷/Ethernet/Wi-Fi/WiFi 포함 시 지원 대상으로 판단. 이더넷/Ethernet 우선 정렬. 선택 어댑터 snapshot으로 IP, subnet, gateway, DNS, DHCP 상태를 UI 필드에 채움. | PowerShell `Get-NetAdapter | ConvertTo-Json` 우선, 실패 시 netsh fallback. name/description/status/mac_address만 채움. IP/subnet/gateway/dns는 비어 있어도 됨. 최근 기본값 입력과 IP 기반 gateway 자동 갱신은 반영됨. | 부분 반영 | 최종 C#의 `GetAdapterSnapshot` 대응이 Python에는 없음. 어댑터 선택 시 현재 IP/DNS를 필드에 채우는 UX 미반영. Python은 PowerShell 기반이라 C#의 .NET NetworkInterface 타입 필터와 정렬 조건과 다름. | 어댑터 목록 조회와 어댑터 상세 snapshot 조회가 하나의 `NetworkConfigurator` port에 충분히 모델링되지 않음. | P1 | `Services/NetworkConfigurationService.cs`, `ViewModels/IpSettingsViewModel.cs`, `IpSettingsViewModelTests.cs` | `domain/network/models.py`, `ports/network_configurator.py`, `infrastructure/windows/netsh_network_configurator.py`, `presentation/qt/viewmodels/network_viewmodel.py`, `panels/network_panel.py` |
| 3. PC 점검 한글 메시지/버전 확인 | Chrome/Edge/PotPlayer/Bandizip은 로컬 버전과 최신 버전을 비교. 최신 버전 조회 실패 시 “미확인”과 수동 새로고침 권장 메시지. PotPlayer는 `History/Korean.txt`의 `[YYMMDD]` 형식 우선. Bandizip은 웹 history에서 최신 버전 파싱. 결과 메시지는 C# 단계에서 한국어. | `InstalledProgramCheck`는 설치 여부만 확인. 최신 버전 네트워크 조회 없음. 메시지는 use case 영어, presentation에서 일부 한글 변환. PotPlayer/Bandizip은 파일 버전 조회 수준. | 미반영/부분 반영 | 최신 버전 조회, 버전 비교, PotPlayer history 파일 파싱, Bandizip history HTML 파싱, “미확인/업데이트 필요/최신 버전” 상태 모델 미반영. | PC 점검을 “설치 여부” 중심의 단순 Check로 포팅했고, final C#의 update check provider 분리가 없음. | P1 | `Services/PcCheckStatusDataSource.cs`, `Services/PcCheckQueryService.cs`, `PcCheckStatusDataSourceTests.cs`, `PcCheckQueryServiceTests.cs` | `application/use_cases/run_pc_checks.py`, `infrastructure/windows/installed_program_reader.py`, `presentation/qt/viewmodels/pc_check_viewmodel.py` |
| 4. 브라우저 기록 확인 | Default profile뿐 아니라 `Profile *`, `Guest Profile` 추가 프로필 존재 여부를 검사. 기본 프로필이 없어도 추가 프로필이 있으면 “기록 있음”. 파일/폴더 크기 합산은 5MB threshold 초과 시 조기 종료. 접근 불가/IO 예외는 무시. 사용자 데이터 루트가 없으면 “양호”. | Chrome/Edge `Default` profile만 검사. 추가 프로필 검사 없음. `root.rglob("*")`로 전체 순회하여 조기 종료/깊이 제한 없음. Default path 없으면 `has_history=None`으로 “경로 없음/unknown” 처리. | 잘못 포팅 | 최종 C#은 user data missing을 기록 없음으로 처리하지만 Python은 unknown으로 처리. 추가 프로필 존재 여부 누락. 대용량 캐시에서 느려질 가능성. | 브라우저 데이터 모델이 default profile path 존재 여부만 담고, user data root/additional profiles/detail 메시지를 표현하지 못함. | P0 | `Services/PcCheckStatusDataSource.cs`, `PcCheckStatusDataSourceTests.cs` | `domain/checks/models.py`, `infrastructure/windows/browser_data_reader.py`, `application/use_cases/run_pc_checks.py` |
| 5. powercfg 한국어 출력 파싱 | `Current AC Power Setting Index:`, `현재 AC 전원 설정 인덱스:`, `현재 AC 전원 설정 색인:` 모두 파싱. 실패 시 `"Error"` 반환 후 점검 실패로 표시. 값이 0이 아니면 `ConvertHexToMinutes`로 “화면 끄기(10분)”처럼 상세 표시. | 같은 3개 prefix 파싱은 반영됨. 실패 시 `None`. `PowerSettingsStatus.is_never`만 보고 OK/Warning/Unknown 판단. 어떤 항목이 몇 분으로 설정됐는지 detail 없음. | 부분 반영 | 한국어 prefix 자체는 반영됐지만 상세 minute 변환, 항목별 detail 메시지, C#의 `"Error"` fallback 의미는 미반영. | domain model이 raw hex 3개만 보유하고 presentation/use case에서 상세 문자열 생성 로직이 없음. | P2 | `Services/PcCheckStatusDataSource.cs`, `PcCheckStatusDataSourceTests.cs` | `infrastructure/windows/power_settings_reader.py`, `domain/checks/models.py`, `application/use_cases/run_pc_checks.py` |
| 6. 23시 자동종료 스케줄 점검/등록 | 점검: PowerShell ScheduledTasks로 `23시 자동 종료` 작업 조회. trigger 22:55, `shutdown(.exe)`, `-s`, `-t 300` 검증. 등록: encoded PowerShell로 `Register-ScheduledTask`, current user, highest run level, WakeToRun, 설명 포함. UI 유지보수 탭에서 등록 버튼 제공. | Python에는 23시 자동종료 check provider/use case/port/adapter/UI가 없음. PC 점검 목록에도 없음. | 미반영 | 전체 기능 누락. | 초기 PC 점검 범위에서 조회 가능한 항목 위주로 구현했고 maintenance 기능을 제외함. | P0 | `Services/PcCheckStatusDataSource.cs`, `Services/PcMaintenanceService.cs`, `ViewModels/PcMaintenanceViewModel.cs`, `PcMaintenanceServiceTests.cs`, `PcCheckQueryServiceTests.cs`, `PcCheckViewModelTests.cs` | 없음. 추가 필요: `ports/scheduled_task_reader.py`, `ports/scheduled_task_configurator.py`, `infrastructure/windows/scheduled_task_*`, `application/use_cases/run_pc_checks.py`, 신규 maintenance use case/UI |
| 7. 디스크 실제/정격 용량, BusType, SSD/HDD 판별 | `Win32_DiskDrive`와 `MSFT_PhysicalDisk`를 결합. serial/model/size tolerance로 매칭. `MediaType`과 `BusType` 매핑. `SSD (NVMe)`처럼 표시. 실제 용량 GiB와 정격 용량 power-of-two 반올림 제공. WMI 실패 시 fallback item 추가. | `Win32_DiskDrive`만 사용. `size_gb`와 `disk_type`만 모델링. `MSFT_PhysicalDisk`, BusType, actual/rated size, serial/model matching 없음. | 미반영 | final C#의 디스크 정확도 개선 전체 미반영. Python UI는 `model / size / disk_type`만 표시. | `DiskInfo` 도메인 모델이 C# final의 필드를 담지 못함. WMI reader가 PhysicalDisk namespace를 조회하지 않음. | P1 | `Services/PcInfoDataSource.cs`, `Models/Snapshots/DiskInfo.cs`, `PcInfoDataSourceDiskLogicTests.cs` | `domain/pc/models.py`, `infrastructure/windows/wmi_pc_info_reader.py`, `presentation/qt/viewmodels/pc_info_viewmodel.py`, `tests/test_load_pc_info.py` |
| 8. Busy 상태/중복 실행 방지 | MainViewModel 전역 `IsBusy`, `BusyMessage`. 주요 command는 busy 중이면 즉시 return. busy 상태 변경 시 command CanExecute 갱신. 초기화/설정/PC 정보/PC 이름 변경 흐름에 일관 적용. | 각 Panel/ViewModel에 local `is_busy`와 버튼 disable 정도만 있음. 전역 busy overlay/중복 실행 guard 없음. 일부 ViewModel 메서드는 busy 중 재진입 방지 조건 없음. | 부분 반영 | 전역 busy, busy message, command gating, long-running task async 처리 미반영. | PySide6 연결 단계에서 간단한 버튼 disable만 구현했고 MainWindow-level coordination이 없음. | P1 | `ViewModels/MainViewModel.cs`, `MainViewModelTests.cs`, `MainWindow.xaml` | `presentation/qt/main_window.py`, `presentation/qt/panels/*`, `presentation/qt/viewmodels/*` |
| 9. 제품키 provider/인증 흐름 | `SecretsProductKeyProvider`에서 Win11/Win10, Office2021/Office2024 키 선택. `SettingsActivationViewModel`은 라디오 선택 상태, `WindowsKey`, `OfficeKey`를 보유하고 선택 변경 시 키 갱신. Office 설치 상태의 recommended version으로 Office 선택 반영. 실행은 `slui.exe`/Excel 실행 후 clipboard 복사 및 auto-close 안내. | `EmbeddedProductKeyProvider`는 `local_product_keys.py`에서 key names를 찾음. UI는 Windows/Office 준비 버튼만 있고 버전 선택/추천 Office 연동/키 상태 표시 없음. Office 실행은 `excel.exe`로 완화됨. 제품키는 화면에 노출하지 않음. | 부분 반영/의도적 차이 | Win10/Win11 선택 UI, Office 2021/2024 선택 UI, Office 설치 점검 결과 기반 추천 버전 적용, auto-close dialog 미반영. 단, Python의 “키 미노출”은 보안상 의도된 개선. | final C#은 ViewModel이 키 문자열을 UI 상태로 보유하지만 Python은 ProductKeyProvider만 use case에서 호출하는 보안 우선 구조라 UX parity가 낮음. | P2 | `Services/SecretsProductKeyProvider.cs`, `ViewModels/SettingsActivationViewModel.cs`, `SettingsActivationViewModelTests.cs` | `ports/product_key_provider.py`, `infrastructure/license/embedded_product_key_provider.py`, `application/use_cases/activate_windows.py`, `activate_office.py`, `presentation/qt/viewmodels/activation_viewmodel.py`, `panels/activation_panel.py` |
| 10. 리소스/작업표시줄/로고 | `TaskbarIconService`가 Resources/TaskBar 폴더와 `TaskBar.reg` 검증, 사용자 pinned TaskBar 폴더 정리, `.lnk` 복사, `regedit /s`, Explorer 재시작. `ResourcePathResolver`는 base dir에서 최대 6단계 상위 Resources 탐색. `Images/skhu_logo.ico` 포함. | Python은 `resources/TaskBar.reg`와 resolver/package 포함만 있음. `resources/TaskBar/*.lnk`는 `.gitkeep`뿐. taskbar apply adapter/use case/UI 없음. 로고/아이콘 반영 없음. | 미반영 | 작업표시줄 적용 기능 전체 누락. 최종 C# publish output의 `.lnk` 리소스가 Python repo에 없음. 앱 아이콘/로고 미반영. | 초기 scaffolding에서 resource resolver와 packaging만 만들고 taskbar configurator/asset copy를 구현하지 않음. | P2 | `Services/TaskbarIconService.cs`, `Services/ResourcePathResolver.cs`, `TaskbarIconServiceTests.cs`, `ResourcePathResolverTests.cs`, `MainWindow.xaml`, `Images/skhu_logo.ico` | `ports/resource_resolver.py`, `infrastructure/windows/pyinstaller_resource_resolver.py`, `resources/`, `SKHU_PC_Management.spec`, `presentation/qt/main_window.py` |

## 현재 Python 버그 원인 분석

| 증상/위험 | 원인 | 관련 파일 | 영향 |
| --- | --- | --- | --- |
| 초기 실행 시 C# final과 달리 상태가 덜 채워짐 | 통합 `InitializeAsync`가 없고 각 panel의 `QTimer` 자동 로딩에 의존 | `main.py`, `main_window.py`, `pc_info_panel.py`, `network_panel.py` | 관리자 권한 누락, 설정/PC 점검 미초기화, 탭 상태 불일치 |
| 브라우저 기록 없음이 unknown으로 보일 수 있음 | Python은 default profile path가 없으면 `BrowserDataStatus(path_exists=False)`로 unknown 처리. C# final은 user data root와 추가 프로필까지 보고 기록 없음이면 양호 처리 | `browser_data_reader.py`, `run_pc_checks.py` | PC 점검 오탐/사용자 혼란 |
| PC 점검이 설치 여부 수준에 머묾 | final C#의 update/version check 흐름이 Python에 없음 | `run_pc_checks.py`, `installed_program_reader.py` | “최신 버전/업데이트 필요/미확인” 판단 불가 |
| 디스크 표시가 부정확함 | `MSFT_PhysicalDisk` 기반 bus/media metadata와 정격 용량 계산이 없음 | `domain/pc/models.py`, `wmi_pc_info_reader.py` | NVMe/SATA/USB 표시 누락, 476GiB -> 512GB 정격 표시 불가 |
| 23시 자동종료 정책을 점검하지 못함 | scheduled task reader/configurator가 없음 | 없음 | 최종 C#의 강의실 정책 점검/등록 기능 누락 |
| Busy 중 중복 실행 가능성 | ViewModel별 `is_busy`만 있고 method entry guard/전역 busy가 없음 | `presentation/qt/viewmodels/*`, `panels/*` | 장시간 작업 중 중복 클릭/상태 경합 가능 |
| 작업표시줄/로고 배포 parity 부족 | `.lnk` 리소스와 taskbar adapter 없음, 로고 asset 미반영 | `resources/`, `main_window.py`, spec | 최종 WPF 배포 UX와 다름 |

## 수정 우선순위 제안

| 우선순위 | 작업 | 이유 | 선행/주의 |
| --- | --- | --- | --- |
| P0 | `InitializeAsync`에 해당하는 Python startup coordinator 추가 | 관리자 권한/초기 상태/탭 로딩 문제의 기반 | Windows 권한 체크는 port로 분리. UI thread blocking 방지 필요 |
| P0 | 브라우저 기록 확인을 final C# 방식으로 보정 | 현재 Python은 user data missing을 unknown으로 처리해 오탐 가능 | 추가 프로필 검사, threshold 조기 종료, 접근 오류 무시 필요 |
| P0 | 23시 자동종료 스케줄 점검 추가 | final C#의 명확한 신규 정책 기능이며 현재 Python에 없음 | 등록 기능은 위험 동작이므로 먼저 조회/check만 구현 권장 |
| P1 | PC 점검 버전 확인 구조 추가 | 설치 여부와 업데이트 필요는 사용자 가치가 다름 | 네트워크 최신 버전 조회는 timeout/cache/오프라인 결과 모델 필요 |
| P1 | 디스크 모델 확장 | PC 정보 품질 차이가 큼 | `DiskInfo` 도메인 모델 확장과 UI 표시 변경 필요 |
| P1 | 네트워크 adapter snapshot 조회 추가 | 현재 IP/DNS 자동 표시가 final C#보다 부족 | PowerShell `Get-NetIPConfiguration` 또는 `netsh show config` structured parser 필요 |
| P1 | 전역 Busy/중복 실행 방지 | 런타임 안정성 | MainWindow 또는 app-level coordinator 설계 필요 |
| P2 | powercfg detail 메시지 보강 | 기능은 동작하지만 final C#에 비해 설명 부족 | hex seconds -> minutes 변환 |
| P2 | 인증 UI parity 검토 | final C#은 버전 선택/추천 Office 연동 있음 | Python 보안 정책상 제품키 화면 노출은 유지하지 않는 방향 권장 |
| P2 | 작업표시줄/리소스/로고 parity | 배포 UX 차이 | `.lnk` 리소스 확보 필요. destructive taskbar 변경은 확인/백업 고려 |

## C# 파일과 Python 파일 매핑

| 기능 | 최종 C# 파일/클래스 | 현재 Python 파일 | 상태 |
| --- | --- | --- | --- |
| App 시작/초기화 | `MainWindow.xaml.cs`, `MainViewModel.Initialization.cs`, `MainViewModel.cs` | `main.py`, `bootstrap.py`, `presentation/qt/main_window.py`, panel `QTimer` | 부분 반영 |
| 네트워크 목록/상세/IP 적용 | `NetworkConfigurationService`, `IpSettingsViewModel`, `NetworkAdapterSnapshot`, `IpSettingsViewModelTests` | `domain/network/models.py`, `ports/network_configurator.py`, `netsh_network_configurator.py`, `network_viewmodel.py`, `network_panel.py` | 목록/적용 일부 반영, snapshot 미반영 |
| PC 점검 orchestration | `PcCheckQueryService`, `PcCheckSnapshot`, `PcCheckViewModel` | `RunPcChecks`, `PcCheckViewModel` | 단순 순차 check만 반영 |
| 프로그램/브라우저 버전 점검 | `PcCheckStatusDataSource.Check*UpdateAsync` | `InstalledProgramCheck`, `WindowsInstalledProgramReader` | 최신 버전 비교 미반영 |
| 브라우저 기록 | `PcCheckStatusDataSource.CheckBrowserHistory`, tests | `WindowsBrowserDataReader`, `BrowserHistoryCheck` | 추가 프로필/누락 처리 잘못 포팅 |
| 전원 설정 | `PcCheckStatusDataSource.CheckPowerSettings`, `GetPowerCfgValue` | `WindowsPowerSettingsReader`, `PowerSettingsCheck` | prefix 파싱 반영, detail 미반영 |
| 자동종료 스케줄 | `PcCheckStatusDataSource.CheckAutoShutdownSchedule`, `PcMaintenanceService.SetAutoShutdownAt23` | 없음 | 미반영 |
| 디스크 정보 | `PcInfoDataSource.GetDiskInfo`, `DiskInfo`, `PcInfoDataSourceDiskLogicTests` | `DiskInfo`, `WmiPcInfoReader._get_disks` | final 개선 미반영 |
| Busy 상태 | `MainViewModel.IsBusy`, `BusyMessage`, command guard | 각 Qt panel `_set_busy`, ViewModel `is_busy` | 부분 반영 |
| 인증 | `SettingsActivationViewModel`, `SecretsProductKeyProvider` | `ProductKeyProvider`, `EmbeddedProductKeyProvider`, `ActivateWindows`, `ActivateOffice`, `ActivationViewModel` | 보안 구조는 개선, UX parity 부족 |
| 리소스/작업표시줄 | `TaskbarIconService`, `ResourcePathResolver`, `Resources/TaskBar.reg`, `.lnk`, `Images/skhu_logo.ico` | `ResourceResolver`, `pyinstaller_resource_resolver.py`, `resources/TaskBar.reg`, spec | resolver 일부 반영, taskbar/logo 미반영 |

## 결론

최종 C#의 staging/main 이후 변경 중 Python에 확실히 반영된 것은 일부 UI 자동 로딩, 기본 IP 입력/게이트웨이 자동 계산, 제품키 파일 경로 개선, PowerShell 기반 어댑터 목록 조회 정도다. 반면 final C#에서 실제 품질을 끌어올린 핵심은 PC 점검/초기화/디스크/브라우저 기록/자동종료/작업표시줄 쪽에 집중되어 있고, 이 영역은 Python에서 대부분 빠져 있다.

다음 구현은 기능을 새로 늘리기보다, 위 P0 항목부터 final C# 동작을 Python의 ports/adapters 구조에 맞춰 옮기는 순서가 가장 안전하다.
