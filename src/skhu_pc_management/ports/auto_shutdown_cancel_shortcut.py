from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME = "23시 자동종료 취소.lnk"
AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE = "23시 자동종료 취소.lnk"


@dataclass(frozen=True)
class AutoShutdownCancelShortcutStatus:
    source_path: Path
    desktop_path: Path
    source_exists: bool
    desktop_exists: bool
    matches: bool
    error: str | None = None


class AutoShutdownCancelShortcut(Protocol):
    def install(self) -> Path:
        """Copy the cancel shortcut resource to the current user's desktop."""

    def check(self) -> AutoShutdownCancelShortcutStatus:
        """Read-only check for the desktop cancel shortcut."""
