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
    SCHEDULED_TASK = "scheduled_task"
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
class ProgramVersionInfo:
    program_id: str
    display_name: str
    current_version: str | None
    latest_version: str | None
    is_installed: bool


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
    additional_profiles: tuple[str, ...] = ()
    skipped_inaccessible_count: int = 0

    @property
    def has_history(self) -> bool | None:
        if not self.path_exists:
            return False
        if self.additional_profiles:
            return True
        if self.size_bytes is None:
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
        parsed_values = tuple(_ac_timeout_to_seconds(value) for value in values)
        if any(value is None for value in parsed_values):
            return None
        return all(value == 0 for value in parsed_values)

    @property
    def detail_text(self) -> str | None:
        monitor = ac_timeout_display(self.monitor_timeout_ac)
        standby = ac_timeout_display(self.standby_timeout_ac)
        hibernate = ac_timeout_display(self.hibernate_timeout_ac)
        if None in (monitor, standby, hibernate):
            return None
        return f"화면 끄기: {monitor}, 절전: {standby}, 최대 절전: {hibernate}"


def ac_timeout_display(value: str | None) -> str | None:
    seconds = _ac_timeout_to_seconds(value)
    if seconds is None:
        return None
    if seconds == 0:
        return "안 함"
    return f"{seconds // 60}분"


def _ac_timeout_to_seconds(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text)
    except ValueError:
        return None


@dataclass(frozen=True)
class ScheduledTaskInfo:
    name: str
    exists: bool
    trigger_time: str | None = None
    executable: str | None = None
    arguments: str | None = None
    raw: object | None = None
    error: str | None = None
