from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.checks.models import PowerSettingsStatus
from skhu_pc_management.infrastructure.profiling import EnvProfiler
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsPowerSettingsReader:
    command_runner: CommandRunner

    def read_status(self) -> PowerSettingsStatus:
        with EnvProfiler("SKHU_PC_MANAGEMENT_PROFILE_TABS").step("power_settings.read_status"):
            combined = self._read_combined_powercfg_status()
            if combined is not None:
                return combined

            return PowerSettingsStatus(
                monitor_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_VIDEO", "VIDEOIDLE")),
                standby_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE")),
                hibernate_timeout_ac=self._read_powercfg_value(("powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "HIBERNATEIDLE")),
            )

    def _read_combined_powercfg_status(self) -> PowerSettingsStatus | None:
        try:
            output = self.command_runner.run(("powercfg", "/q", "SCHEME_CURRENT"))
        except Exception:
            return None

        values = _parse_combined_powercfg_values(output)
        if not all(values.get(alias) for alias in ("VIDEOIDLE", "STANDBYIDLE", "HIBERNATEIDLE")):
            return None

        return PowerSettingsStatus(
            monitor_timeout_ac=values["VIDEOIDLE"],
            standby_timeout_ac=values["STANDBYIDLE"],
            hibernate_timeout_ac=values["HIBERNATEIDLE"],
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


def _parse_combined_powercfg_values(output: str) -> dict[str, str | None]:
    values: dict[str, str | None] = {
        "VIDEOIDLE": None,
        "STANDBYIDLE": None,
        "HIBERNATEIDLE": None,
    }
    current_alias: str | None = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        upper = line.upper()
        matched_alias = next((alias for alias in values if alias in upper), None)
        if matched_alias is not None:
            current_alias = matched_alias
            continue
        if current_alias is None:
            continue
        if (
            line.lower().startswith("current ac power setting index:")
            or line.startswith("현재 AC 전원 설정 인덱스:")
            or line.startswith("현재 AC 전원 설정 색인:")
        ):
            values[current_alias] = line.rsplit(":", 1)[-1].strip()
            current_alias = None
    return values
