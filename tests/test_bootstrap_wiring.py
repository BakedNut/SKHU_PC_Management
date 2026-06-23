from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from skhu_pc_management import bootstrap


def test_bootstrap_exposes_container_factories() -> None:
    guard = bootstrap.create_safety_guard(test_mode=True)

    assert guard.test_mode is True
    assert guard.allow_real_taskbar_apply is False
    assert bootstrap.InfrastructureContainer is not None
    assert bootstrap.UseCaseContainer is not None
    assert bootstrap.ViewModelContainer is not None


def test_bootstrap_reads_test_mode_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKHU_PC_MANAGEMENT_TEST_MODE", "1")

    assert bootstrap.is_test_mode_enabled() is True
    assert bootstrap.create_safety_guard().test_mode is True
    assert bootstrap.create_safety_guard().allow_real_taskbar_apply is False


def test_bootstrap_allows_real_taskbar_apply_in_normal_mode() -> None:
    guard = bootstrap.create_safety_guard(test_mode=False)

    assert guard.test_mode is False
    assert guard.allow_real_taskbar_apply is True
