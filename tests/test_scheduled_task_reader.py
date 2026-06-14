from __future__ import annotations

from collections.abc import Sequence

from skhu_pc_management.infrastructure.windows.windows_scheduled_task_reader import (
    WindowsScheduledTaskReader,
    parse_scheduled_task_json,
)


class FakeCommandRunner:
    def __init__(self, output: str = "", error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> str:
        self.commands.append(tuple(command))
        if self.error is not None:
            raise self.error
        return self.output


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


def test_windows_scheduled_task_reader_uses_command_runner_only() -> None:
    runner = FakeCommandRunner(
        """
        {
          "TaskName": "23시 자동 종료",
          "Actions": {"Execute": "shutdown.exe", "Arguments": "-s -t 300"},
          "Triggers": {"StartBoundary": "2026-06-13T22:55:00"}
        }
        """
    )

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is True
    assert runner.commands == [
        (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Get-ScheduledTask -TaskName '23시 자동 종료' | Select-Object TaskName, State, Actions, Triggers | ConvertTo-Json -Depth 6",
        )
    ]


def test_windows_scheduled_task_reader_returns_error_when_powershell_fails() -> None:
    runner = FakeCommandRunner(error=RuntimeError("ScheduledTasks failed"))

    task = WindowsScheduledTaskReader(runner).get_task("23시 자동 종료")

    assert task.exists is False
    assert task.error == "ScheduledTasks failed"
