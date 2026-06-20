from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass(frozen=True)
class WindowsLatestVersionProvider:
    timeout_seconds: float = 3.0

    def get_latest_version(self, program_id: str) -> str | None:
        try:
            if program_id == "chrome":
                return parse_latest_chrome_version(_read_url("https://chromiumdash.appspot.com/fetch_releases?channel=Stable&platform=Windows", self.timeout_seconds))
            if program_id == "edge":
                return parse_latest_edge_version(_read_url("https://edgeupdates.microsoft.com/api/products", self.timeout_seconds))
            if program_id == "potplayer":
                return parse_latest_potplayer_version(_read_url("https://t1.daumcdn.net/potplayer/PotPlayer/v4/Update2/UpdateEng.html", self.timeout_seconds))
            if program_id == "bandizip":
                return parse_latest_bandizip_version(_read_url("https://www.bandisoft.com/bandizip/history/", self.timeout_seconds))
        except Exception:
            return None
        return None


def _read_url(url: str, timeout_seconds: float) -> str:
    with urlopen(url, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_latest_chrome_version(payload: str) -> str | None:
    try:
        releases = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(releases, list) or not releases:
        return None
    version = releases[0].get("version") if isinstance(releases[0], dict) else None
    return version if isinstance(version, str) and version.strip() else None


def parse_latest_edge_version(payload: str) -> str | None:
    try:
        products = json.loads(payload)
    except json.JSONDecodeError:
        products = None

    if isinstance(products, list):
        for product in products:
            if not isinstance(product, dict) or product.get("Product") != "Stable":
                continue
            releases = product.get("Releases")
            if isinstance(releases, list):
                for release in releases:
                    version = release.get("ProductVersion") if isinstance(release, dict) else None
                    if isinstance(version, str) and version.strip():
                        return version

    stable_index = payload.find('"Stable"')
    if stable_index < 0:
        return None
    version_match = re.search(r'"ProductVersion"\s*:\s*"([^"]+)"', payload[stable_index:])
    return version_match.group(1) if version_match else None


def parse_latest_potplayer_version(payload: str) -> str | None:
    match = re.search(r"\[(\d{6})\]", payload)
    return match.group(1) if match else None


def parse_latest_bandizip_version(payload: str) -> str | None:
    lower_payload = payload.lower()
    history_index = lower_payload.find("bandizip version history")
    search_area = payload[history_index:] if history_index >= 0 else payload

    for marker in ("modifications", "version"):
        marker_index = search_area.lower().find(marker)
        if marker_index >= 0:
            search_area = search_area[marker_index:]
            break

    patterns = (
        r"(?im)^\s*v(\d+\.\d+(?:\.\d+)*)\s*$",
        r"(?i)<[^>]*>\s*v(\d+\.\d+(?:\.\d+)*)\s*</[^>]+>",
    )
    for pattern in patterns:
        match = re.search(pattern, search_area)
        if match:
            return _major_minor_version(match.group(1))
    return None


def _major_minor_version(version: str) -> str:
    match = re.match(r"(\d+\.\d+)", version.strip())
    return match.group(1) if match else version.strip()
