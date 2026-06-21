from __future__ import annotations

import os
import subprocess
from typing import Any, Sequence


def _hidden_subprocess_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


class SubprocessCommandRunner:
    def run(self, command: Sequence[str]) -> str:
        try:
            completed = subprocess.run(
                list(command),
                check=True,
                capture_output=True,
                text=True,
                shell=False,
                **_hidden_subprocess_kwargs(),
            )
        except subprocess.CalledProcessError as exc:
            stdout = (exc.stdout or "").strip()
            stderr = (exc.stderr or "").strip()
            detail = stderr or stdout or f"Command failed with exit code {exc.returncode}."
            raise RuntimeError(detail) from exc

        return (completed.stdout or "").strip()
