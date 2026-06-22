# RELEASE_CHECKLIST

SKHU PC Management 릴리스 전후 점검표입니다. 실제 Windows 설정 변경은 폐기 가능한 Windows 테스트 PC에서만 수행합니다.

## 1. 빌드 전 확인

- [ ] `git status --short`가 의도한 변경만 포함한다.
- [ ] 실제 제품키 파일 `src/skhu_pc_management/infrastructure/license/local_product_keys.py`가 Git에 포함되어 있지 않다.
- [ ] 필요한 경우 빌드 머신에만 `local_product_keys.py`를 준비했다.
- [ ] `resources/images/skhu_logo.ico`가 존재한다.
- [ ] `resources/TaskBar.reg`가 존재한다.
- [ ] `resources/TaskBar/Google Chrome.lnk`가 존재한다.
- [ ] `resources/23시 자동종료 취소.lnk`가 존재한다.
- [ ] `SKHU_PC_Management.spec`에 `uac_admin=True`, `console=False`, 아이콘, resources datas가 유지되어 있다.

## 2. 명령 실행

PowerShell 기준:

```powershell
python -m pytest
.\scripts\build.ps1
.\scripts\check_dist.ps1
```

직접 PyInstaller를 실행하는 경우:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller SKHU_PC_Management.spec --noconfirm
.\scripts\check_dist.ps1
```

선택적 onefile 확인:

```powershell
.\scripts\build.ps1 -OneFile
```

## 3. dist 구조 확인

```text
dist\SKHU_PC_Management\
  SKHU_PC_Management.exe
  _internal\
    resources\
      23시 자동종료 취소.lnk
      TaskBar.reg
      images\skhu_logo.ico
      TaskBar\
        File Explorer.lnk
        Google Chrome.lnk
  README_RELEASE.txt
```

- [ ] `SKHU_PC_Management.exe`가 존재한다.
- [ ] `_internal\resources` 또는 `resources` 폴더가 존재한다.
- [ ] `README_RELEASE.txt`가 배포본 root에 있다.
- [ ] 작업표시줄 리소스가 포함되어 있다.

## 4. 안전 모드 확인

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
.\dist\SKHU_PC_Management\SKHU_PC_Management.exe
```

- [ ] 상단 또는 상태 영역에 테스트 모드가 표시된다.
- [ ] 시스템 설정 적용 버튼이 비활성화된다.
- [ ] 네트워크 IP 적용/DHCP 전환 버튼이 비활성화된다.
- [ ] 인증 준비 버튼이 비활성화된다.
- [ ] Chrome/Edge 사용자 데이터 초기화 버튼이 비활성화된다.
- [ ] 전원 옵션/23시 자동종료 적용 버튼이 비활성화된다.
- [ ] PC 이름 변경 버튼이 비활성화된다.
- [ ] PC 정보 조회, 설정 상태 확인, PC 점검, 네트워크 어댑터 조회는 가능하다.

## 5. 실제 Windows 테스트 PC 확인

### 시작/기본 화면

- [ ] 관리자 권한 실행 시 UAC 프롬프트가 표시된다.
- [ ] 일반 권한 실행 시 관리자 권한 경고가 앱을 중단하지 않는다.
- [ ] PC 정보가 자동 로드된다.
- [ ] PC 이름, 사용자, Windows 버전, CPU/RAM/GPU, 디스크, TPM, Secure Boot, Boot Mode가 표시된다.
- [ ] `PC 이름 변경`은 Windows 설정의 시스템 정보 화면을 연다.
- [ ] `PC 이름 변경` 성공 시 완료 팝업 없이 Windows 설정 화면이 열린다.
- [ ] `PC 이름 변경` 실패 시 경고 팝업이 표시된다.

### 작업 센터

- [ ] 상단 요약은 `설정 상태`, `PC 점검`, `강의실 정책`만 표시된다.
- [ ] 인증 카드에서 제품키가 화면에 표시되지 않는다.
- [ ] Office 감지 결과는 인증 카드 Office row에 표시된다.
- [ ] 설정 상태 표는 `설정 항목 | 현재 상태 | 상세` 3열이다.
- [ ] Windows 10 선택 시 Win11 전용 시작 메뉴 항목이 표시되지 않는다.
- [ ] 설정 적용 후 선택 항목뿐 아니라 표시 대상 전체 상태가 갱신된다.
- [ ] Explorer 재시작 실패가 설정 실패처럼 반복 표시되지 않는다.
- [ ] PC 점검 결과 표에 `Office 설치 확인` 행이 표시되지 않는다.
- [ ] `Chrome 실행`, `Edge 실행`, `팟플레이어 실행`, `반디집 실행` 성공 시 완료 팝업이 뜨지 않는다.
- [ ] 위 단순 실행 버튼 실패 시 경고 팝업이 표시된다.

### 팝업/테마

- [ ] Windows 다크 테마에서 확인/경고 팝업 배경이 흰색으로 표시된다.
- [ ] Windows 다크 테마에서 팝업 본문 텍스트가 읽힌다.
- [ ] Windows 다크 테마에서 `OK`, `Yes`, `No` 버튼 텍스트가 읽힌다.
- [ ] `Chrome 실행`, `Edge 실행`, `팟플레이어 실행`, `반디집 실행` 성공 시 완료 팝업이 뜨지 않는다.
- [ ] 위 단순 실행 버튼 실패 시 경고 팝업이 뜬다.
- [ ] `PC 이름 변경` 성공 시 완료 팝업 없이 Windows 설정 화면이 열린다.
- [ ] `PC 이름 변경` 실패 시 경고 팝업이 뜬다.

### 작업표시줄

- [ ] `작업표시줄 아이콘 설정` 적용 시 dry-run 메시지가 아니라 실제 적용 경로가 실행된다.
- [ ] target TaskBar 폴더에 `Google Chrome.lnk`가 생성되고 `Chrome.lnk`는 생성되지 않는다.
- [ ] `Google Chrome.lnk`의 TargetPath가 실제 `chrome.exe`다.
- [ ] `TaskBar.reg` import 실패 시에는 실패로 표시된다.
- [ ] Explorer 재시작 실패만으로 작업표시줄 적용이 실패 처리되지 않는다.
- [ ] 상태 상세에서 누락/추가 shortcut과 Chrome 대상 문제가 정확히 표시된다.

### 네트워크

- [ ] 물리 Ethernet/Wi-Fi 어댑터가 표시된다.
- [ ] 현재 네트워크 상태 표에 IP 할당 방식, IP, subnet, gateway, DNS가 표시된다.
- [ ] `192.168.` 같은 불완전 IP는 적용 전에 한국어 validation으로 차단된다.
- [ ] 고정 IP/DHCP 적용 후 어댑터 상태가 다시 로드된다.

### PC 점검/강의실 작업

- [ ] 설치 프로그램/버전 메시지가 한국어로 표시된다.
- [ ] Chrome/Edge 사용자 데이터 상태가 표시된다.
- [ ] 전원 옵션 상태가 표시된다.
- [ ] 자동종료 작업이 없으면 `주의 / 23시 자동종료 스케줄이 등록되어 있지 않습니다.`로 표시된다.
- [ ] ScheduledTasks 조회 실패는 `알 수 없음 / 자동종료 스케줄 상태를 확인할 수 없습니다.`로 표시된다.
- [ ] 23시 자동종료 적용 후 현재 사용자 바탕화면에 `23시 자동종료 취소.lnk`가 복사된다.
- [ ] 취소 shortcut이 리소스 원본과 다르면 자동종료 점검이 정상으로 표시되지 않는다.

### 위험 작업

- [ ] Chrome/Edge 사용자 데이터 초기화는 `User Data` 전체 삭제 위험을 설명하는 확인 대화상자를 표시한다.
- [ ] 폐기 가능한 테스트 계정이 아니면 Chrome/Edge 사용자 데이터 초기화를 실행하지 않는다.
- [ ] 전원 옵션 변경과 자동종료 등록은 확인 대화상자를 거친다.
- [ ] 인증 준비 후 클립보드에 제품키가 남을 수 있으므로 운영 절차에 맞게 정리한다.

## 6. 릴리스 판정

- [ ] `python -m pytest` 통과.
- [ ] PyInstaller onedir 빌드 성공.
- [ ] `scripts/check_dist.ps1` 통과.
- [ ] 테스트 모드 수동 확인 완료.
- [ ] Windows 테스트 PC smoke test 완료.
- [ ] 제품키/민감 파일이 Git과 문서에 포함되지 않음.
- [ ] README와 docs가 최신 UI/동작과 일치함.
