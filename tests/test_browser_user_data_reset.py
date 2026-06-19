from __future__ import annotations

from collections.abc import Sequence

import pytest

from skhu_pc_management.application.use_cases.run_pc_maintenance import RunPcMaintenance
from skhu_pc_management.infrastructure.windows import windows_system_maintenance as maintenance_module
from skhu_pc_management.infrastructure.windows.windows_system_maintenance import WindowsSystemMaintenance


class FakeCommandRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return ""


def test_chrome_user_data_reset_deletes_entire_user_data_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(maintenance_module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    user_data = tmp_path / "Google" / "Chrome" / "User Data"
    (user_data / "Default" / "Cache").mkdir(parents=True)
    (user_data / "Profile 1").mkdir()
    (user_data / "Default" / "History").write_text("history", encoding="utf-8")
    (user_data / "Profile 1" / "Preferences").write_text("prefs", encoding="utf-8")

    result = WindowsSystemMaintenance(FakeCommandRunner()).delete_browser_history("chrome")

    assert not user_data.exists()
    assert "Chrome 사용자 데이터 초기화가 완료" in result
    assert "로그인 세션" in result
    assert "확장 프로그램 설정" in result


def test_edge_user_data_reset_deletes_entire_user_data_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(maintenance_module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    user_data = tmp_path / "Microsoft" / "Edge" / "User Data"
    (user_data / "Default").mkdir(parents=True)
    (user_data / "Default" / "History").write_text("history", encoding="utf-8")

    result = WindowsSystemMaintenance(FakeCommandRunner()).delete_browser_history("edge")

    assert not user_data.exists()
    assert "Edge 사용자 데이터 초기화가 완료" in result


def test_browser_user_data_reset_missing_root_is_success_noop(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(maintenance_module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    result = WindowsSystemMaintenance(FakeCommandRunner()).delete_browser_history("chrome")

    assert result == "Chrome 사용자 데이터 폴더가 없어 초기화할 항목이 없습니다."


def test_browser_user_data_reset_delete_failure_is_returned_by_use_case(tmp_path, monkeypatch) -> None:
    class FailingMaintenance:
        def delete_browser_history(self, browser_id: str) -> bool:
            raise PermissionError("access denied")

    result = RunPcMaintenance(FailingMaintenance()).delete_browser_history("chrome")

    assert result.success is False
    assert result.status == "failed"
    assert "access denied" in result.message


def test_browser_user_data_reset_use_case_uses_clear_warning_message() -> None:
    class SuccessfulMaintenance:
        def delete_browser_history(self, browser_id: str) -> bool:
            return True

    result = RunPcMaintenance(SuccessfulMaintenance()).delete_browser_history("edge")

    assert result.success is True
    assert result.name == "Edge 사용자 데이터 초기화"
    assert "방문 기록" in result.message
    assert "로그인 세션" in result.message
    assert "확장 프로그램 설정" in result.message


def test_browser_user_data_reset_rejects_unknown_browser(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(maintenance_module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    with pytest.raises(ValueError):
        WindowsSystemMaintenance(FakeCommandRunner()).delete_browser_history("firefox")
