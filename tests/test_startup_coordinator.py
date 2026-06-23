from __future__ import annotations

from skhu_pc_management.presentation.qt.startup_coordinator import StartupCoordinator


class FakeAdminPrivilegeChecker:
    def __init__(self, is_admin: bool) -> None:
        self.is_admin = is_admin
        self.call_count = 0

    def is_running_as_admin(self) -> bool:
        self.call_count += 1
        return self.is_admin


class FakePcInfoViewModel:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.refresh_count = 0

    def refresh(self) -> None:
        self.refresh_count += 1
        if self.should_fail:
            raise RuntimeError("pc info failed")


class FakeSettingsViewModel:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.check_requests: list[list[str]] = []

    def all_setting_ids(self) -> list[str]:
        return ["setting_a", "setting_b"]

    def check_status(self, setting_ids: list[str]) -> None:
        self.check_requests.append(setting_ids)
        if self.should_fail:
            raise RuntimeError("settings failed")


class FakePcCheckViewModel:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.run_count = 0

    def run_checks(self) -> None:
        self.run_count += 1
        if self.should_fail:
            raise RuntimeError("checks failed")


def _create_coordinator(
    is_admin: bool = True,
    pc_info: FakePcInfoViewModel | None = None,
    settings: FakeSettingsViewModel | None = None,
    pc_checks: FakePcCheckViewModel | None = None,
) -> StartupCoordinator:
    return StartupCoordinator(
        admin_privilege_checker=FakeAdminPrivilegeChecker(is_admin),
        pc_info_view_model=pc_info or FakePcInfoViewModel(),
        settings_view_model=settings or FakeSettingsViewModel(),
        pc_check_view_model=pc_checks or FakePcCheckViewModel(),
    )


def test_startup_coordinator_reports_admin_status() -> None:
    coordinator = _create_coordinator(is_admin=False)

    result = coordinator.initialize()

    assert result.is_admin is False
    assert all(step.success for step in result.step_results)


def test_startup_coordinator_loads_only_pc_info_at_startup() -> None:
    pc_info = FakePcInfoViewModel()
    settings = FakeSettingsViewModel()
    pc_checks = FakePcCheckViewModel()
    coordinator = _create_coordinator(pc_info=pc_info, settings=settings, pc_checks=pc_checks)

    result = coordinator.initialize()

    assert result.is_admin is True
    assert pc_info.refresh_count == 1
    assert settings.check_requests == []
    assert pc_checks.run_count == 0
    assert [step.name for step in result.step_results] == ["pc_info"]


def test_startup_coordinator_continues_when_one_step_fails() -> None:
    pc_info = FakePcInfoViewModel(should_fail=True)
    settings = FakeSettingsViewModel()
    pc_checks = FakePcCheckViewModel()
    coordinator = _create_coordinator(pc_info=pc_info, settings=settings, pc_checks=pc_checks)

    result = coordinator.initialize()

    assert result.has_failures is True
    assert result.step_results[0].success is False
    assert "pc info failed" in result.step_results[0].message
    assert settings.check_requests == []
    assert pc_checks.run_count == 0


def test_startup_coordinator_prevents_duplicate_initialization() -> None:
    pc_info = FakePcInfoViewModel()
    settings = FakeSettingsViewModel()
    pc_checks = FakePcCheckViewModel()
    coordinator = _create_coordinator(pc_info=pc_info, settings=settings, pc_checks=pc_checks)

    first = coordinator.initialize()
    second = coordinator.initialize()

    assert first.step_results[0].name == "pc_info"
    assert second.step_results == [second.step_results[0]]
    assert second.step_results[0].message == "이미 초기화되었습니다."
    assert pc_info.refresh_count == 1
    assert settings.check_requests == []
    assert pc_checks.run_count == 0


def test_startup_coordinator_reports_when_initialization_is_already_running() -> None:
    coordinator = _create_coordinator()
    coordinator.is_busy = True

    result = coordinator.initialize()

    assert result.has_failures is True
    assert result.step_results[0].message == "초기화가 이미 진행 중입니다."
