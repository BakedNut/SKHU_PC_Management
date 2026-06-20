from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

from skhu_pc_management.application.use_cases.activate_office import ActivateOffice
from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.infrastructure.license import embedded_product_key_provider
from skhu_pc_management.infrastructure.license.embedded_product_key_provider import EmbeddedProductKeyProvider
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
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.launches: list[tuple[Path, tuple[str, ...]]] = []

    def launch(self, executable: Path, args: Sequence[str] = ()) -> None:
        if self.error is not None:
            raise self.error
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
    assert "test-windows-key" not in result.message


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
    assert "test-office-key" not in result.message


def test_windows_activation_uses_selected_windows_11_key_kind() -> None:
    provider = FakeProductKeyProvider(windows_key="win11-secret")
    result = ActivateWindows(provider, FakeClipboard(), FakeProcessLauncher()).execute("windows_11")

    assert result.success is True
    assert result.message == "Windows 11 제품키를 클립보드에 복사하고 인증 창을 실행했습니다."
    assert provider.windows_requests == ["windows_11"]


def test_windows_activation_uses_selected_windows_10_key_kind() -> None:
    provider = FakeProductKeyProvider(windows_key="win10-secret")
    result = ActivateWindows(provider, FakeClipboard(), FakeProcessLauncher()).execute("windows_10")

    assert result.success is True
    assert result.message == "Windows 10 제품키를 클립보드에 복사하고 인증 창을 실행했습니다."
    assert provider.windows_requests == ["windows_10"]


def test_office_activation_uses_selected_office_2024_key_kind() -> None:
    provider = FakeProductKeyProvider(office_key="office2024-secret")
    result = ActivateOffice(provider, FakeClipboard(), FakeProcessLauncher()).execute("2024")

    assert result.success is True
    assert result.message == "Office 2024 제품키를 클립보드에 복사하고 Excel을 실행했습니다."
    assert provider.office_requests == ["2024"]


def test_office_activation_uses_selected_office_2021_key_kind() -> None:
    provider = FakeProductKeyProvider(office_key="office2021-secret")
    result = ActivateOffice(provider, FakeClipboard(), FakeProcessLauncher()).execute("2021")

    assert result.success is True
    assert result.message == "Office 2021 제품키를 클립보드에 복사하고 Excel을 실행했습니다."
    assert provider.office_requests == ["2021"]


def test_office_activation_reports_missing_excel_in_korean() -> None:
    provider = FakeProductKeyProvider(office_key="office-secret")

    result = ActivateOffice(provider, FakeClipboard(), FakeProcessLauncher(FileNotFoundError("missing"))).execute("2024")

    assert result.success is False
    assert "Excel 실행 파일을 찾지 못했습니다." in result.message
    assert "제품키는 이미 클립보드에 복사되었을 수 있습니다." in result.message
    assert "office-secret" not in result.message


def test_windows_activation_warns_clipboard_may_contain_key_when_launch_fails() -> None:
    provider = FakeProductKeyProvider(windows_key="windows-secret")

    result = ActivateWindows(provider, FakeClipboard(), FakeProcessLauncher(RuntimeError("launch failed"))).execute("windows_11")

    assert result.success is False
    assert result.copied_to_clipboard is True
    assert "제품키는 이미 클립보드에 복사되었을 수 있습니다." in result.message
    assert "windows-secret" not in result.message


def test_office_activation_warns_clipboard_may_contain_key_when_launch_fails() -> None:
    provider = FakeProductKeyProvider(office_key="office-secret")

    result = ActivateOffice(provider, FakeClipboard(), FakeProcessLauncher(RuntimeError("launch failed"))).execute("2024")

    assert result.success is False
    assert result.copied_to_clipboard is True
    assert "제품키는 이미 클립보드에 복사되었을 수 있습니다." in result.message
    assert "office-secret" not in result.message


def test_windows_activation_returns_failure_when_key_is_missing() -> None:
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()

    result = ActivateWindows(FakeProductKeyProvider(windows_key=None), clipboard, launcher).execute()

    assert result.success is False
    assert "제품키가 설정되어 있지 않습니다" in result.message
    assert clipboard.texts == []
    assert launcher.launches == []


def test_office_activation_returns_failure_when_key_is_missing() -> None:
    clipboard = FakeClipboard()
    launcher = FakeProcessLauncher()

    result = ActivateOffice(FakeProductKeyProvider(office_key=None), clipboard, launcher).execute()

    assert result.success is False
    assert "제품키가 설정되어 있지 않습니다" in result.message
    assert clipboard.texts == []
    assert launcher.launches == []


def test_null_product_key_provider_returns_no_keys() -> None:
    provider = NullProductKeyProvider()

    assert provider.get_windows_product_key() is None
    assert provider.get_office_product_key() is None


def test_embedded_product_key_provider_loads_local_module(monkeypatch) -> None:
    def fake_import_module(module_name: str) -> SimpleNamespace:
        assert module_name == "skhu_pc_management.infrastructure.license.local_product_keys"
        return SimpleNamespace(WINDOWS_PRODUCT_KEY="test-windows-key", OFFICE_PRODUCT_KEY="test-office-key")

    monkeypatch.setattr(embedded_product_key_provider, "import_module", fake_import_module)
    provider = EmbeddedProductKeyProvider()

    assert provider.get_windows_product_key() == "test-windows-key"
    assert provider.get_office_product_key() == "test-office-key"


def test_embedded_product_key_provider_loads_version_specific_keys(monkeypatch) -> None:
    def fake_import_module(module_name: str) -> SimpleNamespace:
        return SimpleNamespace(
            WINDOWS_11_PRODUCT_KEY="win11-key",
            WINDOWS_10_PRODUCT_KEY="win10-key",
            OFFICE_2024_PRODUCT_KEY="office2024-key",
            OFFICE_2021_PRODUCT_KEY="office2021-key",
        )

    monkeypatch.setattr(embedded_product_key_provider, "import_module", fake_import_module)
    provider = EmbeddedProductKeyProvider()

    assert provider.get_windows_product_key("windows_11") == "win11-key"
    assert provider.get_windows_product_key("windows_10") == "win10-key"
    assert provider.get_office_product_key("2024") == "office2024-key"
    assert provider.get_office_product_key("2021") == "office2021-key"


def test_embedded_product_key_provider_falls_back_to_generic_keys(monkeypatch) -> None:
    def fake_import_module(module_name: str) -> SimpleNamespace:
        return SimpleNamespace(WINDOWS_PRODUCT_KEY="windows-fallback", OFFICE_PRODUCT_KEY="office-fallback")

    monkeypatch.setattr(embedded_product_key_provider, "import_module", fake_import_module)
    provider = EmbeddedProductKeyProvider()

    assert provider.get_windows_product_key("windows_11") == "windows-fallback"
    assert provider.get_office_product_key("2024") == "office-fallback"


def test_embedded_product_key_provider_reports_missing_local_file(monkeypatch) -> None:
    def fake_import_module(module_name: str) -> SimpleNamespace:
        raise ModuleNotFoundError(module_name)

    monkeypatch.setattr(embedded_product_key_provider, "import_module", fake_import_module)
    provider = EmbeddedProductKeyProvider()

    try:
        provider.get_windows_product_key()
    except RuntimeError as exc:
        assert "제품키 파일이 없습니다" in str(exc)
        assert "local_product_keys.example.py" in str(exc)
        assert "local_product_keys.py" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")
