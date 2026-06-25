from __future__ import annotations

import json
import re
import base64
import csv
import io
import shlex
from dataclasses import dataclass
from typing import Any

from skhu_pc_management.domain.checks.models import ScheduledTaskInfo
from skhu_pc_management.infrastructure.profiling import EnvProfiler
from skhu_pc_management.ports.command_runner import CommandRunner


@dataclass(frozen=True)
class WindowsScheduledTaskReader:
    command_runner: CommandRunner

    def get_task(self, name: str) -> ScheduledTaskInfo:
        with EnvProfiler("SKHU_PC_MANAGEMENT_PROFILE_TABS").step("scheduled_task.get_task"):
            task = self._get_task_with_schtasks(name)
            if task is not None:
                return task
            return self._get_task_with_powershell(name)

    def _get_task_with_schtasks(self, name: str) -> ScheduledTaskInfo | None:
        try:
            output = self.command_runner.run(("schtasks", "/Query", "/TN", name, "/FO", "CSV", "/V"))
        except Exception as exc:
            if _looks_like_task_not_found_error(str(exc)):
                return ScheduledTaskInfo(name=name, exists=False)
            return None

        task = parse_schtasks_csv(name, output)
        if task is None:
            return None
        if task.exists and (not task.trigger_time or not task.executable):
            return None
        return task

    def _get_task_with_powershell(self, name: str) -> ScheduledTaskInfo:
        escaped_name = _escape_powershell_single_quoted(name)
        script = f"""
$ErrorActionPreference = 'Stop'
Import-Module ScheduledTasks -ErrorAction Stop
$taskName = '{escaped_name}'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {{
    [PSCustomObject]@{{
        Exists = $false
        TaskName = $taskName
    }} | ConvertTo-Json -Depth 4
    exit 0
}}
$action = $task.Actions | Select-Object -First 1
$trigger = $task.Triggers | Select-Object -First 1
[PSCustomObject]@{{
    Exists = $true
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
            message = str(exc)
            if _looks_like_task_not_found_error(message):
                return ScheduledTaskInfo(name=name, exists=False)
            return ScheduledTaskInfo(name=name, exists=False, error=str(exc))

        return parse_scheduled_task_json(name, output)


def parse_schtasks_csv(name: str, output: str) -> ScheduledTaskInfo | None:
    if not output.strip():
        return ScheduledTaskInfo(name=name, exists=False)
    try:
        rows = list(csv.DictReader(io.StringIO(output)))
    except csv.Error:
        return None
    if not rows:
        return ScheduledTaskInfo(name=name, exists=False)

    row = rows[0]
    task_name = _read_first_present(row, ("TaskName", "Task Name", "작업 이름")) or name
    task_to_run = _read_first_present(row, ("Task To Run", "TaskToRun", "실행할 작업", "실행할 작업:"))
    start_time = _read_first_present(row, ("Start Time", "StartTime", "시작 시간"))
    executable, arguments = _split_task_to_run(task_to_run)
    return ScheduledTaskInfo(
        name=str(task_name).lstrip("\\") or name,
        exists=True,
        trigger_time=_parse_time(start_time),
        executable=executable,
        arguments=arguments,
        raw=row,
    )


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

    exists_value = _read_first_present(parsed, ("Exists", "exists"))
    if _boolish(exists_value) is False:
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


def _boolish(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _looks_like_task_not_found_error(message: str) -> bool:
    normalized = message.casefold()
    return any(
        token in normalized
        for token in (
            "no msft_scheduledtask objects found",
            "cannot find",
            "not found",
            "does not exist",
            "지정된 작업",
            "찾을 수 없습니다",
            "개체를 찾을 수 없습니다",
            "cannot find the file specified",
            "system cannot find",
            "지정된 파일을 찾을 수 없습니다",
        )
    )


def _parse_time(value: object) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = re.search(
        r"(?:(?P<prefix>AM|PM|오전|오후)\s*)?"
        r"(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::\d{2})?"
        r"\s*(?P<suffix>AM|PM|오전|오후)?",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None

    hour = int(match.group("hour"))
    period = (match.group("prefix") or match.group("suffix") or "").casefold()
    if period in {"pm", "오후"} and hour < 12:
        hour += 12
    if period in {"am", "오전"} and hour == 12:
        hour = 0
    return f"{hour:02d}:{match.group('minute')}"


def _split_task_to_run(value: object) -> tuple[str | None, str | None]:
    text = str(value or "").strip()
    if not text or text.upper() in {"N/A", "사용 안 함"}:
        return None, None
    try:
        parts = shlex.split(text, posix=False)
    except ValueError:
        parts = text.split()
    if not parts:
        return None, None
    executable = parts[0].strip('"')
    arguments = text[len(parts[0]) :].strip() or None
    return executable or None, arguments
