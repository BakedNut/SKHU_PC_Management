from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from skhu_pc_management.domain.checks.models import ScheduledTaskInfo
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsScheduledTaskReader:
    command_runner: CommandRunner

    def get_task(self, name: str) -> ScheduledTaskInfo:
        command = (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"Get-ScheduledTask -TaskName '{_escape_powershell_single_quoted(name)}' "
            "| Select-Object TaskName, State, Actions, Triggers | ConvertTo-Json -Depth 6",
        )
        try:
            output = self.command_runner.run(command)
        except Exception as exc:
            return ScheduledTaskInfo(name=name, exists=False, error=str(exc))

        return parse_scheduled_task_json(name, output)


def parse_scheduled_task_json(name: str, output: str) -> ScheduledTaskInfo:
    if not output.strip():
        return ScheduledTaskInfo(name=name, exists=False)

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        return ScheduledTaskInfo(name=name, exists=False, error=f"ScheduledTasks JSON parse failed: {exc}")

    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else None

    if not isinstance(parsed, dict):
        return ScheduledTaskInfo(name=name, exists=False, raw=parsed)

    task_name = _read_first_present(parsed, ("TaskName", "taskName")) or name
    actions = _as_list(_read_first_present(parsed, ("Actions", "actions")))
    triggers = _as_list(_read_first_present(parsed, ("Triggers", "triggers")))
    action = actions[0] if actions else {}
    trigger = triggers[0] if triggers else {}

    executable = _read_first_present(action, ("Execute", "execute", "Path", "path")) if isinstance(action, dict) else None
    arguments = _read_first_present(action, ("Arguments", "arguments")) if isinstance(action, dict) else None
    start_boundary = (
        _read_first_present(trigger, ("StartBoundary", "startBoundary"))
        if isinstance(trigger, dict)
        else None
    )

    return ScheduledTaskInfo(
        name=str(task_name),
        exists=True,
        trigger_time=_parse_time(start_boundary),
        executable=None if executable is None else str(executable),
        arguments=None if arguments is None else str(arguments),
        raw=parsed,
    )


def _escape_powershell_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _read_first_present(source: object, names: tuple[str, ...]) -> Any:
    if not isinstance(source, dict):
        return None
    for name in names:
        if name in source:
            return source[name]
    return None


def _parse_time(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})", text)
    if match is None:
        return None

    return f"{int(match.group('hour')):02d}:{match.group('minute')}"
