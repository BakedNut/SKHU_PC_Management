from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplyResult:
    name: str
    success: bool
    message: str = ""


@dataclass(frozen=True)
class SettingStatus:
    name: str
    is_applied: bool
    current_value: str | None = None
    expected_value: str | None = None
