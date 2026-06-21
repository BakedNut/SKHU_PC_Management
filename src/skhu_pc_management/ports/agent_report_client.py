from abc import ABC, abstractmethod

from skhu_pc_management.domain.agent.models import AgentReport, AgentReportResult


class AgentReportClient(ABC):
    @abstractmethod
    def send_report(self, report: AgentReport) -> AgentReportResult:
        raise NotImplementedError