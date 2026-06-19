from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.application.safety import SafetyGuard
from skhu_pc_management.domain.settings.models import ApplyResult
from skhu_pc_management.ports.system_settings_operator import SystemSettingsOperator


@dataclass(frozen=True)
class SystemSettingsActions:
    operator: SystemSettingsOperator
    safety_guard: SafetyGuard = SafetyGuard()

    def execute(self, setting_id: str, name: str) -> ApplyResult:
        blocked = self.safety_guard.blocked_message(setting_id)
        if blocked is not None:
            return ApplyResult(setting_id=setting_id, name=name, success=False, status="skipped", message=blocked)
        try:
            if setting_id == "set_default_wallpaper":
                self.operator.set_default_wallpaper()
            elif setting_id == "delete_edge_shortcut":
                self.operator.delete_edge_shortcuts()
            elif setting_id == "disable_password_expiration":
                self.operator.disable_password_expiration_for_all_users()
            else:
                return ApplyResult(setting_id=setting_id, name=name, success=False, status="failed", message=f"Unknown action setting id: {setting_id}")
        except Exception as exc:
            return ApplyResult(setting_id=setting_id, name=name, success=False, status="failed", message=str(exc))
        return ApplyResult(setting_id=setting_id, name=name, success=True, status="applied", message="Applied.")
