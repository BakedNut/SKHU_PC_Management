from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.agent.models import AgentReport, AgentReportResult
from skhu_pc_management.ports.agent_report_client import AgentReportClient


@dataclass(frozen=True)
class SendAgentReport:
    agent_report_client: AgentReportClient

    def execute(self, report: AgentReport) -> AgentReportResult:
        return self.agent_report_client.send_report(report)


SendAgentReportUseCase = SendAgentReport