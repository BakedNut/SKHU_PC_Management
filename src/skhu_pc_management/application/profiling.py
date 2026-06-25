from __future__ import annotations

import os
import time


class EnvProfiler:
    def __init__(self, env_var: str) -> None:
        self._enabled = os.environ.get(env_var) == "1"

    def step(self, name: str) -> "_ProfileStep":
        return _ProfileStep(name, self._enabled)


class _ProfileStep:
    def __init__(self, name: str, enabled: bool) -> None:
        self._name = name
        self._enabled = enabled
        self._started_at = 0.0

    def __enter__(self) -> None:
        if self._enabled:
            self._started_at = time.perf_counter()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._enabled:
            elapsed_ms = (time.perf_counter() - self._started_at) * 1000
            print(f"{self._name}: {elapsed_ms:.1f} ms")
