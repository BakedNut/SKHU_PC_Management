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
        if program_id == "potplayer":
            return self._get_potplayer_program()

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
                    version=self._get_program_version(program_id, path),
                    path=str(path),
                )
        return None

    def _get_potplayer_program(self) -> InstalledProgramInfo | None:
        paths = _PROGRAM_PATHS.get("potplayer", ())
        registry_path = self._get_program_registry_path("potplayer")
        if registry_path:
            paths = (registry_path, *paths)

        for raw_path in paths:
            exe_path = _resolve_potplayer_exe_path(raw_path)
            if exe_path is None:
                continue
            return InstalledProgramInfo(
                program_id="potplayer",
                name=_PROGRAM_NAMES["potplayer"],
                version=self._get_program_version("potplayer", exe_path),
                path=str(exe_path),
            )

        registry_version = _get_potplayer_registry_version(self.registry)
        if registry_version:
            return InstalledProgramInfo(
                program_id="potplayer",
                name=_PROGRAM_NAMES["potplayer"],
                version=registry_version,
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

    def _get_program_version(self, program_id: str, path: Path) -> str | None:
        if program_id == "potplayer":
            if not path.is_file():
                return _get_potplayer_registry_version(self.registry)
            history_version = _get_potplayer_history_version(path)
            if history_version:
                return history_version
            file_version = _get_file_version(path)
            file_date_version = _extract_potplayer_date_version(file_version)
            if file_date_version:
                return file_date_version
            return _get_potplayer_registry_version(self.registry)

        if program_id == "bandizip":
            file_version = _get_file_version(path)
            return _extract_bandizip_version(file_version)

        return _get_file_version(path)

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

_POTPLAYER_EXE_NAMES = (
    "PotPlayerMini64.exe",
    "PotPlayerMini.exe",
    "PotPlayer64.exe",
    "PotPlayer.exe",
)


def _resolve_potplayer_exe_path(raw_path: str | Path) -> Path | None:
    path = Path(raw_path)
    if path.is_file():
        return path
    if path.is_dir():
        for exe_name in _POTPLAYER_EXE_NAMES:
            candidate = path / exe_name
            if candidate.is_file():
                return candidate
    return None


def _is_office_display_name(display_name: str) -> bool:
    text = display_name.lower()
    if "microsoft 365" in text or "office 365" in text:
        return True
    if "microsoft office" not in text:
        return False
    return any(
        token in text
        for token in (
            "professional",
            "standard",
            "ltsc",
            "home and business",
            "365",
            "2021",
            "2024",
        )
    )


def _get_file_version(path: Path) -> str | None:
    try:
        import win32api

        product_version = _get_file_string_info(win32api, path, "ProductVersion")
        if product_version:
            return product_version
        file_version = _get_file_string_info(win32api, path, "FileVersion")
        if file_version:
            return file_version

        info = win32api.GetFileVersionInfo(str(path), "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return ".".join(str(part) for part in (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF))
    except Exception:
        return None


def _get_file_string_info(win32api: object, path: Path, field_name: str) -> str | None:
    try:
        translations = win32api.GetFileVersionInfo(str(path), r"\VarFileInfo\Translation")
    except Exception:
        return None

    for language, codepage in translations:
        try:
            value = win32api.GetFileVersionInfo(
                str(path),
                rf"\StringFileInfo\{language:04x}{codepage:04x}\{field_name}",
            )
        except Exception:
            continue
        if isinstance(value, str):
            cleaned = _clean_version_text(value)
            if cleaned:
                return cleaned
    return None


def _get_potplayer_history_version(path: Path) -> str | None:
    history_path = path.parent / "History" / "Korean.txt"
    try:
        content = history_path.read_bytes()
    except Exception:
        return None
    return _parse_potplayer_history_version(content)


def _parse_potplayer_history_version(content: str | bytes) -> str | None:
    if isinstance(content, bytes):
        match = re.search(rb"\[(\d{6})\]", content)
        if not match:
            return None
        candidate = match.group(1).decode("ascii")
        return candidate if _is_valid_potplayer_date_version(candidate) else None

    match = re.search(r"\[(\d{6})\]", content)
    if not match:
        return None
    return match.group(1) if _is_valid_potplayer_date_version(match.group(1)) else None


def _extract_potplayer_date_version(version: str | None) -> str | None:
    if _is_invalid_potplayer_version(version):
        return None

    text = version.strip()
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
    if match and _is_valid_potplayer_date_version(match.group(1)):
        return match.group(1)

    compact = re.sub(r"[.,\s]", "", text)
    for match in re.finditer(r"(?=(\d{6}))", compact):
        candidate = match.group(1)
        if _is_valid_potplayer_date_version(candidate):
            return candidate
    return None


def _is_invalid_potplayer_version(version: str | None) -> bool:
    if not version:
        return True
    text = version.strip()
    if not text:
        return True
    digits = re.sub(r"\D", "", text)
    return not digits or all(digit == "0" for digit in digits)


def _is_valid_potplayer_date_version(candidate: str) -> bool:
    if re.fullmatch(r"\d{6}", candidate) is None:
        return False
    if all(digit == "0" for digit in candidate):
        return False
    month = int(candidate[2:4])
    day = int(candidate[4:6])
    return 1 <= month <= 12 and 1 <= day <= 31


def _extract_bandizip_version(version: str | None) -> str | None:
    if not version:
        return None
    match = re.search(r"\d+\.\d+", version)
    return match.group(0) if match else None


def _get_potplayer_registry_version(registry: Registry) -> str | None:
    for key_path in (r"SOFTWARE\DAUM\PotPlayer64", r"SOFTWARE\DAUM\PotPlayer"):
        for value_name in ("Version", "DisplayVersion"):
            value = _read_registry_string(registry, "HKEY_LOCAL_MACHINE", key_path, value_name)
            version = _extract_potplayer_date_version(value)
            if version:
                return version

    uninstall_roots = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    for root_path in uninstall_roots:
        try:
            subkeys = registry.list_subkeys("HKEY_LOCAL_MACHINE", root_path)
        except Exception:
            continue
        for subkey in subkeys:
            key_path = rf"{root_path}\{subkey}"
            display_name = _read_registry_string(registry, "HKEY_LOCAL_MACHINE", key_path, "DisplayName")
            if display_name and "potplayer" in display_name.lower():
                display_version = _read_registry_string(registry, "HKEY_LOCAL_MACHINE", key_path, "DisplayVersion")
                version = _extract_potplayer_date_version(display_version)
                if version:
                    return version
    return None


def _read_registry_string(registry: Registry, root: str, path: str, name: str) -> str | None:
    try:
        value = registry.read_value(root, path, name)
    except (FileNotFoundError, OSError):
        return None
    return _clean_version_text(value) if isinstance(value, str) else None


def _clean_version_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
