from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.ports.process_launcher import ProcessLauncher
from skhu_pc_management.ports.registry import Registry


@dataclass(frozen=True)
class WindowsProgramLauncher:
    registry: Registry
    process_launcher: ProcessLauncher

    def launch_program(self, program_id: str) -> bool:
        executable = self._find_executable(program_id)
        if executable is None:
            return False
        self.process_launcher.launch(executable)
        return True

    def _find_executable(self, program_id: str) -> Path | None:
        candidates = {
            "chrome": (
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ),
            "edge": (
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            ),
            "potplayer": (
                self._potplayer_from_registry("SOFTWARE\\DAUM\\PotPlayer64"),
                self._potplayer_from_registry("SOFTWARE\\DAUM\\PotPlayer"),
                Path(r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe"),
                Path(r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe"),
            ),
            "bandizip": (
                self._bandizip_from_uninstall(),
                Path(r"C:\Program Files\Bandizip\Bandizip.exe"),
                Path(r"C:\Program Files (x86)\Bandizip\Bandizip.exe"),
            ),
        }.get(program_id, ())

        for candidate in candidates:
            if candidate is not None and candidate.exists():
                return candidate
        return None

    def _potplayer_from_registry(self, key_path: str) -> Path | None:
        install_path = self.registry.read_value("HKEY_CURRENT_USER", key_path, "ProgramFolder")
        if install_path is None:
            install_path = self.registry.read_value("HKEY_LOCAL_MACHINE", key_path, "ProgramFolder")
        if not install_path:
            return None
        base = Path(str(install_path))
        return base / ("PotPlayerMini64.exe" if "64" in key_path else "PotPlayerMini.exe")

    def _bandizip_from_uninstall(self) -> Path | None:
        uninstall_root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        for root in ("HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER"):
            try:
                subkeys = self.registry.list_subkeys(root, uninstall_root)
            except Exception:
                continue
            for subkey in subkeys:
                path = f"{uninstall_root}\\{subkey}"
                name = self.registry.read_value(root, path, "DisplayName")
                if name and "bandizip" in str(name).lower():
                    install_location = self.registry.read_value(root, path, "InstallLocation")
                    if install_location:
                        return Path(str(install_location)) / "Bandizip.exe"
        return None
