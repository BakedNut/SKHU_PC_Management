from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.domain.settings.definitions import HKCU, HKLM, REG_DWORD, REG_STRING
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class WindowsSystemSettingsOperator:
    registry: Registry
    command_runner: CommandRunner

    def set_default_wallpaper(self) -> None:
        wallpaper = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Web" / "Wallpaper" / "Windows" / "img0.jpg"
        self.registry.write_value(
            HKCU,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers",
            "BackgroundType",
            0,
            REG_DWORD,
        )
        self.registry.write_value(HKCU, r"Control Panel\Desktop", "Wallpaper", str(wallpaper), REG_STRING)
        self.registry.write_value(
            HKCU,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
            "{2CC5CA98-6485-489A-920E-B3E88A6CCCE3}",
            1,
            REG_DWORD,
        )
        self.command_runner.run(("RUNDLL32.EXE", "user32.dll,UpdatePerUserSystemParameters"))

    def delete_edge_shortcuts(self) -> None:
        for desktop in _desktop_paths():
            shortcut = desktop / "Microsoft Edge.lnk"
            try:
                if shortcut.exists():
                    shortcut.unlink()
            except OSError:
                pass
        self.registry.write_value(
            HKLM,
            r"SOFTWARE\Policies\Microsoft\EdgeUpdate",
            "CreateDesktopShortcutDefault",
            0,
            REG_DWORD,
        )

    def disable_password_expiration_for_all_users(self) -> None:
        self.command_runner.run(("net", "accounts", "/maxpwage:unlimited"))
        script = "Get-LocalUser | Where-Object {$_.Enabled -eq $true} | Set-LocalUser -PasswordNeverExpires $true"
        self.command_runner.run(("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script))


def _desktop_paths() -> tuple[Path, ...]:
    public = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"
    user_profile = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    return public, user_profile
