from __future__ import annotations

import subprocess
from types import SimpleNamespace

from skhu_pc_management.infrastructure.windows import subprocess_command_runner
from skhu_pc_management.infrastructure.windows.subprocess_command_runner import (
    SubprocessCommandRunner,
    _hidden_subprocess_kwargs,
)


def test_hidden_subprocess_kwargs_returns_empty_on_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_command_runner.os, "name", "posix")

    assert _hidden_subprocess_kwargs() == {}


def test_hidden_subprocess_kwargs_sets_windows_no_window_flags(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_command_runner.os, "name", "nt")

    kwargs = _hidden_subprocess_kwargs()

    assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
    startupinfo = kwargs["startupinfo"]
    assert startupinfo.dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert startupinfo.wShowWindow == subprocess.SW_HIDE


def test_subprocess_command_runner_passes_hidden_kwargs_and_captures_stdout(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return SimpleNamespace(stdout=" result \n")

    monkeypatch.setattr(subprocess_command_runner.os, "name", "nt")
    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    output = SubprocessCommandRunner().run(("powershell", "-NoProfile", "-Command", "Write-Output result"))

    assert output == "result"
    assert calls == [
        {
            "command": ["powershell", "-NoProfile", "-Command", "Write-Output result"],
            "check": True,
            "capture_output": True,
            "text": True,
            "shell": False,
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "startupinfo": calls[0]["startupinfo"],
        }
    ]
    startupinfo = calls[0]["startupinfo"]
    assert startupinfo.dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert startupinfo.wShowWindow == subprocess.SW_HIDE


def test_subprocess_command_runner_returns_empty_when_stdout_is_none(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return SimpleNamespace(stdout=None)

    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    assert SubprocessCommandRunner().run(("netsh", "test")) == ""


def test_subprocess_command_runner_strips_stdout(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return SimpleNamespace(stdout=" ok\n")

    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    assert SubprocessCommandRunner().run(("netsh", "test")) == "ok"


def test_subprocess_command_runner_raises_runtime_error_from_stderr(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, output="", stderr="관리자 권한이 필요합니다.\n")

    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    try:
        SubprocessCommandRunner().run(("netsh", "test"))
    except RuntimeError as exc:
        assert str(exc) == "관리자 권한이 필요합니다."
    else:
        raise AssertionError("RuntimeError was not raised")


def test_subprocess_command_runner_raises_runtime_error_from_stdout_when_stderr_is_empty(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, output="netsh failed\n", stderr="")

    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    try:
        SubprocessCommandRunner().run(("netsh", "test"))
    except RuntimeError as exc:
        assert str(exc) == "netsh failed"
    else:
        raise AssertionError("RuntimeError was not raised")


def test_subprocess_command_runner_raises_exit_code_message_when_output_is_none(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(7, command, output=None, stderr=None)

    monkeypatch.setattr(subprocess_command_runner.subprocess, "run", fake_run)

    try:
        SubprocessCommandRunner().run(("netsh", "test"))
    except RuntimeError as exc:
        assert str(exc) == "Command failed with exit code 7."
    else:
        raise AssertionError("RuntimeError was not raised")
