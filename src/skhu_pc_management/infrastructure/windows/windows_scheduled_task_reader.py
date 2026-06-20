from __future__ import annotations

import json
import re
import base64
from dataclasses import dataclass
from typing import Any

from skhu_pc_management.domain.checks.models import ScheduledTaskInfo
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsScheduledTaskReader:
    command_runner: CommandRunner

    def get_task(self, name: str) -> ScheduledTaskInfo:
        escaped_name = _escape_powershell_single_quoted(name)
        script = f"""
$ErrorActionPreference = 'Stop'
Import-Module ScheduledTasks -ErrorAction Stop
$taskName = '{escaped_name}'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$action = $task.Actions | Select-Object -First 1
$trigger = $task.Triggers | Select-Object -First 1
[PSCustomObject]@{{
    TaskName = $task.TaskName
    State = [string]$task.State
    Execute = [string]$action.Execute
    Arguments = [string]$action.Arguments
    StartBoundary = [string]$trigger.StartBoundary
    Description = [string]$task.Description
}} | ConvertTo-Json -Depth 4
""".strip()
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        command = (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
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
    executable = _read_first_present(parsed, ("Execute", "execute"))
    arguments = _read_first_present(parsed, ("Arguments", "arguments"))
    start_boundary = _read_first_present(parsed, ("StartBoundary", "startBoundary"))

    actions = _as_list(_read_first_present(parsed, ("Actions", "actions")))
    triggers = _as_list(_read_first_present(parsed, ("Triggers", "triggers")))
    action = actions[0] if actions else {}
    trigger = triggers[0] if triggers else {}

    if executable is None and isinstance(action, dict):
        executable = _read_first_present(action, ("Execute", "execute", "Path", "path"))
    if arguments is None and isinstance(action, dict):
        arguments = _read_first_present(action, ("Arguments", "arguments"))
    if start_boundary is None and isinstance(trigger, dict):
        start_boundary = _read_first_present(trigger, ("StartBoundary", "startBoundary"))

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
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})", text)
    if match is None:
        return None

    return f"{int(match.group('hour')):02d}:{match.group('minute')}"
