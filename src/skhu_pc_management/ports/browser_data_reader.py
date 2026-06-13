from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import BrowserDataStatus


class BrowserDataReader(Protocol):
    def get_browser_data_status(self, browser_id: str) -> BrowserDataStatus:
        """Return browser data size/status without deleting anything."""
