from __future__ import annotations

from skhu_pc_management.application.use_cases.check_settings_status import CheckSettingsStatus
from skhu_pc_management.domain.settings.definitions import HKCU, HKLM


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], object] = {}
        self.reads: list[tuple[str, str, str]] = []

    def set_value(self, root: str, path: str, name: str, value: object) -> None:
        self.values[(root, path, name)] = value

    def read_value(self, root: str, path: str, name: str) -> object | None:
        self.reads.append((root, path, name))
        return self.values.get((root, path, name))

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        raise AssertionError("status checks must not write registry values")


def test_configured_when_actual_value_matches_expected_value() -> None:
    registry = FakeRegistry()
    registry.set_value(
        HKCU,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer",
        "ShowFrequent",
        0,
    )
    use_case = CheckSettingsStatus(registry)

    statuses = use_case.execute(["hide_frequent_folders"])

    assert len(statuses) == 1
    assert statuses[0].setting_id == "hide_frequent_folders"
    assert statuses[0].label == "자주 사용하는 폴더 숨김"
    assert statuses[0].expected_value == 0
    assert statuses[0].actual_value == 0
    assert statuses[0].is_configured is True
    assert statuses[0].severity == "ok"
    assert statuses[0].status_text == "configured"


def test_warning_when_actual_value_does_not_match_expected_value() -> None:
    registry = FakeRegistry()
    registry.set_value(
        HKCU,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "HideFileExt",
        1,
    )
    use_case = CheckSettingsStatus(registry)

    status = use_case.execute(["show_file_extensions"])[0]

    assert status.expected_value == 0
    assert status.actual_value == 1
    assert status.is_configured is False
    assert status.severity == "warning"
    assert status.status_text == "not_configured"


def test_unknown_when_registry_value_is_missing() -> None:
    use_case = CheckSettingsStatus(FakeRegistry())

    status = use_case.execute(["show_search_icon"])[0]

    assert status.expected_value == 1
    assert status.actual_value is None
    assert status.is_configured is False
    assert status.severity == "unknown"
    assert status.status_text == "missing"


def test_checks_only_selected_setting_ids() -> None:
    registry = FakeRegistry()
    registry.set_value(
        HKCU,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer",
        "ShowRecent",
        0,
    )
    use_case = CheckSettingsStatus(registry)

    statuses = use_case.execute(["hide_recent_files"])

    assert [status.setting_id for status in statuses] == ["hide_recent_files"]
    assert registry.reads == [
        (
            HKCU,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer",
            "ShowRecent",
        )
    ]


def test_hklm_status_is_read_through_registry_port() -> None:
    registry = FakeRegistry()
    registry.set_value(
        HKLM,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
        "HiberbootEnabled",
        0,
    )
    use_case = CheckSettingsStatus(registry)

    status = use_case.execute(["disable_fast_startup"])[0]

    assert status.is_configured is True
    assert registry.reads == [
        (
            HKLM,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
            "HiberbootEnabled",
        )
    ]


def test_unknown_setting_id_returns_error_status() -> None:
    registry = FakeRegistry()
    use_case = CheckSettingsStatus(registry)

    status = use_case.execute(["missing_setting_id"])[0]

    assert status.setting_id == "missing_setting_id"
    assert status.is_configured is False
    assert status.severity == "error"
    assert "Unknown setting id" in status.status_text
    assert registry.reads == []


def test_registry_read_failure_returns_unknown_status() -> None:
    class FailingRegistry(FakeRegistry):
        def read_value(self, root: str, path: str, name: str) -> object | None:
            raise RuntimeError("boom")

    use_case = CheckSettingsStatus(FailingRegistry())

    status = use_case.execute(["hide_frequent_folders"])[0]

    assert status.is_configured is False
    assert status.severity == "unknown"
    assert status.status_text == "Read failed: boom"
