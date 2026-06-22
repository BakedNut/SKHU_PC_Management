from __future__ import annotations

from pathlib import Path

from skhu_pc_management.application.safety import REAL_TASKBAR_APPLY_DISABLED_MESSAGE, SafetyGuard
from skhu_pc_management.application.use_cases.apply_taskbar_layout import ApplyTaskbarLayout
from skhu_pc_management.application.use_cases.validate_taskbar_resources import ValidateTaskbarResources
from skhu_pc_management.domain.resources.models import ResourceValidationResult, TaskbarApplyResult
from skhu_pc_management.infrastructure.windows.windows_taskbar_configurator import WindowsTaskbarConfigurator


class FakeTaskbarConfigurator:
    def __init__(self) -> None:
        self.apply_requests: list[bool] = []

    def validate_resources(self) -> ResourceValidationResult:
        return ResourceValidationResult(success=True, message="ok")

    def apply_taskbar_layout(self, dry_run: bool = True) -> TaskbarApplyResult:
        self.apply_requests.append(dry_run)
        return TaskbarApplyResult(success=True, message="ok", dry_run=dry_run)


class FakeCommandRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...]) -> str:
        self.commands.append(tuple(command))
        return ""


class FakeResourceResolver:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resources_root(self) -> Path:
        if not self.root.exists():
            raise FileNotFoundError(self.root)
        return self.root

    def resolve(self, relative_path: str) -> Path:
        path = self.root / relative_path
        if not path.exists():
            raise FileNotFoundError(path)
        return path


def test_apply_taskbar_layout_defaults_to_dry_run() -> None:
    configurator = FakeTaskbarConfigurator()

    result = ApplyTaskbarLayout(configurator).execute()

    assert result.success is True
    assert result.dry_run is True
    assert configurator.apply_requests == [True]


def test_apply_taskbar_layout_can_run_real_apply_when_allowed() -> None:
    configurator = FakeTaskbarConfigurator()

    result = ApplyTaskbarLayout(
        configurator,
        safety_guard=SafetyGuard(allow_real_taskbar_apply=True),
    ).execute(dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert configurator.apply_requests == [False]


def test_taskbar_validation_fails_when_reg_file_is_missing(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    (resources / "TaskBar").mkdir(parents=True)
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = ValidateTaskbarResources(configurator).execute()

    assert result.success is False
    assert result.message == "TaskBar.reg 파일을 찾을 수 없습니다."


def test_taskbar_validation_warns_when_shortcuts_are_missing(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    (resources / "TaskBar.reg").write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = configurator.validate_resources()

    assert result.success is True
    assert result.shortcut_files == ()
    assert result.warnings == ("TaskBar 폴더에 .lnk 바로가기 파일이 없습니다.",)


def test_taskbar_validation_finds_reg_and_shortcuts(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    reg_file = resources / "TaskBar.reg"
    reg_file.write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    shortcut = taskbar_dir / "Google Chrome.lnk"
    shortcut.write_text("shortcut", encoding="utf-8")
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = configurator.validate_resources()

    assert result.success is True
    assert result.reg_file == reg_file
    assert result.shortcut_files == (shortcut,)


def test_taskbar_dry_run_does_not_modify_files_or_run_system_commands(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    (resources / "TaskBar.reg").write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    shortcut = taskbar_dir / "Google Chrome.lnk"
    shortcut.write_text("shortcut", encoding="utf-8")
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = ApplyTaskbarLayout(configurator).execute(dry_run=True)

    assert result.success is True
    assert result.dry_run is True
    assert result.shortcut_files == (shortcut,)
    assert any("복사 예정: Google Chrome.lnk" in action for action in result.planned_actions)
    assert shortcut.read_text(encoding="utf-8") == "shortcut"


def test_taskbar_real_apply_requires_command_runner(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    (resources / "TaskBar.reg").write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    (taskbar_dir / "Google Chrome.lnk").write_text("shortcut", encoding="utf-8")
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = configurator.apply_taskbar_layout(dry_run=False)

    assert result.success is False
    assert "명령 실행기가 구성되지 않았습니다" in result.message


def test_taskbar_real_apply_is_blocked_by_default_policy(tmp_path: Path, monkeypatch) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    (resources / "TaskBar.reg").write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    (taskbar_dir / "Google Chrome.lnk").write_text("shortcut", encoding="utf-8")
    appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata))
    command_runner = FakeCommandRunner()
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources), command_runner)

    result = ApplyTaskbarLayout(configurator).execute(dry_run=False)

    assert result.success is False
    assert result.message == REAL_TASKBAR_APPLY_DISABLED_MESSAGE
    assert not appdata.exists()
    assert command_runner.commands == []


def test_taskbar_real_apply_uses_temp_appdata_and_fake_commands(tmp_path: Path, monkeypatch) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    reg_file = resources / "TaskBar.reg"
    reg_file.write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    shortcut = taskbar_dir / "Google Chrome.lnk"
    shortcut.write_text("shortcut", encoding="utf-8")

    appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata))
    target_dir = appdata / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
    target_dir.mkdir(parents=True)
    old_shortcut = target_dir / "Old.lnk"
    old_shortcut.write_text("old", encoding="utf-8")

    command_runner = FakeCommandRunner()
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources), command_runner)

    result = ApplyTaskbarLayout(
        configurator,
        safety_guard=SafetyGuard(allow_real_taskbar_apply=True),
    ).execute(dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert not old_shortcut.exists()
    assert (target_dir / "Google Chrome.lnk").read_text(encoding="utf-8") == "shortcut"
    assert command_runner.commands == [
        ("reg", "import", str(reg_file)),
        ("taskkill", "/F", "/IM", "explorer.exe"),
        ("explorer.exe",),
    ]
