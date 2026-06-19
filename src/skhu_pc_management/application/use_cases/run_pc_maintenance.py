from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.ports.system_maintenance import SystemMaintenance


@dataclass(frozen=True)
class RunPcMaintenance:
    system_maintenance: SystemMaintenance
    safety_guard: SafetyGuard = SafetyGuard()

    def empty_recycle_bin(self) -> ApplyResult:
        blocked = self.safety_guard.blocked_message("empty_recycle_bin")
        if blocked is not None:
            return ApplyResult(name="휴지통 비우기", success=False, status="skipped", message=blocked)
        try:
            code = self.system_maintenance.empty_recycle_bin()
        except Exception as exc:
            return ApplyResult(name="휴지통 비우기", success=False, status="failed", message=str(exc))
        if code != 0:
            return ApplyResult(name="휴지통 비우기", success=False, status="failed", message=f"휴지통 비우기 실패 (코드: {code})")
        return ApplyResult(name="휴지통 비우기", success=True, status="applied", message="휴지통을 비웠습니다.")

    def delete_browser_history(self, browser_id: str) -> ApplyResult:
        label = "Chrome 기록 삭제" if browser_id == "chrome" else "Edge 기록 삭제"
        blocked = self.safety_guard.blocked_message("delete_browser_history")
        if blocked is not None:
            return ApplyResult(name=label, success=False, status="skipped", message=blocked)
        try:
            ok = self.system_maintenance.delete_browser_history(browser_id)
        except Exception as exc:
            return ApplyResult(name=label, success=False, status="failed", message=str(exc))
        if not ok:
            return ApplyResult(name=label, success=False, status="failed", message=f"{label}에 실패했습니다.")
        return ApplyResult(name=label, success=True, status="applied", message=f"{label}가 완료되었습니다.")

    def set_power_never(self) -> ApplyResult:
        blocked = self.safety_guard.blocked_message("set_power_never")
        if blocked is not None:
            return ApplyResult(name="전원 옵션 '안 함' 적용", success=False, status="skipped", message=blocked)
        try:
            self.system_maintenance.set_power_never()
        except Exception as exc:
            return ApplyResult(name="전원 옵션 '안 함' 적용", success=False, status="failed", message=str(exc))
        return ApplyResult(name="전원 옵션 '안 함' 적용", success=True, status="applied", message="전원 옵션이 '안 함'으로 설정되었습니다.")

    def set_auto_shutdown_at_23(self) -> ApplyResult:
        blocked = self.safety_guard.blocked_message("set_auto_shutdown_at_23")
        if blocked is not None:
            return ApplyResult(name="23시 자동종료 적용", success=False, status="skipped", message=blocked)
        try:
            self.system_maintenance.set_auto_shutdown_at_23()
        except Exception as exc:
            return ApplyResult(name="23시 자동종료 적용", success=False, status="failed", message=str(exc))
        return ApplyResult(
            name="23시 자동종료 적용",
            success=True,
            status="applied",
            message="23시 자동종료 작업이 등록되었습니다. (22:55 시작 + 300초 후 종료)",
        )
