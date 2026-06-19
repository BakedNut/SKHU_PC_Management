from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsPcRenamer:
    command_runner: CommandRunner

    def rename(self, new_name: str) -> bool:
        self.command_runner.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Rename-Computer -NewName '{_escape_single_quote(new_name)}' -Force",
            )
        )
        return True


def _escape_single_quote(value: str) -> str:
    return value.replace("'", "''")
