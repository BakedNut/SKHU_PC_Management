# 성능 계측 및 회귀 검증

## Profiling

Windows 개발/테스트 PC에서 다음 환경변수로 계측한다.

```powershell
$env:SKHU_PC_MANAGEMENT_PROFILE_STARTUP = "1"
$env:SKHU_PC_MANAGEMENT_PROFILE_TABS = "1"
python -m skhu_pc_management
```

- `SKHU_PC_MANAGEMENT_PROFILE_STARTUP=1`: PC 정보 단계별 시간과 WMI class별 시간을 출력한다.
- `SKHU_PC_MANAGEMENT_PROFILE_TABS=1`: 네트워크 탭, 작업 센터, 전원 설정, 예약 작업, 설정 provider 구간 시간을 출력한다.
- WMI 조회 실패는 기본 실행에서는 조용히 fallback/unknown 처리한다. startup profiling이 켜진 경우에만 `pc_info.wmi.<Class>[namespace] failed: <error>` 형식으로 짧게 출력한다.

현재 Codex 검증 환경에서는 `python` 명령이 PATH에 없고 프로젝트 `.venv`의 base interpreter 경로가 깨져 있으며, bundled test runtime에는 PySide6가 없어 GUI profiling 실행을 완료하지 못했다. 대신 단위 테스트 기반 회귀 검증을 수행했다.

## PC 정보

- OS/CPU는 registry fast path를 우선하고 WMI fallback을 유지한다.
- Windows 11 build(`22000+`)에서 registry `ProductName`이 Windows 10으로 남아 있으면 Windows 11 caption으로 보정한다.
- WMI client는 namespace별로 재사용한다.
- RAM은 `Win32_PhysicalMemory` module capacity 합계를 우선한다. module capacity가 없을 때만 `GlobalMemoryStatusEx` total을 fallback으로 사용한다.
- RAM 클럭은 `Win32_PhysicalMemory.Speed`만 사용한다. `ConfiguredClockSpeed`는 사용하지 않는다.
- TPM은 `Win32_Tpm.SpecVersion`을 우선한다. registry `Services\TPM\Start`는 disabled 판단이나 version 추론에 사용하지 않는다.
- 디스크는 Storage WMI로 보강하되, Storage WMI 실패/빈 결과에서도 `Win32_DiskDrive` 기반 row와 NVMe/SSD/HDD summary를 표시한다.
- PC 정보 대표 네트워크는 `GetAdaptersAddresses` 기반 fast path를 우선하고, GUID 대신 friendly name/description/type을 표시한다.

## 네트워크 탭

- 어댑터 목록은 `GetAdaptersAddresses` fast path를 우선한다.
- registry TCP/IP interface 값으로 gateway, DHCP, DNS, subnet mask를 보강한다.
- Ethernet/Wi-Fi 실제 어댑터를 우선하고 virtual/VPN/VM/Docker/WSL/Bluetooth/Loopback/Tunnel 계열은 제외한다.
- fast path 결과가 하나 이상 있으면 일부 필드가 비어도 PowerShell fallback을 강제하지 않는다.

## 작업 센터

- 설정 상태 확인과 PC 점검은 병렬 실행한다.
- 설정 provider 내부도 가능한 범위에서 병렬 실행하고, 결과 순서는 UI 표시 순서를 유지한다.
- provider/check 실패는 해당 항목의 unknown/error 결과로 격리한다.
- 전원 옵션은 통합 `powercfg` 조회를 우선한다.
- Scheduled Task는 `schtasks` CSV fast path와 PowerShell fallback을 유지한다.
- 암호 만료는 `net accounts` fast path를 우선한다.
- 작업표시줄 shortcut target 상세 확인은 기본 상태 확인에서 생략한다.

## 23시 자동종료

- 적용 정책은 22:55에 `shutdown.exe -s -t 300`을 실행해 23:00 종료를 목표로 한다.
- 취소 바로가기 `23시 자동종료 취소.lnk` 검사는 의도된 점검 항목이다.
- task가 정상이어도 취소 바로가기가 없거나 원본과 다르면 `WARNING`을 유지한다.
- 한국어 `schtasks` 시간 `오후 10:55:00`은 `22:55`로 파싱한다.

## 검증 결과

- `python -m pytest`: `370 passed, 2 skipped`.
- GUI profiling: 현재 Codex 환경의 Python/PySide6 제약으로 직접 완료하지 못함. Windows 개발 PC에서 위 profiling 명령으로 startup, network tab, action center refresh를 확인해야 한다.
- 남은 병목은 profiling 출력에서 300ms 이상 구간이 확인될 때 별도 기록한다.
