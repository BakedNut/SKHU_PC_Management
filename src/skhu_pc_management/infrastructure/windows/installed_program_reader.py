from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from skhu_pc_management.domain.checks.models import InstalledProgramInfo
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class WindowsInstalledProgramReader:
    registry: Registry

    def get_program(self, program_id: str) -> InstalledProgramInfo | None:
        paths = _PROGRAM_PATHS.get(program_id, ())
        registry_path = self._get_program_registry_path(program_id)
        if registry_path:
            paths = (registry_path, *paths)

        for raw_path in paths:
            path = Path(raw_path)
            if path.exists():
                return InstalledProgramInfo(
                    program_id=program_id,
                    name=_PROGRAM_NAMES.get(program_id, program_id),
                    version=_get_program_version(program_id, path),
                    path=str(path),
                )
        return None

    def get_installed_office_name(self) -> str | None:
        uninstall_roots = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        for root_path in uninstall_roots:
            try:
                subkeys = self.registry.list_subkeys("HKEY_LOCAL_MACHINE", root_path)
            except Exception:
                continue

            for subkey in subkeys:
                try:
                    display_name = self.registry.read_value(
                        "HKEY_LOCAL_MACHINE",
                        rf"{root_path}\{subkey}",
                        "DisplayName",
                    )
                except (FileNotFoundError, OSError):
                    continue
                if not isinstance(display_name, str):
                    continue
                if _is_office_display_name(display_name):
                    return display_name
        return None

    def _get_program_registry_path(self, program_id: str) -> str | None:
        if program_id == "potplayer":
            for key_path in (r"SOFTWARE\DAUM\PotPlayer64", r"SOFTWARE\DAUM\PotPlayer"):
                try:
                    value = self.registry.read_value("HKEY_LOCAL_MACHINE", key_path, "ProgramPath")
                except (FileNotFoundError, OSError):
                    continue
                if isinstance(value, str):
                    return value

        if program_id == "bandizip":
            for key_path in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Bandizip",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Bandizip",
            ):
                try:
                    value = self.registry.read_value("HKEY_LOCAL_MACHINE", key_path, "InstallLocation")
                except (FileNotFoundError, OSError):
                    continue
                if isinstance(value, str):
                    return str(Path(value) / "Bandizip.exe")
        return None


_PROGRAM_NAMES = {
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "potplayer": "PotPlayer",
    "bandizip": "Bandizip",
}

_PROGRAM_PATHS = {
    "chrome": (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ),
    "edge": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ),
    "potplayer": (
        r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
        r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe",
        r"C:\Program Files\DAUM\PotPlayer\PotPlayer64.exe",
        r"C:\Program Files\DAUM\PotPlayer\PotPlayer.exe",
        r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayer.exe",
    ),
    "bandizip": (
        r"C:\Program Files\Bandizip\Bandizip.exe",
        r"C:\Program Files (x86)\Bandizip\Bandizip.exe",
    ),
}


def _is_office_display_name(display_name: str) -> bool:
    text = display_name.lower()
    return (
        "microsoft office" in text
        and any(token in text for token in ("professional", "standard", "ltsc", "home and business"))
    )


def _get_file_version(path: Path) -> str | None:
    try:
        import win32api

        info = win32api.GetFileVersionInfo(str(path), "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return ".".join(str(part) for part in (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF))
    except Exception:
        return None


def _get_program_version(program_id: str, path: Path) -> str | None:
    if program_id == "potplayer":
        history_version = _get_potplayer_history_version(path)
        if history_version:
            return history_version
        file_version = _get_file_version(path)
        return _extract_potplayer_date_version(file_version)

    if program_id == "bandizip":
        file_version = _get_file_version(path)
        return _extract_bandizip_version(file_version)

    return _get_file_version(path)


def _get_potplayer_history_version(path: Path) -> str | None:
    history_path = path.parent / "History" / "Korean.txt"
    try:
        content = history_path.read_text(encoding="mbcs")
    except Exception:
        return None
    return _parse_potplayer_history_version(content)


def _parse_potplayer_history_version(content: str) -> str | None:
    match = re.search(r"\[(\d{6})\]", content)
    return match.group(1) if match else None


def _extract_potplayer_date_version(version: str | None) -> str | None:
    if not version:
        return None
    compact = version.replace(".", "").replace(",", "").replace(" ", "")
    match = re.search(r"(\d{6})", compact)
    return match.group(1) if match else None


def _extract_bandizip_version(version: str | None) -> str | None:
    if not version:
        return None
    match = re.search(r"\d+\.\d+", version)
    return match.group(0) if match else None
