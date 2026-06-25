from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os

from skhu_pc_management.ports.process_launcher import ProcessLauncher


_PC_NAME_SETTINGS_URI = "ms-settings:about"


@dataclass(frozen=True)
class WindowsSettingsAppLauncher:
    process_launcher: ProcessLauncher

    def open_pc_name_settings(self) -> None:
        _open_settings_uri(_PC_NAME_SETTINGS_URI)


def _open_settings_uri(uri: str) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows 설정 URI는 Windows에서만 지원됩니다.")

    result = ctypes.windll.shell32.ShellExecuteW(None, "open", uri, None, None, 1)
    if int(result) <= 32:
        raise RuntimeError(f"Windows 설정 URI를 열 수 없습니다: {uri}")
