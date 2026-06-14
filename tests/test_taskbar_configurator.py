from __future__ import annotations

from pathlib import Path

from skhu_pc_management.application.use_cases.apply_taskbar_layout import ApplyTaskbarLayout
from skhu_pc_management.application.use_cases.validate_taskbar_resources import ValidateTaskbarResources
from skhu_pc_management.infrastructure.windows.windows_taskbar_configurator import WindowsTaskbarConfigurator


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


def test_taskbar_real_apply_is_blocked_until_explicit_implementation(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    taskbar_dir = resources / "TaskBar"
    taskbar_dir.mkdir(parents=True)
    (resources / "TaskBar.reg").write_text("Windows Registry Editor Version 5.00", encoding="utf-8")
    (taskbar_dir / "Google Chrome.lnk").write_text("shortcut", encoding="utf-8")
    configurator = WindowsTaskbarConfigurator(FakeResourceResolver(resources))

    result = configurator.apply_taskbar_layout(dry_run=False)

    assert result.success is False
    assert "아직 구현되지 않았습니다" in result.message
