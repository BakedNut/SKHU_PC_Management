from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplyResult:
    name: str
    success: bool
    message: str = ""
    setting_id: str = ""
    status: str = "applied"


@dataclass(frozen=True)
class ApplySettingsResult:
    results: list[ApplyResult]

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for result in self.results if result.status == "skipped")

    @property
    def is_success(self) -> bool:
        return self.failure_count == 0


@dataclass(frozen=True)
class SettingStatus:
    setting_id: str = ""
    label: str = ""
    expected_value: object | None = None
    actual_value: object | None = None
    is_configured: bool = False
    severity: str = "unknown"
    status_text: str = "Unknown"
    name: str = ""
    is_applied: bool = False
    current_value: str | None = None
    detail: str = ""
