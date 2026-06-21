from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from skhu_pc_management.infrastructure.logging.agent_logger import create_agent_logger


@dataclass
class AgentReportViewModel:
    load_pc_info_use_case: Any
    list_network_adapters_use_case: Any
    run_pc_checks_use_case: Any
    list_installed_programs_use_case: Any
    build_agent_report_use_case: Any
    send_agent_report_use_case: Any | None

    status_message: str = "서버 전송 대기 중입니다."
    last_result_message: str = "-"
    last_sent_at: str = "-"
    last_report_id: str = "-"
    last_match_status: str = "-"
    is_busy: bool = False
    logger: Any = None

    max_retry_count: int = 3
    retry_delay_seconds: int = 5

    def send_report(self) -> None:
        if self.logger is None:
            self.logger = create_agent_logger()

        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return

        if self.send_agent_report_use_case is None:
            self.status_message = "config.json이 없어 서버 전송을 사용할 수 없습니다."
            self.last_result_message = (
                "config.example.json을 config.json으로 복사하고 "
                "Agent API Key를 입력하세요."
            )
            self.logger.warning("Agent report skipped: config.json is missing")
            return

        self.is_busy = True
        self.status_message = "PC 정보를 수집하고 서버로 전송하는 중입니다."

        try:
            report = self._build_report()
            result = self._send_with_retry(report)

            self.status_message = "서버 전송이 완료되었습니다."
            self.last_sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_report_id = str(result.reportId)
            self.last_match_status = result.matchStatus
            self.last_result_message = (
                f"reportId={result.reportId}, "
                f"matchedPcId={result.matchedPcId}, "
                f"matchStatus={result.matchStatus}, "
                f"identityEventCreated={result.identityEventCreated}"
            )
            self.logger.info("Agent report sent successfully: %s", self.last_result_message)
        except Exception as exc:
            self.status_message = "서버 전송에 실패했습니다."
            self.last_result_message = str(exc)
            self.logger.exception("Agent report send failed after retries")
        finally:
            self.is_busy = False

    def _build_report(self) -> Any:
        pc_info = self.load_pc_info_use_case.execute()

        network_adapters = self._safe_execute_list(
            self.list_network_adapters_use_case,
            "network adapters",
        )
        check_results = self._safe_execute_list(
            self.run_pc_checks_use_case,
            "pc checks",
        )
        installed_programs = self._safe_execute_list(
            self.list_installed_programs_use_case,
            "installed programs",
        )

        return self.build_agent_report_use_case.execute(
            pc_info=pc_info,
            network_adapters=network_adapters,
            check_results=check_results,
            installed_programs=installed_programs,
        )

    def _send_with_retry(self, report: Any) -> Any:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retry_count + 1):
            try:
                self.logger.info(
                    "Sending agent report attempt %s/%s",
                    attempt,
                    self.max_retry_count,
                )
                return self.send_agent_report_use_case.execute(report)
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "Agent report attempt %s/%s failed: %s",
                    attempt,
                    self.max_retry_count,
                    exc,
                )

                if attempt < self.max_retry_count:
                    time.sleep(self.retry_delay_seconds)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Agent report send failed for unknown reason.")

    def _safe_execute_list(
        self,
        use_case: Any,
        label: str,
    ) -> list[Any]:
        try:
            result = use_case.execute()
        except Exception:
            if self.logger is None:
                self.logger = create_agent_logger()
            self.logger.exception("Optional collection failed: %s", label)
            return []

        if result is None:
            return []

        if isinstance(result, list):
            return result

        if isinstance(result, tuple):
            return list(result)

        return []