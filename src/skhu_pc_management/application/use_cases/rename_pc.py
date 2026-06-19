from __future__ import annotations

from dataclasses import dataclass
import re

from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.ports.pc_renamer import PcRenamer


@dataclass(frozen=True)
class RenamePc:
    pc_renamer: PcRenamer | None = None
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, new_name: str) -> ApplyResult:
        normalized_name = new_name.strip()
        validation_error = _validate_pc_name(normalized_name)
        if validation_error:
            return ApplyResult(name="PC 이름 변경", success=False, status="failed", message=validation_error)

        blocked_message = self.safety_guard.blocked_message("rename_pc")
        if blocked_message is not None:
            return ApplyResult(name="PC 이름 변경", success=False, status="skipped", message=blocked_message)

        if self.pc_renamer is None:
            return ApplyResult(name="PC 이름 변경", success=False, status="failed", message="PC 이름 변경 기능이 구성되지 않았습니다.")

        try:
            self.pc_renamer.rename(normalized_name)
        except Exception as exc:
            return ApplyResult(name="PC 이름 변경", success=False, status="failed", message=str(exc))

        return ApplyResult(
            name="PC 이름 변경",
            success=True,
            status="applied",
            message="PC 이름 변경이 예약되었습니다. 적용하려면 재부팅이 필요합니다.",
        )


def _validate_pc_name(name: str) -> str | None:
    if not 1 <= len(name) <= 15:
        return "PC 이름은 1~15자여야 합니다."
    if name.startswith("-") or name.endswith("-"):
        return "PC 이름은 하이픈으로 시작하거나 끝날 수 없습니다."
    if name.isdigit():
        return "PC 이름은 숫자만으로 구성할 수 없습니다."
    if not re.fullmatch(r"[0-9A-Za-z가-힣-]+", name):
        return "PC 이름은 한글, 영문, 숫자, 하이픈만 사용할 수 있습니다."
    return None
