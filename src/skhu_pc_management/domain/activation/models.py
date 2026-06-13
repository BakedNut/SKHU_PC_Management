from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivationResult:
    success: bool
    action: str
    message: str
    launched_process: str | None = None
    copied_to_clipboard: bool = False
    error: str | None = None
