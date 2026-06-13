from __future__ import annotations

from dataclasses import dataclass


class CheckStatus:
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class CheckCategory:
    PROGRAM = "program"
    OFFICE = "office"
    POWER = "power"
    RECYCLE_BIN = "recycle_bin"
    BROWSER_HISTORY = "browser_history"


@dataclass(frozen=True)
class CheckDefinition:
    check_id: str
    label: str
    category: str


@dataclass(frozen=True)
class CheckResult:
    check_id: str = ""
    label: str = ""
    category: str = ""
    status: str = CheckStatus.UNKNOWN
    message: str = ""
    detail: str | None = None
    raw_value: object | None = None
    name: str = ""
    passed: bool = False

    def __post_init__(self) -> None:
        if not self.name and self.label:
            object.__setattr__(self, "name", self.label)
        if self.status == CheckStatus.OK and not self.passed:
            object.__setattr__(self, "passed", True)


@dataclass(frozen=True)
class InstalledProgramInfo:
    program_id: str
    name: str
    version: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class RecycleBinStatus:
    item_count: int | None
    size_bytes: int | None = None

    @property
    def is_empty(self) -> bool | None:
        if self.item_count is None:
            return None
        return self.item_count == 0


@dataclass(frozen=True)
class BrowserDataStatus:
    browser_id: str
    size_bytes: int | None
    path_exists: bool

    @property
    def has_history(self) -> bool | None:
        if not self.path_exists or self.size_bytes is None:
            return None
        return self.size_bytes >= 5 * 1024 * 1024


@dataclass(frozen=True)
class PowerSettingsStatus:
    monitor_timeout_ac: str | None = None
    standby_timeout_ac: str | None = None
    hibernate_timeout_ac: str | None = None

    @property
    def is_never(self) -> bool | None:
        values = (self.monitor_timeout_ac, self.standby_timeout_ac, self.hibernate_timeout_ac)
        if any(value is None for value in values):
            return None
        return all(value == "0x00000000" for value in values)
