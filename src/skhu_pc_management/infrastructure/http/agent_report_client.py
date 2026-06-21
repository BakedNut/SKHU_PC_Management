from dataclasses import asdict
from datetime import datetime
from typing import Any

import requests

from skhu_pc_management.domain.agent.models import AgentReport, AgentReportResult
from skhu_pc_management.infrastructure.config.agent_config_loader import AgentConfig
from skhu_pc_management.ports.agent_report_client import AgentReportClient


class HttpAgentReportClient(AgentReportClient):
    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def send_report(self, report: AgentReport) -> AgentReportResult:
        url = f"{self._config.api_base_url}/api/agent/pc-reports"

        response = requests.post(
            url,
            json=_to_payload(report),
            headers={
                "X-Agent-Api-Key": self._config.agent_api_key,
                "Content-Type": "application/json",
            },
            timeout=self._config.timeout_seconds,
        )
        response.raise_for_status()

        body = response.json()
        data = body.get("data", body)

        return AgentReportResult(
            reportId=int(data["reportId"]),
            matchedPcId=data.get("matchedPcId"),
            matchStatus=str(data["matchStatus"]),
            identityEventCreated=bool(data["identityEventCreated"]),
        )


def _to_payload(report: AgentReport) -> dict[str, Any]:
    payload = asdict(report)

    if isinstance(report.reportedAt, datetime):
        payload["reportedAt"] = report.reportedAt.isoformat()

    payload["networkAdapters"] = payload["networkAdapters"] or []
    payload["disks"] = payload["disks"] or []
    payload["checkResults"] = payload["checkResults"] or []
    payload["installedSoftware"] = payload["installedSoftware"] or []

    return payload