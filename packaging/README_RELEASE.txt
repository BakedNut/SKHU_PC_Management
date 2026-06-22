SKHU PC Management 배포 안내
================================

이 폴더는 PyInstaller onedir 배포본입니다.

실행 파일:
- SKHU_PC_Management.exe

필수 포함 항목:
- _internal/
- _internal/resources/ 또는 resources/
- resources/images/skhu_logo.ico
- resources/TaskBar.reg
- resources/TaskBar/Google Chrome.lnk
- resources/23시 자동종료 취소.lnk

제품키 파일:
- 실제 제품키는 Git에 포함하지 않습니다.
- 제품키를 로컬 파일로 사용하는 정책이라면 빌드 머신에서만
  src/skhu_pc_management/infrastructure/license/local_product_keys.py를 준비합니다.
- local_product_keys.example.py를 local_product_keys.py로 복사한 뒤 실제 값을 입력합니다.
- 제품키 값은 화면, 로그, 문서에 출력하지 않습니다.

주의:
- 앱은 관리자 권한 실행이 필요할 수 있습니다.
- 기본 설정 적용, 네트워크 변경, 인증 준비, 작업표시줄 적용, 자동종료 등록은 실제 Windows 테스트 PC에서만 검증합니다.
- 작업표시줄 Chrome 바로가기는 Google Chrome.lnk 이름과 실제 chrome.exe 대상 경로 기준으로 검증합니다.
- Chrome/Edge 사용자 데이터 초기화는 User Data 폴더 전체 삭제입니다.
- UI 자동화 테스트는 SKHU_PC_MANAGEMENT_TEST_MODE=1 상태에서 실행하세요.
