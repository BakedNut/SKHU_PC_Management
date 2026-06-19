from __future__ import annotations

from dataclasses import dataclass


TEST_MODE_DISABLED_MESSAGE = "테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다."
REAL_TASKBAR_APPLY_DISABLED_MESSAGE = "작업표시줄 실제 적용은 기본적으로 비활성화되어 있습니다. 리소스 검증/dry-run만 수행하세요."


@dataclass(frozen=True)
class SafetyGuard:
    test_mode: bool = False
    allow_real_taskbar_apply: bool = False

    def blocked_message(self, action: str) -> str | None:
        if not self.test_mode:
            return None
        return TEST_MODE_DISABLED_MESSAGE

    def blocked_taskbar_apply_message(self, dry_run: bool) -> str | None:
        if dry_run:
            return None
        if self.test_mode:
            return TEST_MODE_DISABLED_MESSAGE
        if not self.allow_real_taskbar_apply:
            return REAL_TASKBAR_APPLY_DISABLED_MESSAGE
        return None
