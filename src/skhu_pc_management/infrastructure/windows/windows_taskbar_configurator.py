from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from skhu_pc_management.domain.resources.models import ResourceValidationResult, TaskbarApplyResult
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.resource_resolver import ResourceResolver


@dataclass(frozen=True)
class WindowsTaskbarConfigurator:
    resource_resolver: ResourceResolver
    command_runner: CommandRunner | None = None

    def validate_resources(self) -> ResourceValidationResult:
        try:
            resources_root = self.resource_resolver.resources_root()
        except AttributeError:
            try:
                taskbar_reg = self.resource_resolver.resolve("TaskBar.reg")
                resources_root = taskbar_reg.parent
            except Exception as exc:
                return ResourceValidationResult(False, f"Resources 폴더를 찾을 수 없습니다: {exc}")
        except Exception as exc:
            return ResourceValidationResult(False, f"Resources 폴더를 찾을 수 없습니다: {exc}")

        reg_file = resources_root / "TaskBar.reg"
        taskbar_dir = resources_root / "TaskBar"
        warnings: list[str] = []

        if not reg_file.exists():
            return ResourceValidationResult(
                success=False,
                message="TaskBar.reg 파일을 찾을 수 없습니다.",
                resources_root=resources_root,
                reg_file=reg_file,
                taskbar_dir=taskbar_dir,
            )

        if not taskbar_dir.exists() or not taskbar_dir.is_dir():
            return ResourceValidationResult(
                success=False,
                message="TaskBar 폴더를 찾을 수 없습니다.",
                resources_root=resources_root,
                reg_file=reg_file,
                taskbar_dir=taskbar_dir,
            )

        shortcuts = tuple(sorted(taskbar_dir.glob("*.lnk"), key=lambda path: path.name.lower()))
        if not shortcuts:
            warnings.append("TaskBar 폴더에 .lnk 바로가기 파일이 없습니다.")

        return ResourceValidationResult(
            success=True,
            message="작업표시줄 리소스를 확인했습니다." if shortcuts else "작업표시줄 리소스는 있으나 바로가기 파일이 없습니다.",
            resources_root=resources_root,
            reg_file=reg_file,
            taskbar_dir=taskbar_dir,
            shortcut_files=shortcuts,
            warnings=tuple(warnings),
        )

    def apply_taskbar_layout(self, dry_run: bool = True) -> TaskbarApplyResult:
        validation = self.validate_resources()
        if not validation.success:
            return TaskbarApplyResult(
                success=False,
                message=validation.message,
                dry_run=dry_run,
                reg_file=validation.reg_file,
                shortcut_files=validation.shortcut_files,
            )

        planned_actions = _planned_actions(validation)
        if dry_run:
            return TaskbarApplyResult(
                success=True,
                message="작업표시줄 설정 dry-run이 완료되었습니다. 실제 변경은 수행하지 않았습니다.",
                dry_run=True,
                reg_file=validation.reg_file,
                shortcut_files=validation.shortcut_files,
                planned_actions=planned_actions,
            )

        if self.command_runner is None:
            return TaskbarApplyResult(
                success=False,
                message="작업표시줄 설정 적용을 위한 명령 실행기가 구성되지 않았습니다.",
                dry_run=False,
                reg_file=validation.reg_file,
                shortcut_files=validation.shortcut_files,
                planned_actions=planned_actions,
            )

        try:
            target_dir = _taskbar_target_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            for shortcut in target_dir.glob("*.lnk"):
                shortcut.unlink()
            for shortcut in validation.shortcut_files:
                shutil.copy2(shortcut, target_dir / shortcut.name)
            if validation.reg_file is not None:
                self.command_runner.run(("reg", "import", str(validation.reg_file)))
        except Exception as exc:
            return TaskbarApplyResult(
                success=False,
                message=f"작업표시줄 설정 적용 실패: {exc}",
                dry_run=False,
                reg_file=validation.reg_file,
                shortcut_files=validation.shortcut_files,
                planned_actions=planned_actions,
            )

        for command in (("taskkill", "/F", "/IM", "explorer.exe"), ("explorer.exe",)):
            try:
                self.command_runner.run(command)
            except Exception:
                pass

        return TaskbarApplyResult(
            success=True,
            message="작업표시줄 설정을 적용했습니다.",
            dry_run=False,
            reg_file=validation.reg_file,
            shortcut_files=validation.shortcut_files,
            planned_actions=planned_actions,
        )


def _planned_actions(validation: ResourceValidationResult) -> tuple[str, ...]:
    actions: list[str] = []
    if validation.taskbar_dir is not None:
        actions.append(f"TaskBar 바로가기 원본 확인: {validation.taskbar_dir}")
    for shortcut in validation.shortcut_files:
        actions.append(f"복사 예정: {shortcut.name}")
    if validation.reg_file is not None:
        actions.append(f"레지스트리 적용 예정: {validation.reg_file}")
    actions.append("Explorer 재시작 예정")
    return tuple(actions)


def _taskbar_target_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA 환경변수를 찾을 수 없습니다.")
    return Path(appdata) / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
