from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.ports.process_launcher import ProcessLauncher


@dataclass(frozen=True)
class WindowsSettingsAppLauncher:
    process_launcher: ProcessLauncher

    def open_pc_name_settings(self) -> None:
        self.process_launcher.launch(Path("cmd"), ("/c", "start", "", "ms-settings:about"))
