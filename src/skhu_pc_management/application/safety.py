from __future__ import annotations

from dataclasses import dataclass


TEST_MODE_DISABLED_MESSAGE = "테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다."


@dataclass(frozen=True)
class SafetyGuard:
    test_mode: bool = False

    def blocked_message(self, action: str) -> str | None:
        if not self.test_mode:
            return None
        return TEST_MODE_DISABLED_MESSAGE
