from __future__ import annotations

from pathlib import Path
from typing import Sequence

from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.infrastructure.license.null_product_key_provider import NullProductKeyProvider


class FakeProductKeyProvider:
    def __init__(self, windows_key: str | None = "test-windows-key", office_key: str | None = "test-office-key") -> None:
        self.windows_key = windows_key
        self.office_key = office_key
        self.windows_requests: list[str | None] = []
        self.office_requests: list[str | None] = []

    def get_windows_product_key(self, edition: str | None = None) -> str | None:
        self.windows_requests.append(edition)
        return self.windows_key

    def get_office_product_key(self, version: str | None = None) -> str | None:
        self.office_requests.append(version)
        return self.office_key


class FakeClipboard:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def set_text(self, text: str) -> None:
        self.texts.append(text)


class FakeProcessLauncher:
    def __init__(self) -> None:
        self.launches: list[tuple[Path, tuple[str, ...]]] = []

    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        self.launches.append((executable, tuple(args)))


def test_windows_activation_copies_key_and_launches_slui() -> None:
    provider = FakeProductKeyProvider(windows_key="test-windows-key")
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()

    result = ActivateWindows(provider, clipboard, launcher).execute("windows_11")

    assert result.success is True
    assert result.action == "windows_activation"
    assert result.copied_to_clipboard is True
    assert result.launched_process == "slui.exe"
    assert provider.windows_requests == ["windows_11"]
    assert clipboard.texts == ["test-windows-key"]
    assert launcher.launches == [(Path("slui.exe"), ())]


def test_office_activation_copies_key_and_launches_excel() -> None:
    provider = FakeProductKeyProvider(office_key="test-office-key")
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()
    excel_path = Path("EXCEL.EXE")

    result = ActivateOffice(provider, clipboard, launcher, excel_path=excel_path).execute("2024")

    assert result.success is True
    assert result.action == "office_activation"
    assert result.copied_to_clipboard is True
    assert result.launched_process == str(excel_path)
    assert provider.office_requests == ["2024"]
    assert clipboard.texts == ["test-office-key"]
    assert launcher.launches == [(excel_path, ())]


def test_windows_activation_returns_failure_when_key_is_missing() -> None:
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()

    result = ActivateWindows(FakeProductKeyProvider(windows_key=None), clipboard, launcher).execute()

    assert result.success is False
    assert "not configured" in result.message
    assert clipboard.texts == []
    assert launcher.launches == []


def test_office_activation_returns_failure_when_key_is_missing() -> None:
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()

    result = ActivateOffice(FakeProductKeyProvider(office_key=None), clipboard, launcher).execute()

    assert result.success is False
    assert "not configured" in result.message
    assert clipboard.texts == []
    assert launcher.launches == []


def test_null_product_key_provider_returns_no_keys() -> None:
    provider = NullProductKeyProvider()

    assert provider.get_windows_product_key() is None
    assert provider.get_office_product_key() is None
