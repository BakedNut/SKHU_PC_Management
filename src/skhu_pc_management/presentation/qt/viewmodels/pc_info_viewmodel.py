from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PcInfoViewModel:
    status_message: str = "PC information is not loaded."
