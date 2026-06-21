from __future__ import annotations

from dataclasses import dataclass

from skhu_pc_management.domain.checks.models import InstalledProgramInfo
from skhu_pc_management.ports.installed_program_reader import InstalledProgramReader


DEFAULT_PROGRAM_IDS = (
    "chrome",
    "edge",
    "potplayer",
    "bandizip",
)


@dataclass(frozen=True)
class ListInstalledPrograms:
    installed_program_reader: InstalledProgramReader
    program_ids: tuple[str, ...] = DEFAULT_PROGRAM_IDS

    def execute(self) -> list[InstalledProgramInfo]:
        programs: list[InstalledProgramInfo] = []

        for program_id in self.program_ids:
            try:
                program = self.installed_program_reader.get_program(program_id)
            except Exception:
                continue

            if program is not None:
                programs.append(program)

        office_name = self._get_installed_office_name()
        if office_name is not None:
            programs.append(
                InstalledProgramInfo(
                    program_id="office",
                    name=office_name,
                    version=None,
                    path=None,
                )
            )

        return programs

    def _get_installed_office_name(self) -> str | None:
        try:
            office_name = self.installed_program_reader.get_installed_office_name()
        except Exception:
            return None

        if office_name is None:
            return None

        text = office_name.strip()
        return text or None


ListInstalledProgramsUseCase = ListInstalledPrograms