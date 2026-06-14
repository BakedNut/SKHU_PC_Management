SKHU PC Management 배포 안내
================================

이 폴더는 PyInstaller onedir 배포본입니다.

실행 파일:
- SKHU_PC_Management.exe

필수 포함 항목:
- _internal/
- resources/
- resources/images/skhu_logo.ico
- resources/TaskBar.reg
- resources/TaskBar/*.lnk (작업표시줄 리소스를 배포하는 경우)

제품키 파일:
- 실제 제품키는 Git에 포함하지 않습니다.
- 제품키를 로컬 파일로 사용하는 정책이라면 빌드 머신에서만
  src/skhu_pc_management/infrastructure/license/local_product_keys.py를 준비합니다.
- local_product_keys.example.py를 local_product_keys.py로 복사한 뒤 실제 값을 입력합니다.
- 제품키 값은 화면, 로그, 문서에 출력하지 않습니다.

주의:
- 앱은 관리자 권한 실행이 필요할 수 있습니다.
- 기본 설정 적용, 네트워크 변경, 인증 준비, 작업표시줄 관련 기능은 실제 Windows 테스트 PC에서만 검증합니다.
- 작업표시줄 기능은 현재 리소스 검증과 dry-run 계획 확인이 기본입니다.
