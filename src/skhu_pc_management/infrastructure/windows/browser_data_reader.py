from __future__ import annotations

import os
from pathlib import Path

from skhu_pc_management.domain.checks.models import BrowserDataStatus


_BROWSER_HISTORY_THRESHOLD_BYTES = 5 * 1024 * 1024
_STOP_AT_BYTES = _BROWSER_HISTORY_THRESHOLD_BYTES + 1


class WindowsBrowserDataReader:
    def __init__(self, local_app_data_path: Path | None = None) -> None:
        self._local_app_data_path = local_app_data_path

    def get_browser_data_status(self, browser_id: str) -> BrowserDataStatus:
        user_data_root = self._browser_user_data_root(browser_id)
        if user_data_root is None or not user_data_root.exists():
            return BrowserDataStatus(browser_id=browser_id, size_bytes=0, path_exists=False)

        profiles = _browser_profiles(user_data_root)
        total_size = 0
        skipped_count = 0
        for profile in profiles:
            size, skipped = _browser_data_size(profile, _STOP_AT_BYTES - total_size)
            total_size += size
            skipped_count += skipped
            if total_size >= _STOP_AT_BYTES:
                break

        return BrowserDataStatus(
            browser_id=browser_id,
            size_bytes=total_size,
            path_exists=True,
            additional_profiles=tuple(
                profile.name for profile in profiles
                if profile.name.lower().startswith("profile ") or profile.name.lower() == "guest profile"
            ),
            skipped_inaccessible_count=skipped_count,
        )

    def _browser_user_data_root(self, browser_id: str) -> Path | None:
        local_app_data = self._local_app_data_path or _default_local_app_data_path()
        if browser_id == "chrome":
            return local_app_data / "Google" / "Chrome" / "User Data"
        if browser_id == "edge":
            return local_app_data / "Microsoft" / "Edge" / "User Data"
        return None


def _default_local_app_data_path() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    return Path(value) if value else Path.home() / "AppData" / "Local"


def _browser_profiles(user_data_root: Path) -> list[Path]:
    profiles: list[Path] = []
    default_profile = user_data_root / "Default"
    if default_profile.exists() and default_profile.is_dir():
        profiles.append(default_profile)

    try:
        children = list(user_data_root.iterdir())
    except OSError:
        return profiles

    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name.lower().startswith("profile ") or name.lower() == "guest profile":
            profiles.append(child)
    return profiles


def _browser_data_size(root: Path, remaining_budget: int) -> tuple[int, int]:
    total = 0
    skipped_count = 0
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
        if total >= remaining_budget:
            return total, skipped_count
        path = root / relative
        try:
            if path.exists() and path.is_file():
                total += path.stat().st_size
        except OSError:
            skipped_count += 1

    for relative in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
        if total >= remaining_budget:
            return total, skipped_count
        path = root / relative
        try:
            if path.exists() and path.is_dir():
                size, skipped = _directory_size(path, remaining_budget - total, max_depth=2)
                total += size
                skipped_count += skipped
        except OSError:
            skipped_count += 1
    return total, skipped_count


def _directory_size(root: Path, remaining_budget: int, max_depth: int) -> tuple[int, int]:
    total = 0
    skipped_count = 0
    queue: list[tuple[Path, int]] = [(root, 0)]

    while queue and total < remaining_budget:
        current, depth = queue.pop(0)
        try:
            children = list(current.iterdir())
        except OSError:
            skipped_count += 1
            continue

        for child in children:
            if total >= remaining_budget:
                break
            try:
                if child.is_file():
                    total += child.stat().st_size
                elif child.is_dir() and depth < max_depth:
                    queue.append((child, depth + 1))
            except OSError:
                skipped_count += 1
                continue
    return total, skipped_count
