from __future__ import annotations

from typing import Protocol


class SystemMaintenance(Protocol):
    def empty_recycle_bin(self) -> int:
        """Empty recycle bin and return the native result code."""

    def delete_browser_history(self, browser_id: str) -> bool | str:
        """Reset the browser User Data root for the given browser."""

    def set_power_never(self) -> bool:
        """Set AC/DC monitor, standby, and hibernate timeouts to never."""

    def set_auto_shutdown_at_23(self) -> bool:
        """Register the classroom 23:00 auto-shutdown scheduled task."""
