from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.ports.windows_settings_launcher import WindowsSettingsLauncher


@dataclass(frozen=True)
class OpenPcNameSettings:
    settings_launcher: WindowsSettingsLauncher
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self) -> ApplyResult:
        blocked_message = self.safety_guard.blocked_message("rename_pc")
        if blocked_message is not None:
            return ApplyResult(name="PC 이름 변경", success=False, status="skipped", message=blocked_message)

        try:
            self.settings_launcher.open_pc_name_settings()
        except Exception as exc:
            return ApplyResult(
                name="PC 이름 변경",
                success=False,
                status="failed",
                message=f"Windows 설정을 열 수 없습니다: {exc}",
            )

        return ApplyResult(
            name="PC 이름 변경",
            success=True,
            status="opened",
            message="Windows 설정에서 PC 이름 변경 화면을 열었습니다.",
        )
