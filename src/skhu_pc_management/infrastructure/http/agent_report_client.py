import logging
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

import requests

from skhu_pc_management.domain.agent.models import AgentReport, AgentReportResult
from skhu_pc_management.infrastructure.config.agent_config_loader import AgentConfig
from skhu_pc_management.infrastructure.config.worker_token_loader import load_worker_token
from skhu_pc_management.ports.agent_report_client import AgentReportClient


class HttpAgentReportClient(AgentReportClient):
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)

    def send_report(self, report: AgentReport) -> AgentReportResult:
        url = f"{self._config.api_base_url}/api/agent/pc-reports"
        payload = _to_payload(report)

        self._logger.info("Agent report request url: %s", url)
        self._logger.info("Agent report payload: %s", payload)

        response = requests.post(
            url,
            json=payload,
            headers=self._build_headers(),
            timeout=self._config.timeout_seconds,
        )

        if not response.ok:
            self._logger.warning(
                "Agent report request failed. status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(f"{response.status_code} Error: {response.text}")

        body = response.json()
        data = body.get("data", body)

        return AgentReportResult(
            reportId=int(data["reportId"]),
            matchedPcId=data.get("matchedPcId"),
            matchStatus=str(data["matchStatus"]),
            identityEventCreated=bool(data["identityEventCreated"]),
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "X-Agent-Api-Key": self._config.agent_api_key,
            "Content-Type": "application/json",
        }

        worker_token = load_worker_token(self._config)

        if worker_token is not None:
            headers["X-Worker-Token"] = worker_token

        return headers


def _to_payload(report: AgentReport) -> dict[str, Any]:
    payload = asdict(report)

    reported_at = payload.get("reportedAt")

    if isinstance(reported_at, datetime):
        payload["reportedAt"] = _format_reported_at(reported_at)

    payload["networkAdapters"] = _to_json_safe(payload.get("networkAdapters") or [])
    payload["disks"] = _to_json_safe(payload.get("disks") or [])
    payload["checkResults"] = _to_json_safe(payload.get("checkResults") or [])
    payload["installedSoftware"] = _to_json_safe(payload.get("installedSoftware") or [])

    return _to_json_safe(payload)


def _format_reported_at(value: datetime) -> str:
    return value.replace(microsecond=0, tzinfo=None).isoformat()


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return _format_reported_at(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_to_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}

    return value