from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SettingsViewModel:
    status_message: str = "Settings are not loaded."
