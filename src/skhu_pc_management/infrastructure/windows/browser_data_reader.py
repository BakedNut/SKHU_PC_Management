from __future__ import annotations

from pathlib import Path

from skhu_pc_management.domain.checks.models import BrowserDataStatus


class WindowsBrowserDataReader:
    def get_browser_data_status(self, browser_id: str) -> BrowserDataStatus:
        root = _browser_default_profile(browser_id)
        if root is None or not root.exists():
            return BrowserDataStatus(browser_id=browser_id, size_bytes=None, path_exists=False)

        return BrowserDataStatus(
            browser_id=browser_id,
            size_bytes=_browser_data_size(root),
            path_exists=True,
        )


def _browser_default_profile(browser_id: str) -> Path | None:
    local_app_data = Path.home() / "AppData" / "Local"
    if browser_id == "chrome":
        return local_app_data / "Google" / "Chrome" / "User Data" / "Default"
    if browser_id == "edge":
        return local_app_data / "Microsoft" / "Edge" / "User Data" / "Default"
    return None


def _browser_data_size(root: Path) -> int:
    total = 0
    files_to_check = (
        "History",
        "History-journal",
        "Cache",
        "Cookies",
        "Cookies-journal",
        "Visited Links",
        "Web Data",
        "Web Data-journal",
        "Login Data",
        "Login Data-journal",
        "Top Sites",
        "Shortcuts",
        "Last Session",
        "Last Tabs",
        "Current Session",
        "Current Tabs",
        "Network Action Predictor",
    )
    for relative in files_to_check:
        path = root / relative
        if path.exists() and path.is_file():
            total += path.stat().st_size

    for relative in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
        path = root / relative
        if path.exists() and path.is_dir():
            total += _directory_size(path)
    return total


def _directory_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total
