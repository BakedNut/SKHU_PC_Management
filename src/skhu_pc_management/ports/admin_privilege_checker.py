from __future__ import annotations

from typing import Protocol


class AdminPrivilegeChecker(Protocol):
    def is_running_as_admin(self) -> bool:
        """Return whether the current process has administrator privileges."""
