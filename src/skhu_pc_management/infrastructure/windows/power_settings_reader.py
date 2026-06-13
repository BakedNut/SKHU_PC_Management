from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.checks.models import PowerSettingsStatus
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsPowerSettingsReader:
    command_runner: CommandRunner

    def read_status(self) -> PowerSettingsStatus:
        return PowerSettingsStatus(
            monitor_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_VIDEO", "VIDEOIDLE")),
            standby_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE")),
            hibernate_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "HIBERNATEIDLE")),
        )

    def _read_powercfg_value(self, command: tuple[str, ...]) -> str | None:
        try:
            output = self.command_runner.run(command)
        except Exception:
            return None

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if (
                line.lower().startswith("current ac power setting index:")
                or line.startswith("현재 AC 전원 설정 인덱스:")
                or line.startswith("현재 AC 전원 설정 색인:")
            ):
                return line.rsplit(":", 1)[-1].strip()
        return None
