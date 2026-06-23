from __future__ import annotations

from typing import Protocol


class WindowsSettingsLauncher(Protocol):
    def open_pc_name_settings(self) -> None:
        """Open the Windows Settings page for changing the PC name."""
