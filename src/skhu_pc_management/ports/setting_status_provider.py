from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.settings.models import SettingStatus


class SettingStatusProvider(Protocol):
    def check(self, setting_id: str) -> SettingStatus:
        """Read current status for a setting that is not fully registry-backed."""
