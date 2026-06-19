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

    def delete_browser_history(self, browser_id: str) -> str:
        return self.reset_browser_user_data(browser_id)

    def reset_browser_user_data(self, browser_id: str) -> str:
        browser_id = browser_id.lower()
        browser_name = "Chrome" if browser_id == "chrome" else "Edge"
        if browser_id == "chrome":
            self._kill_processes(("chrome.exe",))
        elif browser_id == "edge":
            self._kill_processes(("msedge.exe", "msedgewebview2.exe"))
        else:
            raise ValueError(f"Unsupported browser id: {browser_id}")

        root = _browser_user_data_root(browser_id)
        time.sleep(2)
        if not root.exists():
            return f"{browser_name} 사용자 데이터 폴더가 없어 초기화할 항목이 없습니다."

        # Intentional policy: reset the whole browser User Data root, not only
        # History files. This can remove sessions, extensions, and settings.
        shutil.rmtree(root)
        return f"{browser_name} 사용자 데이터 초기화가 완료되었습니다. 방문 기록, 로그인 세션, 확장 프로그램 설정 등이 삭제될 수 있습니다."

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


def _browser_user_data_root(browser_id: str) -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    if browser_id == "chrome":
        return local_app_data / "Google" / "Chrome" / "User Data"
    if browser_id == "edge":
        return local_app_data / "Microsoft" / "Edge" / "User Data"
    raise ValueError(f"Unsupported browser id: {browser_id}")
