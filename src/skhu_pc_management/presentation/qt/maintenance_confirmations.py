from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceConfirmation:
    title: str
    message: str


MAINTENANCE_CONFIRMATIONS: dict[str, MaintenanceConfirmation] = {
    "empty_recycle_bin": MaintenanceConfirmation(
        title="휴지통 비우기",
        message="휴지통의 항목을 삭제합니다. 계속하시겠습니까?",
    ),
    "delete_chrome_history": MaintenanceConfirmation(
        title="Chrome 사용자 데이터 초기화",
        message="Chrome의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?",
    ),
    "delete_edge_history": MaintenanceConfirmation(
        title="Edge 사용자 데이터 초기화",
        message="Edge의 User Data 폴더를 삭제합니다. 방문 기록뿐 아니라 로그인 세션, 확장 프로그램 설정, 브라우저 설정 등이 삭제될 수 있습니다. 계속하시겠습니까?",
    ),
    "set_power_never": MaintenanceConfirmation(
        title="전원 옵션 적용",
        message="전원 절전/화면 꺼짐 옵션을 '안 함'으로 변경합니다. 계속하시겠습니까?",
    ),
    "set_auto_shutdown_at_23": MaintenanceConfirmation(
        title="23시 자동종료 적용",
        message="매일 22:55에 300초 후 종료 예약 작업을 등록합니다. 계속하시겠습니까?",
    ),
}


def maintenance_confirmation_for(action: str) -> MaintenanceConfirmation:
    return MAINTENANCE_CONFIRMATIONS[action]
