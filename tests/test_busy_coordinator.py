from __future__ import annotations

import pytest

from skhu_pc_management.presentation.qt.busy_coordinator import BusyCoordinator


def test_busy_coordinator_begin_and_end_notify_listeners() -> None:
    coordinator = BusyCoordinator()
    events: list[tuple[bool, str]] = []
    coordinator.add_listener(lambda is_busy, message: events.append((is_busy, message)))

    coordinator.begin("작업 중")
    assert coordinator.is_busy is True
    assert coordinator.message == "작업 중"

    coordinator.end("완료")
    assert coordinator.is_busy is False
    assert coordinator.message == "완료"
    assert events == [(True, "작업 중"), (False, "완료")]


def test_busy_coordinator_try_begin_fails_while_busy() -> None:
    coordinator = BusyCoordinator()

    assert coordinator.try_begin("첫 작업") is True
    assert coordinator.try_begin("두 번째 작업") is False
    assert coordinator.message == "첫 작업"


def test_busy_coordinator_begin_raises_while_busy() -> None:
    coordinator = BusyCoordinator()
    coordinator.begin("작업 중")

    with pytest.raises(RuntimeError, match="다른 작업이 진행 중입니다."):
        coordinator.begin("중복 작업")


def test_busy_coordinator_guard_releases_busy_after_exception() -> None:
    coordinator = BusyCoordinator()

    with pytest.raises(ValueError):
        with coordinator.guard("작업 중") as acquired:
            assert acquired is True
            raise ValueError("failed")

    assert coordinator.is_busy is False
    assert coordinator.message == ""


def test_busy_coordinator_guard_yields_false_when_already_busy() -> None:
    coordinator = BusyCoordinator()
    coordinator.begin("선행 작업")

    with coordinator.guard("중복 작업") as acquired:
        assert acquired is False

    assert coordinator.is_busy is True
    assert coordinator.message == "선행 작업"
