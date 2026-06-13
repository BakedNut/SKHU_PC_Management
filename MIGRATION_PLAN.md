# SKHU PC Management Python 마이그레이션 계획

## 전제와 범위

- `legacy/csharp/`는 참조 전용이다. Python 마이그레이션 중에도 수정하지 않는다.
- 기존 C# 코드를 줄 단위로 번역하지 않고, 기능/유스케이스/포트/어댑터 단위로 재설계한다.
- `domain`과 `application` 계층에는 PySide6, `winreg`, `subprocess`, WMI, `netsh`, `powercfg` 직접 사용을 금지한다.
- Windows 전용 동작은 `ports` 뒤에 숨기고 `infrastructure/windows` 어댑터에서 구현한다.
- 실제 제품키는 Git에 커밋하지 않는다. 제품키 접근은 `ProductKeyProvider` 포트 뒤로 둔다.
- 이 문서는 계획 문서이며, 실제 Windows 설정 변경 기능 구현은 별도 단계에서 진행한다.

## 기존 C# 구조 요약

| 영역 | 주요 C# 위치 | 역할 |
| --- | --- | --- |
| UI | `SKHU_PC_Management/MainWindow.xaml`, `MainWindow.xaml.cs` | WPF 화면, 바인딩, 앱 로드 시 초기화 호출 |
| ViewModel | `ViewModels/*.cs` | 화면 상태, 명령, 사용자 확인 흐름 |
| 서비스 | `Services/*.cs` | WMI/레지스트리/프로세스/파일/네트워크 등 실제 동작 |
| 추상화 | `Abstractions/*.cs` | 테스트 가능한 인터페이스 |
| 모델 | `Models/Options`, `Results`, `Snapshots`, `Status`, `ViewStates` | 옵션, 결과, 조회 스냅샷, UI 상태 |
| 조립 | `Composition/MainWindowComposition.cs` | 서비스와 ViewModel 생성 |
| 테스트 | `SKHU_PC_Management.Tests/**` | 서비스, ViewModel, 조립 테스트 |
| 리소스 | `Resources/TaskBar.reg`, `Resources/TaskBar/*.lnk` | 작업표시줄 아이콘/레지스트리 적용 |

## 기능별 마이그레이션 매핑

| 기능 | 기존 C# 파일/클래스 | 관련 테스트 | Python 배치 제안 | 비고 |
| --- | --- | --- | --- | --- |
| PC 정보 조회 | `PcInfoQueryService`, `PcInfoDataSource`, `PcInfoPresentationService`, `PcInfoSnapshot`, `DiskInfo`, `PcInfoViewState` | `PcInfoQueryServiceTests`, `PcInfoPresentationServiceTests`, `MainViewModelTests` | `application/use_cases/load_pc_info.py`, `domain/pc/models.py`, `ports/pc_info_reader.py`, `infrastructure/windows/wmi_pc_info_reader.py`, `presentation/qt/viewmodels/pc_info_viewmodel.py` | WMI/레지스트리/`bcdedit`는 adapter로 격리 |
| PC 이름 변경 | `PcRenameService`, `PcRenameFlowService`, `PcRenamePresentationService`, `PcRenameFlowResult`, `PcRenameViewState` | `PcRenameServiceTests`, `PcRenameFlowServiceTests`, `PcRenamePresentationServiceTests`, `PcActionsViewModelTests` | `application/use_cases/rename_pc.py`, `domain/pc/models.py`, 신규 `ports/pc_renamer.py` 또는 `command_runner.py`, `infrastructure/windows`의 WMI rename adapter | 이름 유효성은 domain/application에서 순수 함수로 테스트 가능 |
| 기본 설정 적용 | `SettingsApplyService`, `SettingsApplyOptions`, `SettingsApplyResult`, `WindowsSystemService`, `WindowsRuntimeService`, `SettingsOptionsViewModel` | `SettingsApplyServiceTests`, `SettingsOptionsViewModelTests`, `SettingsPostApplyServiceTests`, `WindowsSystemServiceTests` | `domain/settings/definitions.py`, `domain/settings/models.py`, `application/use_cases/apply_settings.py`, `ports/registry.py`, `ports/command_runner.py`, `ports/process_launcher.py`, `infrastructure/windows/winreg_registry.py`, `subprocess_command_runner.py` | 레지스트리 정의를 데이터화하고 적용 use case는 포트만 호출 |
| 기본 설정 상태 확인 | `SettingsStatusQueryService`, `SettingsStatusDataSource`, `SettingsStatusItem`, `SettingStatus` | `SettingsStatusQueryServiceTests`, `MainViewModelTests` | `application/use_cases/check_settings_status.py`, `domain/settings/models.py`, `domain/settings/definitions.py`, `ports/registry.py`, `ports/resource_resolver.py`, Windows 상태 조회 adapter | 적용 정의와 상태 확인 정의를 같은 소스로 공유 |
| 네트워크/IP 설정 | `NetworkConfigurationService`, `IpSettingsViewModel`, `NetworkAdapterSnapshot`, `NetworkInfoItem` | `IpSettingsViewModelTests`, `FakeNetworkConfigurationService` | `application/use_cases/apply_static_ip.py`, `set_dhcp.py`, `domain/network/models.py`, `ports/network_configurator.py`, `infrastructure/windows/netsh_network_configurator.py`, `presentation/qt/viewmodels/network_viewmodel.py` | `netsh` 실행은 adapter 내부로 제한 |
| PC 점검 | `PcCheckQueryService`, `PcCheckStatusDataSource`, `PcCheckSnapshot`, `PcCheckItem`, `OfficeInstallStatus`, `PcCheckViewModel` | `PcCheckQueryServiceTests`, `PcCheckViewModelTests`, `FakePcCheckDataSource` | `application/use_cases/run_pc_checks.py`, `domain/checks/models.py`, 신규 포트 예: `pc_check_reader.py`, `browser_version_checker.py`, `power_settings_reader.py` | 네트워크 호출/파일 크기 조회/휴지통 API/powercfg를 세부 포트로 분리 권장 |
| Windows/Office 인증 | `SettingsActivationViewModel`, `SecretsProductKeyProvider`, `IProductKeyProvider`, `WpfClipboardService`, `ProcessService` | `SettingsActivationViewModelTests`, `FakeProductKeyProvider`, `FakeClipboardService`, `FakeProcessService` | `application/use_cases/activate_windows.py`, `ports/product_key_provider.py`, `ports/process_launcher.py`, 신규 `ports/clipboard.py`, `infrastructure/license/*`, Qt viewmodel | 기존은 키 복사 후 `slui.exe`/Excel 실행. 제품키 저장소는 반드시 secret provider 뒤로 격리 |
| 유지보수 작업 | `PcMaintenanceService`, `PcMaintenanceViewModel` | `PcMaintenanceViewModelTests`, `FakePcMaintenanceService` | 신규 use case 예: `empty_recycle_bin.py`, `clear_browser_history.py`, `set_power_never.py`; 신규 ports 예: `recycle_bin.py`, `browser_data_cleaner.py`, `power_configurator.py` | 실제 삭제/전원 변경은 위험 동작으로 확인 대화와 관리자 권한 처리 필요 |
| 리소스/작업표시줄/바탕화면 설정 | `TaskbarIconService`, `ResourcePathResolver`, `WindowsSystemService.SetDefaultWallpaper`, `Resources/TaskBar.reg`, `Resources/TaskBar/*.lnk` | `TaskbarIconServiceTests`, `ResourcePathResolverTests`, `WindowsSystemServiceTests` | `ports/resource_resolver.py`, 신규 `ports/taskbar_configurator.py`, `infrastructure/windows/pyinstaller_resource_resolver.py`, taskbar adapter, `resources/` | PyInstaller `_MEIPASS`와 개발 경로 모두 고려 |
| 프로그램 실행 | `PcProgramLaunchService`, `PcActionsViewModel`, `ProcessService` | `PcActionsViewModelTests`, `FakePcProgramLaunchService` | `ports/process_launcher.py`, 신규 use case 예: `launch_program.py`, Windows program locator adapter | Chrome/Edge/PotPlayer/Bandizip 경로 탐색과 실행 분리 |

## 레지스트리 사용 지점

| 목적 | Hive/경로 | 값 | 기대값/동작 | 기존 C# 위치 | Python 위치 | 위험도/권한 |
| --- | --- | --- | --- | --- | --- | --- |
| 자주 사용하는 폴더 숨김 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer` | `ShowFrequent` | `0` | `SettingsApplyService`, `SettingsStatusQueryService` | `domain/settings/definitions.py`, `ports/registry.py` | 낮음, 사용자 설정 |
| 최근 사용 항목 숨김 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer` | `ShowRecent` | `0` | 동일 | 동일 | 낮음, 사용자 설정 |
| 탐색기 시작 위치 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `LaunchTo` | `1` | 동일 | 동일 | 낮음 |
| 파일 확장자 표시 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `HideFileExt` | `0` | 동일 | 동일 | 낮음 |
| 파일 선택 확인란 비활성화 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `AutoCheckSelect` | `0` | 동일 | 동일 | 낮음 |
| 바탕화면 내 PC 표시 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel` | `{20D04FE0-3AEA-1069-A2D8-08002B30309D}` | `0` | 동일 | 동일 | 낮음 |
| 바탕화면 제어판 표시 | 같은 경로 | `{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}` | `0` | 동일 | 동일 | 낮음 |
| 사용자 폴더 아이콘 숨김/기본 배경 상태 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel` | `{2CC5CA98-6485-489A-920E-B3E88A6CCCE3}` | `1` | `WindowsSystemService`, `SettingsStatusQueryService` | settings definition + registry adapter | 낮음 |
| 기본 배경 유형 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers` | `BackgroundType` | `0` | `WindowsSystemService`, `SettingsStatusQueryService` | settings definition + registry adapter | 낮음 |
| 기본 배경 파일 | `HKCU\Control Panel\Desktop` | `Wallpaper` | `%WINDIR%\Web\Wallpaper\Windows\img0.jpg` | 동일 | 동일 | 낮음 |
| 부팅 시 암호 입력 생략 | `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device` | `DevicePasswordLessBuildVersion` | `0` | `SettingsApplyService`, `SettingsStatusQueryService` | settings definition + registry adapter | 중간, 관리자 권한 필요 가능 |
| 빠른 시작 비활성화 | `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power` | `HiberbootEnabled` | `0` | 동일 | 동일 | 중간, 관리자 권한/재부팅 필요 |
| Edge 바로가기 생성 정책 | `HKLM\SOFTWARE\Policies\Microsoft\EdgeUpdate` | `CreateDesktopShortcutDefault` | `0` | `WindowsSystemService`, `SettingsStatusQueryService` | settings/resource adapter | 중간, 관리자 권한 필요 |
| 작업 보기 버튼 숨김 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `ShowTaskViewButton` | `0` | `SettingsApplyService`, `SettingsStatusQueryService` | settings definition | 낮음, Explorer 재시작 가능 |
| 검색 아이콘만 표시 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Search` | `SearchboxTaskbarMode` | `1` | 동일 | settings definition | 낮음, Explorer 재시작 가능 |
| Win11 시작 메뉴 고정 항목 더 보기 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `Start_Layout` | `1` | 동일 | settings definition | 낮음, Win11 조건부 |
| Win11 최근 추가 앱 숨김 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Start` | `ShowRecentList` | `0` | 동일 | settings definition | 낮음 |
| Win11 자주 사용 앱 숨김 | 같은 경로 | `ShowFrequentList` | `0` | 동일 | settings definition | 낮음 |
| Win11 추천 파일 숨김 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` | `Start_TrackDocs` | `0` | 동일 | settings definition | 낮음 |
| Win11 팁/권장 사항 숨김 | 같은 경로 | `Start_IrisRecommendations` | `0` | 동일 | settings definition | 낮음 |
| Win11 계정 알림 숨김 | 같은 경로 | `Start_AccountNotifications` | `0` | 동일 | settings definition | 낮음 |
| Secure Boot 상태 조회 | `HKLM\SYSTEM\CurrentControlSet\Control\SecureBoot\State` | `UEFISecureBootEnabled` | `1`이면 활성 | `PcInfoDataSource` | `wmi_pc_info_reader.py` 또는 별도 security status adapter | 조회 전용 |
| Secure Boot 정책 조회 | `HKLM\SYSTEM\CurrentControlSet\Control\Secure Boot\Policy` | 값 존재 여부 | 정책 존재 시 활성 추정 | `PcInfoDataSource` | 동일 | 조회 전용 |
| Boot Mode 조회 | `HKLM\System\CurrentControlSet\Control` | `PEFirmwareType` | `2` UEFI, `1` Legacy | `PcInfoDataSource` | PC info adapter | 조회 전용 |
| TPM fallback 조회 | `HKLM\SYSTEM\CurrentControlSet\Services\TPM` | `Start` | `3`이 아니면 활성 추정 | `PcInfoDataSource` | PC info adapter | 조회 전용 |
| PotPlayer 경로 조회 | `HKLM\SOFTWARE\DAUM\PotPlayer64`, `HKLM\SOFTWARE\DAUM\PotPlayer` | `ProgramPath` | 실행 파일 경로 | `PcProgramLaunchService`, `PcCheckStatusDataSource` | program locator/check adapter | 조회 전용 |
| Bandizip 경로 조회 | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Bandizip`, `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Bandizip` | `InstallLocation` | 실행 파일 경로 | `PcProgramLaunchService`, `PcCheckStatusDataSource` | program locator/check adapter | 조회 전용 |
| Office 설치 확인 | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`, `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall` | `DisplayName` | Office 2021/2024 계열 확인 | `PcCheckStatusDataSource` | Office check adapter | 조회 전용 |
| 작업표시줄 고정 상태 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Taskband` 등 | `Favorites*`, `AuxilliaryPins/*` | `TaskBar.reg` import | `Resources/TaskBar.reg`, `TaskbarIconService` | resource/taskbar adapter | 중간, Explorer 재시작 |

## 외부 명령/프로세스 실행 지점

| 명령/프로그램 | 인자 | 목적 | 기존 C# 위치 | Python 포트/어댑터 | 위험도/권한 |
| --- | --- | --- | --- | --- | --- |
| `net` | `accounts /maxpwage:unlimited` | 계정 암호 만료 비활성화 | `SettingsApplyService` | `CommandRunner` + 계정 설정 use case | 높음, 관리자 권한 |
| `RUNDLL32.EXE` | `user32.dll,UpdatePerUserSystemParameters` | 사용자 시스템 파라미터 갱신 | `SettingsApplyService`, `WindowsRuntimeService` | `ProcessLauncher` 또는 Windows settings adapter | 낮음~중간 |
| `bcdedit` | `/enum {current}` | Boot Mode fallback 조회 | `PcInfoDataSource` | `CommandRunner` in PC info adapter | 조회지만 관리자 권한/로캘 이슈 가능 |
| `netsh` | `interface ip set address "{adapter}" static ...` | 정적 IP 설정 | `NetworkConfigurationService` | `NetworkConfigurator` adapter | 높음, 관리자 권한, 네트워크 단절 가능 |
| `netsh` | `interface ip set dns "{adapter}" static {dns}` | DNS 설정 | 동일 | 동일 | 높음 |
| `netsh` | `interface ip add dns "{adapter}" {dns2} index=2` | 보조 DNS 추가 | 동일 | 동일 | 높음 |
| `netsh` | `interface ip set address "{adapter}" dhcp` | DHCP 전환 | 동일 | 동일 | 높음 |
| `netsh` | `interface ip set dns "{adapter}" dhcp` | DNS DHCP 전환 | 동일 | 동일 | 높음 |
| `powercfg` | `/q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE` | AC 화면 끄기 상태 조회 | `PcCheckStatusDataSource` | power settings reader adapter | 조회 전용 |
| `powercfg` | `/q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` | AC 절전 상태 조회 | 동일 | 동일 | 조회 전용 |
| `powercfg` | `/q SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE` | AC 최대 절전 상태 조회 | 동일 | 동일 | 조회 전용 |
| `powercfg` | `-change -monitor-timeout-ac 0` 등 6개 | 전원 옵션 모두 안 함 | `PcMaintenanceService` | power configurator adapter | 중간, 시스템 정책 변경 |
| `shutdown` | `/r /t 0` | PC 이름 변경 직후 즉시 재부팅 | `PcRenameFlowService` | `ProcessLauncher` 또는 restart port | 높음, 사용자 작업 손실 가능 |
| `shutdown` | `/r /t 5 /f /c "..."` | PC 이름 자동 변경 후 강제 재부팅 예약 | `PcRenameFlowService`, `WindowsSystemService` | restart port | 높음, 강제 종료 |
| `taskkill` | `/F /IM chrome.exe /T` | Chrome 종료 후 기록 삭제 | `PcMaintenanceService` | browser maintenance adapter | 높음, 데이터 손실 가능 |
| `taskkill` | `/F /IM msedge.exe /T`, `/F /IM msedgewebview2.exe /T` | Edge 종료 후 기록 삭제 | 동일 | 동일 | 높음 |
| `regedit.exe` | `/s "{Resources}\TaskBar.reg"` | 작업표시줄 레지스트리 import | `TaskbarIconService` | taskbar adapter + resource resolver | 중간, 사용자 작업표시줄 변경 |
| `explorer.exe` | 없음 | Explorer 재시작 | `WindowsSystemService` | process launcher | 중간, 셸 재시작 |
| `slui.exe` | 없음 | Windows 인증 창 열기 | `SettingsActivationViewModel` | activation UI/use case + process launcher | 낮음, 실제 인증은 사용자 진행 |
| `EXCEL.EXE` | 없음 | Office 키 복사 후 Excel 실행 | `SettingsActivationViewModel` | process launcher + clipboard port | 낮음 |
| Chrome/Edge/PotPlayer/Bandizip exe | 없음 | 앱 실행 버튼 | `PcProgramLaunchService` | program launcher/locator | 낮음 |

## WMI 사용 지점

| WMI 클래스/네임스페이스 | 목적 | 기존 C# 위치 | Python 위치 | 주의사항 |
| --- | --- | --- | --- | --- |
| `Win32_OperatingSystem` | Windows caption/build/architecture, Win10/11 판별 | `PcInfoDataSource`, `SettingsStatusDataSource` | `wmi_pc_info_reader.py`, settings status adapter | 빌드 번호와 릴리스명 매핑을 테스트로 고정 |
| `Win32_Processor` | CPU 이름 | `PcInfoQueryService` -> `PcInfoDataSource.GetSystemInfo` | `wmi_pc_info_reader.py` | WMI 실패 시 명확한 fallback |
| `Win32_PhysicalMemory` | RAM 용량/속도/DDR 타입/슬롯 수 | `PcInfoDataSource.GetRamInfo` | `wmi_pc_info_reader.py` | `SMBIOSMemoryType`/`MemoryType` 둘 다 고려 |
| `Win32_VideoController` | 물리 GPU 이름 | `PcInfoDataSource.GetGpuInfo` | `wmi_pc_info_reader.py` | 가상/원격 GPU 필터 유지 |
| `Win32_DiskDrive` | 디스크 모델/크기/회전율 | `PcInfoDataSource.GetDiskInfo` | `wmi_pc_info_reader.py` | `MediaRotationRate` 누락 가능 |
| `root\Microsoft\Windows\Storage: MSFT_PhysicalDisk` | HDD/SSD 판별 보강 | `PcInfoDataSource.GetPhysicalDiskMediaType` | `wmi_pc_info_reader.py` | 일부 Windows에서 권한/제공자 차이 가능 |
| `root\CIMV2\Security\MicrosoftTpm: Win32_Tpm` | TPM 설치/버전 | `PcInfoDataSource.GetTpmInfo` | `wmi_pc_info_reader.py` | 실패 시 registry fallback |
| `Win32_ComputerSystem.Rename` | PC 이름 변경 | `PcRenameService` | 별도 PC renamer adapter | 관리자 권한과 재부팅 필요 |

## netsh 사용 지점

| 기능 | 명령 | 기존 C# 위치 | Python 위치 | 위험/권한 |
| --- | --- | --- | --- | --- |
| 정적 IP 설정 | `netsh interface ip set address "{adapter}" static {ip} {mask} {gateway}` | `NetworkConfigurationService.SetStaticIp` | `netsh_network_configurator.py` | 관리자 권한, 네트워크 단절 가능 |
| DNS DHCP 설정 | `netsh interface ip set dns "{adapter}" dhcp` | DNS1 비어있을 때, `SetDhcp` | 동일 | 관리자 권한 |
| DNS 정적 설정 | `netsh interface ip set dns "{adapter}" static {dns1}` | `SetStaticIp` | 동일 | 관리자 권한 |
| 보조 DNS 추가 | `netsh interface ip add dns "{adapter}" {dns2} index=2` | `SetStaticIp` | 동일 | 관리자 권한 |
| DHCP 전환 | `netsh interface ip set address "{adapter}" dhcp` | `SetDhcp` | 동일 | 관리자 권한 |

## powercfg 사용 지점

| 기능 | 명령 | 기존 C# 위치 | Python 위치 | 위험/권한 |
| --- | --- | --- | --- | --- |
| 화면 끄기 상태 조회 | `powercfg /q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE` | `PcCheckStatusDataSource.CheckPowerSettings` | power settings reader adapter | 조회 전용 |
| 절전 상태 조회 | `powercfg /q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` | 동일 | 동일 | 조회 전용 |
| 최대 절전 상태 조회 | `powercfg /q SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE` | 동일 | 동일 | 조회 전용 |
| AC/DC 화면 끄기 비활성화 | `powercfg -change -monitor-timeout-ac 0`, `-monitor-timeout-dc 0` | `PcMaintenanceService.SetPowerNever` | power configurator adapter | 시스템 설정 변경 |
| AC/DC 절전 비활성화 | `powercfg -change -standby-timeout-ac 0`, `-standby-timeout-dc 0` | 동일 | 동일 | 시스템 설정 변경 |
| AC/DC 최대 절전 비활성화 | `powercfg -change -hibernate-timeout-ac 0`, `-hibernate-timeout-dc 0` | 동일 | 동일 | 시스템 설정 변경 |

## 리소스 파일 사용 지점

| 리소스 | 사용 목적 | 기존 C# 위치 | Python 위치 | 주의사항 |
| --- | --- | --- | --- | --- |
| `Resources/TaskBar.reg` | 작업표시줄 고정 레지스트리 import | `TaskbarIconService`, `Resources/TaskBar.reg` | `resources/TaskBar.reg`, taskbar adapter, `ResourceResolver` | binary-like registry payload이므로 인코딩/경로 고정 주의 |
| `Resources/TaskBar/File Explorer.lnk` | 작업표시줄 고정 아이콘 복사 | `TaskbarIconService` | `resources/TaskBar/` | PyInstaller 포함 데이터 지정 필요 |
| `Resources/TaskBar/Google Chrome.lnk` | 작업표시줄 고정 아이콘 복사 | 동일 | 동일 | 대상 경로 청소 전 백업/확인 필요 |
| `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar` | 작업표시줄 바로가기 대상 폴더 | `TaskbarIconService`, `SettingsStatusDataSource` | taskbar adapter | 기존 사용자 고정 항목 삭제 위험 |
| `%WINDIR%\Web\Wallpaper\Windows\img0.jpg` | 기본 배경화면 경로 | `WindowsSystemService`, `SettingsStatusQueryService` | settings definition/resource-aware adapter | Windows 버전별 경로 존재 확인 |

## 위험 동작과 관리자 권한

| 동작 | 위험도 | 관리자 권한 필요 | 사용자 확인 필요 | 마이그레이션 방침 |
| --- | --- | --- | --- | --- |
| HKLM 레지스트리 쓰기 | 높음 | 예 | 예 | `Registry` port adapter에서만 수행, dry-run/test double 우선 |
| HKCU 레지스트리 쓰기 | 중간 | 보통 아니오 | 설정 묶음 적용 전 예 | 정의 기반 적용, 변경 내역 결과 반환 |
| PC 이름 변경 | 높음 | 예 | 예 | 이름 검증과 실제 rename adapter 분리, 재부팅은 별도 명령 |
| 강제/예약 재부팅 | 높음 | 예 | 예 | restart 전용 port로 분리, UI에서 명확히 확인 |
| IP/DNS 변경 | 높음 | 예 | 예 | 어댑터/입력 검증 선행, 실패 결과 상세화 |
| 브라우저 프로세스 강제 종료 | 높음 | 보통 아니오 | 예 | 열린 작업 손실 경고 |
| 브라우저 사용자 데이터 삭제 | 높음 | 보통 아니오 | 예 | 삭제 대상 목록과 백업/복구 전략 검토 |
| 휴지통 비우기 | 중간 | 보통 아니오 | 예 | Win32 shell adapter로 분리 |
| 전원 옵션 변경 | 중간 | 환경에 따라 다름 | 예 | `powercfg` adapter, 적용 전 현재 상태 표시 |
| Explorer 재시작 | 중간 | 보통 아니오 | 예 또는 후처리 안내 | 작업표시줄/Explorer 설정 적용 후 선택적 실행 |
| 작업표시줄 폴더 비우기/복사 | 중간~높음 | 보통 아니오 | 예 | 기존 고정 항목 백업 검토 |
| 제품키 표시/복사 | 중간 | 아니오 | 예 | secret provider/clipboard port, 로그 출력 금지 |
| 외부 업데이트 서버 조회 | 낮음~중간 | 아니오 | 아니오 | timeout/cache/오프라인 결과 모델링 |

## 테스트 마이그레이션 전략

- C# 테스트의 fake service 패턴은 Python에서도 유지한다.
- `domain` 테스트는 dataclass/정의/검증 규칙만 다루고 Windows API를 import하지 않는다.
- `application` 테스트는 fake port로 use case 결과를 검증한다.
- `infrastructure/windows` 테스트는 기본적으로 dry-run 또는 command builder 검증으로 시작한다.
- 실제 레지스트리/netsh/powercfg/WMI 통합 테스트는 별도 marker 예: `pytest.mark.windows_integration`으로 분리한다.
- 제품키 테스트는 `NullProductKeyProvider`와 fake provider만 사용하고 실제 `secrets/product_keys.py`를 요구하지 않는다.

## 구현 우선순위 제안

| 우선순위 | 항목 | 이유 |
| --- | --- | --- |
| 1 | 설정 정의/적용 | 레지스트리 기반 기능이 많고 상태 확인과 UI의 기반이 된다. 정의를 데이터화하면 테스트 범위가 명확해진다. |
| 2 | 설정 상태 확인 | 적용과 같은 정의를 공유해 회귀를 줄일 수 있고, 실제 변경 없이도 사용자 가치가 있다. |
| 3 | PC 정보 조회 | 대부분 조회 기능이라 위험도가 낮고 WMI adapter 구조를 검증하기 좋다. |
| 4 | 네트워크 설정 | 위험도가 높으므로 앞선 port/use case 패턴이 안정된 뒤 구현한다. |
| 5 | PC 점검 | 외부 네트워크, 파일 시스템, Win32 API, powercfg 조회가 섞여 있어 세부 포트 분리가 필요하다. |
| 6 | 인증 기능 | 제품키 보안 정책과 UI/clipboard/process 흐름을 명확히 한 뒤 연결한다. |
| 7 | PySide6 UI 연결 | use case가 안정된 뒤 얇은 ViewModel/패널에 바인딩한다. |
| 8 | PyInstaller 패키징 | 리소스 포함, 관리자 권한 manifest, secret 제외 정책을 마지막에 검증한다. |

## 최종 권장 구현 순서

1. 설정 정의/적용
2. 설정 상태 확인
3. PC 정보 조회
4. 네트워크 설정
5. PC 점검
6. 인증 기능
7. PySide6 UI 연결
8. PyInstaller 패키징
