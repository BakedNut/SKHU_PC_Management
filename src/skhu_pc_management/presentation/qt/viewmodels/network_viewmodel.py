from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NetworkViewModel:
    status_message: str = "Network configuration is not loaded."
