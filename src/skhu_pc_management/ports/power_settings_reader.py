from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import PowerSettingsStatus


class PowerSettingsReader(Protocol):
    def read_status(self) -> PowerSettingsStatus:
        """Read current power settings."""
