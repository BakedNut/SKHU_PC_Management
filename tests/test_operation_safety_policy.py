from __future__ import annotations

from skhu_pc_management.application.safety import (
    REAL_TASKBAR_APPLY_DISABLED_MESSAGE,
    TEST_MODE_DISABLED_MESSAGE,
    SafetyGuard,
)
from skhu_pc_management.presentation.qt.maintenance_confirmations import MAINTENANCE_CONFIRMATIONS, maintenance_confirmation_for


def test_safety_guard_blocks_real_taskbar_apply_by_default() -> None:
    guard = SafetyGuard()

    assert guard.blocked_taskbar_apply_message(dry_run=False) == REAL_TASKBAR_APPLY_DISABLED_MESSAGE


def test_safety_guard_allows_taskbar_dry_run_by_default() -> None:
    guard = SafetyGuard()

    assert guard.blocked_taskbar_apply_message(dry_run=True) is None


def test_safety_guard_blocks_mutating_actions_in_test_mode() -> None:
    guard = SafetyGuard(test_mode=True)

    assert guard.blocked_message("apply_settings") == TEST_MODE_DISABLED_MESSAGE
    assert guard.blocked_taskbar_apply_message(dry_run=False) == TEST_MODE_DISABLED_MESSAGE
    assert guard.blocked_taskbar_apply_message(dry_run=True) is None


def test_safety_guard_allows_explicit_real_taskbar_apply_when_not_test_mode() -> None:
    guard = SafetyGuard(allow_real_taskbar_apply=True)

    assert guard.blocked_taskbar_apply_message(dry_run=False) is None


def test_maintenance_confirmation_messages_cover_all_dangerous_actions() -> None:
    expected_actions = {
        "empty_recycle_bin",
        "delete_chrome_history",
        "delete_edge_history",
        "set_power_never",
        "set_auto_shutdown_at_23",
    }

    assert set(MAINTENANCE_CONFIRMATIONS) == expected_actions


def test_browser_user_data_reset_confirmation_warns_about_full_user_data_deletion() -> None:
    chrome = maintenance_confirmation_for("delete_chrome_history")
    edge = maintenance_confirmation_for("delete_edge_history")

    assert chrome.title == "Chrome 사용자 데이터 초기화"
    assert "User Data" in chrome.message
    assert "로그인 세션" in chrome.message
    assert "확장 프로그램 설정" in chrome.message
    assert edge.title == "Edge 사용자 데이터 초기화"
    assert "User Data" in edge.message
    assert "로그인 세션" in edge.message
    assert "확장 프로그램 설정" in edge.message
