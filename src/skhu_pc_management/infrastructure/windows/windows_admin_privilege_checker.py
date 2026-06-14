from __future__ import annotations

import ctypes


class WindowsAdminPrivilegeChecker:
    def is_running_as_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
