from __future__ import annotations

import threading

from skhu_pc_management.application.use_cases.check_settings_status import CheckSettingsStatus
from skhu_pc_management.domain.settings.definitions import HKCU, HKLM, SettingDefinition
from skhu_pc_management.domain.settings.models import SettingStatus


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
    assert status.status_text == "read_failed"
    assert "레지스트리 값을 읽을 수 없습니다" in status.detail


def test_provider_is_used_for_non_registry_setting() -> None:
    class FakeProvider:
        def check(self, setting_id: str) -> SettingStatus:
            return SettingStatus(
                setting_id=setting_id,
                label="작업표시줄 아이콘 설정",
                is_configured=True,
                severity="ok",
                status_text="configured",
                detail="provider detail",
            )

    use_case = CheckSettingsStatus(FakeRegistry(), setting_status_providers={"set_taskbar_icons": FakeProvider()})

    status = use_case.execute(["set_taskbar_icons"])[0]

    assert status.is_configured is True
    assert status.detail == "provider detail"


def test_non_registry_setting_without_provider_returns_korean_missing_status() -> None:
    use_case = CheckSettingsStatus(FakeRegistry())

    status = use_case.execute(["set_taskbar_icons"])[0]

    assert status.status_text == "status_provider_missing"
    assert status.detail == "상태 확인 구현 필요"
    assert "No registry-backed" not in status.detail


def test_execute_returns_empty_list_for_empty_setting_ids() -> None:
    use_case = CheckSettingsStatus(FakeRegistry())

    assert use_case.execute([]) == []


def test_execute_preserves_input_order_when_checks_finish_out_of_order() -> None:
    class FakeProvider:
        def __init__(self, label: str) -> None:
            self.label = label

        def check(self, setting_id: str) -> SettingStatus:
            return SettingStatus(
                setting_id=setting_id,
                label=self.label,
                is_configured=True,
                severity="ok",
                status_text="configured",
            )

    definitions = {
        "first": SettingDefinition("first", "First"),
        "second": SettingDefinition("second", "Second"),
        "third": SettingDefinition("third", "Third"),
    }
    use_case = CheckSettingsStatus(
        FakeRegistry(),
        setting_status_providers={
            "first": FakeProvider("First"),
            "second": FakeProvider("Second"),
            "third": FakeProvider("Third"),
        },
        definitions_by_id=definitions,
    )

    statuses = use_case.execute(["third", "first", "second"])

    assert [status.setting_id for status in statuses] == ["third", "first", "second"]
    assert [status.label for status in statuses] == ["Third", "First", "Second"]


def test_provider_failure_is_isolated_to_that_setting() -> None:
    class PassingProvider:
        def check(self, setting_id: str) -> SettingStatus:
            return SettingStatus(
                setting_id=setting_id,
                label="정상 항목",
                is_configured=True,
                severity="ok",
                status_text="configured",
            )

    class FailingProvider:
        def check(self, setting_id: str) -> SettingStatus:
            raise RuntimeError("provider boom")

    definitions = {
        "passing": SettingDefinition("passing", "정상 항목"),
        "failing": SettingDefinition("failing", "실패 항목"),
    }
    use_case = CheckSettingsStatus(
        FakeRegistry(),
        setting_status_providers={"passing": PassingProvider(), "failing": FailingProvider()},
        definitions_by_id=definitions,
    )

    statuses = use_case.execute(["passing", "failing"])

    assert statuses[0].setting_id == "passing"
    assert statuses[0].status_text == "configured"
    assert statuses[1].setting_id == "failing"
    assert statuses[1].severity == "unknown"
    assert statuses[1].status_text == "read_failed"
    assert "provider boom" in statuses[1].detail


def test_execute_runs_setting_providers_in_parallel() -> None:
    barrier = threading.Barrier(2)

    class BarrierProvider:
        def check(self, setting_id: str) -> SettingStatus:
            barrier.wait(timeout=3)
            return SettingStatus(
                setting_id=setting_id,
                label=setting_id,
                is_configured=True,
                severity="ok",
                status_text="configured",
            )

    definitions = {
        "first": SettingDefinition("first", "First"),
        "second": SettingDefinition("second", "Second"),
    }
    provider = BarrierProvider()
    use_case = CheckSettingsStatus(
        FakeRegistry(),
        setting_status_providers={"first": provider, "second": provider},
        definitions_by_id=definitions,
    )

    statuses = use_case.execute(["first", "second"])

    assert [status.status_text for status in statuses] == ["configured", "configured"]
