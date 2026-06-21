from __future__ import annotations

from typing import Protocol

from skhu_pc_management.domain.checks.models import InstalledProgramInfo


class InstalledProgramReader(Protocol):
    def get_program(self, program_id: str) -> InstalledProgramInfo | None:
        """Return local program installation information."""

    def get_installed_office_name(self) -> str | None:
        """Return installed Office display name, if present."""

    def list_installed_programs(self) -> list[InstalledProgramInfo]:
        """Return installed programs from Windows Uninstall registry."""