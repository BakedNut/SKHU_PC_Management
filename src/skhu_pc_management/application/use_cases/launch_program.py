from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.ports.program_launcher import ProgramLauncher


PROGRAM_LABELS = {
    "chrome": "Chrome",
    "edge": "Edge",
    "potplayer": "팟플레이어",
    "bandizip": "반디집",
}


@dataclass(frozen=True)
class LaunchProgram:
    program_launcher: ProgramLauncher
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, program_id: str) -> ApplyResult:
        label = PROGRAM_LABELS.get(program_id, program_id)
        blocked_message = self.safety_guard.blocked_message("launch_program")
        if blocked_message is not None:
            return ApplyResult(name=label, success=False, status="skipped", message=blocked_message)
        try:
            launched = self.program_launcher.launch_program(program_id)
        except Exception as exc:
            return ApplyResult(name=label, success=False, status="failed", message=str(exc))
        if not launched:
            return ApplyResult(name=label, success=False, status="failed", message=f"{label} 실행 파일을 찾을 수 없습니다.")
        return ApplyResult(name=label, success=True, status="applied", message=f"{label}을 실행했습니다.")
