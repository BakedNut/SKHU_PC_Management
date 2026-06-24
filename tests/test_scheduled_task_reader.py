from __future__ import annotations

import base64
from collections.abc import Sequence

from skhu_pc_management.infrastructure.windows.windows_scheduled_task_reader import (
    WindowsScheduledTaskReader,
    parse_schtasks_csv,
    parse_scheduled_task_json,
)


class FakeCommandRunner:
    def __init__(self, output: str | list[str] = "", error: Exception | None = None) -> None:
        self.outputs = [output] if isinstance(output, str) else list(output)
        self.error = error
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        if self.error is not None:
            raise self.error
        if not self.outputs:
            raise AssertionError("unexpected command")
        return self.outputs.pop(0)


def test_parse_scheduled_task_json_handles_single_action_and_trigger_objects() -> None:
    output = """
    {
      "TaskName": "23시 자동 종료",
      "Actions": {"Execute": "shutdown.exe", "Arguments": "-s -t 300"},
      "Triggers": {"StartBoundary": "2026-06-13T22:55:00"}
    }
    """

    task = parse_scheduled_task_json("23시 자동 종료", output)

    assert task.exists is True
    assert task.name == "23시 자동 종료"
    assert task.trigger_time == "22:55"
    assert task.executable == "shutdown.exe"
    assert task.arguments == "-s -t 300"


def test_parse_scheduled_task_json_handles_flat_powershell_object() -> None:
    output = """
    {
      "TaskName": "23시 자동 종료",
      "State": "Ready",
      "Execute": "shutdown.exe",
      "Arguments": "-s -t 300 -c \\"원치 않는 경우 바탕화면의 종료 취소를 실행해주세요\\"",
      "StartBoundary": "2026-06-13T22:55:00",
      "Description": "강의실 23시 자동 종료 정책"
    }
    """

    task = parse_scheduled_task_json("23시 자동 종료", output)

    assert task.exists is True
    assert task.trigger_time == "22:55"
    assert task.executable == "shutdown.exe"
    assert "-t 300" in (task.arguments or "")


def test_parse_scheduled_task_json_handles_action_and_trigger_arrays() -> None:
    output = """
    {
      "TaskName": "23시 자동 종료",
      "Actions": [{"Execute": "C:\\\\Windows\\\\System32\\\\shutdown.exe", "Arguments": "-s -t 300"}],
      "Triggers": [{"StartBoundary": "2026-06-13T22:55:00"}]
    }
    """

    task = parse_scheduled_task_json("23시 자동 종료", output)

    assert task.exists is True
    assert task.trigger_time == "22:55"
    assert task.executable == r"C:\Windows\System32\shutdown.exe"


def test_parse_scheduled_task_json_treats_empty_output_as_missing() -> None:
    task = parse_scheduled_task_json("23시 자동 종료", "")

    assert task.exists is False
    assert task.error is None


def test_parse_scheduled_task_json_handles_exists_false_object() -> None:
    task = parse_scheduled_task_json("23시 자동 종료", '{"Exists": false, "TaskName": "23시 자동 종료"}')

    assert task.exists is False
    assert task.error is None


def test_parse_schtasks_csv_reads_task_details() -> None:
    output = (
        '"TaskName","Task To Run","Start Time","Status"\n'
        '"\\\\23시 자동 종료","shutdown.exe -s -t 300","10:55:00 PM","Ready"\n'
    )

    task = parse_schtasks_csv("23시 자동 종료", output)

    assert task is not None
    assert task.exists is True
    assert task.name == "23시 자동 종료"
    assert task.trigger_time == "22:55"
    assert task.executable == "shutdown.exe"
    assert task.arguments == "-s -t 300"


def test_windows_scheduled_task_reader_uses_schtasks_fast_path_without_powershell() -> None:
    runner = FakeCommandRunner(
        '"TaskName","Task To Run","Start Time","Status"\n'
        '"\\\\23시 자동 종료","shutdown.exe -s -t 300","22:55:00","Ready"\n'
    )

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is True
    assert task.executable == "shutdown.exe"
    assert runner.commands == [("schtasks", "/Query", "/TN", "23시 자동 종료", "/FO", "CSV", "/V")]


def test_windows_scheduled_task_reader_falls_back_to_powershell_when_schtasks_is_incomplete() -> None:
    runner = FakeCommandRunner(
        [
            '"TaskName","Task To Run","Start Time","Status"\n"\\\\23시 자동 종료","N/A","","Ready"\n',
            """
        {
          "TaskName": "23시 자동 종료",
          "Actions": {"Execute": "shutdown.exe", "Arguments": "-s -t 300"},
          "Triggers": {"StartBoundary": "2026-06-13T22:55:00"}
        }
        """,
        ]
    )

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is True
    assert runner.commands[0] == ("schtasks", "/Query", "/TN", "23시 자동 종료", "/FO", "CSV", "/V")
    assert runner.commands[1][:4] == ("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass")
    assert runner.commands[1][4] == "-EncodedCommand"
    script = _decode_encoded_powershell(runner.commands[1])
    assert "$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue" in script
    assert "Exists = $false" in script
    assert "Exists = $true" in script
    assert "Execute = [string]$action.Execute" in script
    assert "Arguments = [string]$action.Arguments" in script
    assert "StartBoundary = [string]$trigger.StartBoundary" in script
    assert "ConvertTo-Json -Depth 4" in script


def test_windows_scheduled_task_reader_returns_missing_when_schtasks_reports_not_found() -> None:
    runner = FakeCommandRunner(error=RuntimeError("ERROR: The system cannot find the file specified."))

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is False
    assert task.error is None
    assert runner.commands == [("schtasks", "/Query", "/TN", "23시 자동 종료", "/FO", "CSV", "/V")]


def test_windows_scheduled_task_reader_returns_error_when_powershell_fails() -> None:
    runner = FakeCommandRunner(error=RuntimeError("ScheduledTasks failed"))

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is False
    assert task.error == "ScheduledTasks failed"


def _decode_encoded_powershell(command: tuple[str, ...]) -> str:
    encoded_index = command.index("-EncodedCommand") + 1
    return base64.b64decode(command[encoded_index]).decode("utf-16le")
