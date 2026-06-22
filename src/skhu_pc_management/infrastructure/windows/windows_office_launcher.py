from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.domain.settings.definitions import HKCU, HKLM
from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.registry import Registry


_APP_PATHS_KEYS = (
    (HKLM, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe"),
    (HKCU, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe"),
    (HKLM, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\excel.exe"),
    (HKCU, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\excel.exe"),
)


@dataclass(frozen=True)
class WindowsOfficeLauncher:
    registry: Registry
    process_launcher: ProcessLauncher

    def launch_excel(self) -> str:
        executable = self.find_excel_executable()
        if executable is not None:
            self.process_launcher.launch(executable)
            return str(executable)

        fallback = Path("excel.exe")
        self.process_launcher.launch(fallback)
        return str(fallback)

    def find_excel_executable(self) -> Path | None:
        for candidate in _known_excel_paths():
            if candidate.is_file():
                return candidate

        for candidate in self._registry_app_path_candidates():
            if candidate.is_file():
                return candidate

        return None

    def _registry_app_path_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        for root, key_path in _APP_PATHS_KEYS:
            for value_name in ("", "Path"):
                try:
                    value = self.registry.read_value(root, key_path, value_name)
                except PermissionError:
                    raise
                except Exception:
                    continue

                candidate = _path_from_registry_value(value, value_name)
                if candidate is not None:
                    candidates.append(candidate)
        return candidates


def _known_excel_paths() -> tuple[Path, ...]:
    program_files = Path(os.environ.get("ProgramFiles") or r"C:\Program Files")
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)")
    return (
        program_files / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE",
        program_files_x86 / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE",
        program_files / "Microsoft Office" / "Office16" / "EXCEL.EXE",
        program_files_x86 / "Microsoft Office" / "Office16" / "EXCEL.EXE",
    )


def _path_from_registry_value(value: object | None, value_name: str) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None

    path = Path(value.strip().strip('"'))
    if value_name == "Path" and path.suffix.lower() != ".exe":
        return path / "EXCEL.EXE"
    return path
