from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PcCheckViewModel:
    run_pc_checks_use_case: Any
    status_message: str = "PC 점검을 실행하지 않았습니다."
    result_rows: list[tuple[str, str, str]] = field(default_factory=list)
    is_busy: bool = False

    def run_checks(self) -> None:
        self.is_busy = True
        self.status_message = "PC 점검 실행 중입니다..."
        try:
            results = self.run_pc_checks_use_case.execute()
            self.result_rows = [
                (result.label or result.name, result.status, result.message)
                for result in results
            ]
            self.status_message = f"PC 점검 완료: {len(results)}개 항목"
        except Exception as exc:
            self.result_rows = []
            self.status_message = f"PC 점검 실패: {exc}"
        finally:
            self.is_busy = False
