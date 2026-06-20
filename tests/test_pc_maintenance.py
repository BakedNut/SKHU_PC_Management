from __future__ import annotations

import base64
from collections.abc import Sequence

import pytest

from skhu_pc_management.infrastructure.windows.windows_system_maintenance import WindowsSystemMaintenance


class FakeCommandRunner:
    def __init__(self, output: str = "__OK__") -> None:
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        return self.output


def test_set_auto_shutdown_at_23_uses_csharp_style_scheduled_task_script() -> None:
    runner = FakeCommandRunner("__OK__")

    assert WindowsSystemMaintenance(runner).set_auto_shutdown_at_23() is True

    script = _decode_encoded_powershell(runner.commands[0])
    assert "Import-Module ScheduledTasks" in script
    assert "$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name" in script
    assert "-LogonType Interactive" in script
    assert "New-ScheduledTaskSettingsSet" in script
    assert "-Description '강의실 23시 자동 종료 정책'" in script
    assert "Get-ScheduledTask -TaskName $taskName" in script
    assert "__OK__" in script
    assert "__ERROR__" in script
    assert "-UserId 'SYSTEM'" not in script


def test_set_auto_shutdown_at_23_raises_clear_error_when_marker_is_error() -> None:
    runner = FakeCommandRunner("__ERROR__등록 실패")

    with pytest.raises(RuntimeError, match="등록 실패"):
        WindowsSystemMaintenance(runner).set_auto_shutdown_at_23()


def test_set_auto_shutdown_at_23_raises_when_output_is_empty() -> None:
    runner = FakeCommandRunner("")

    with pytest.raises(RuntimeError, match="등록 결과를 확인할 수 없습니다"):
        WindowsSystemMaintenance(runner).set_auto_shutdown_at_23()


def _decode_encoded_powershell(command: tuple[str, ...]) -> str:
    encoded_index = command.index("-EncodedCommand") + 1
    return base64.b64decode(command[encoded_index]).decode("utf-16le")
