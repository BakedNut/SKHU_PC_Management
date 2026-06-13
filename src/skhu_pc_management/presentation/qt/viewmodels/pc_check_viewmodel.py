from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PcCheckViewModel:
    status_message: str = "PC checks have not run."
