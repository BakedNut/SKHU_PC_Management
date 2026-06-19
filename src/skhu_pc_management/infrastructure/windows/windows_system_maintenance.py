from __future__ import annotations

import ctypes
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.ports.command_runner import CommandRunner


SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004


@dataclass(frozen=True)
class WindowsSystemMaintenance:
    command_runner: CommandRunner

    def empty_recycle_bin(self) -> int:
        shell32 = ctypes.windll.shell32
        shell32.SHEmptyRecycleBinW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
        shell32.SHEmptyRecycleBinW.restype = ctypes.c_int
        return int(shell32.SHEmptyRecycleBinW(None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND))

    def delete_browser_history(self, browser_id: str) -> bool:
        browser_id = browser_id.lower()
        if browser_id == "chrome":
            self._kill_processes(("chrome.exe",))
            root = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
        elif browser_id == "edge":
            self._kill_processes(("msedge.exe", "msedgewebview2.exe"))
            root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"
        else:
            raise ValueError(f"Unsupported browser id: {browser_id}")

        time.sleep(2)
        if not root.exists():
            return True
        shutil.rmtree(root)
        return True

    def set_power_never(self) -> bool:
        for command in (
            ("powercfg", "-change", "-monitor-timeout-ac", "0"),
            ("powercfg", "-change", "-monitor-timeout-dc", "0"),
            ("powercfg", "-change", "-standby-timeout-ac", "0"),
            ("powercfg", "-change", "-standby-timeout-dc", "0"),
            ("powercfg", "-change", "-hibernate-timeout-ac", "0"),
            ("powercfg", "-change", "-hibernate-timeout-dc", "0"),
        ):
            self.command_runner.run(command)
        return True

    def set_auto_shutdown_at_23(self) -> bool:
        script = """
$taskName = '23시 자동 종료'
$action = New-ScheduledTaskAction -Execute 'shutdown.exe' -Argument '-s -t 300 -c "원치 않는 경우 바탕화면의 종료 취소를 실행해주세요"'
$trigger = New-ScheduledTaskTrigger -Daily -At '22:55'
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
""".strip()
        self.command_runner.run(("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script))
        return True

    def _kill_processes(self, image_names: tuple[str, ...]) -> None:
        for image_name in image_names:
            try:
                self.command_runner.run(("taskkill", "/F", "/IM", image_name, "/T"))
            except Exception:
                pass
