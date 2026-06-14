from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.domain.resources.models import ResourceValidationResult, TaskbarApplyResult
from skhu_pc_management.ports.resource_resolver import ResourceResolver


@dataclass(frozen=True)
class WindowsTaskbarConfigurator:
    resource_resolver: ResourceResolver

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

        return TaskbarApplyResult(
            success=False,
            message="실제 작업표시줄 적용은 아직 구현되지 않았습니다. dry-run 결과를 확인한 뒤 별도 구현이 필요합니다.",
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
