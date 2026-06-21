from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AgentReport:
    pcName: str
    macAddress: str
    reportedAt: datetime
    username: str | None = None
    osVersion: str | None = None
    cpu: str | None = None
    ram: str | None = None
    gpu: str | None = None
    ipAddress: str | None = None
    networkAdapters: list[dict[str, Any]] | None = None
    disks: list[dict[str, Any]] | None = None
    checkResults: list[dict[str, Any]] | None = None
    installedSoftware: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class AgentReportResult:
    reportId: int
    matchedPcId: int | None
    matchStatus: str
    identityEventCreated: bool