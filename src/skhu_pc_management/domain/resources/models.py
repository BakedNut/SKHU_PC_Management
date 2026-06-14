from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ResourceValidationResult:
    success: bool
    message: str
    resources_root: Path | None = None
    reg_file: Path | None = None
    taskbar_dir: Path | None = None
    shortcut_files: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskbarApplyResult:
    success: bool
    message: str
    dry_run: bool = True
    reg_file: Path | None = None
    shortcut_files: tuple[Path, ...] = ()
    planned_actions: tuple[str, ...] = field(default_factory=tuple)
