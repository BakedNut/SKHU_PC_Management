from __future__ import annotations

import ctypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from skhu_pc_management.ports.auto_shutdown_cancel_shortcut import (
    AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME,
    AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE,
    AutoShutdownCancelShortcutStatus,
)
from skhu_pc_management.ports.resource_resolver import ResourceResolver


SOURCE_MISSING_MESSAGE = "자동종료 취소 바로가기 리소스를 찾을 수 없습니다."
DESKTOP_MISSING_MESSAGE = f"바탕화면에 {AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME}가 없습니다."
MISMATCH_MESSAGE = f"바탕화면의 {AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME}가 리소스 원본과 다릅니다."


@dataclass(frozen=True)
class WindowsAutoShutdownCancelShortcut:
    resource_resolver: ResourceResolver

    def install(self) -> Path:
        try:
            source = self.resource_resolver.resolve(AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE)
        except FileNotFoundError as exc:
            raise RuntimeError(SOURCE_MISSING_MESSAGE) from exc

        target = _current_user_desktop_dir() / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except Exception as exc:
            raise RuntimeError(f"자동종료 취소 바로가기 복사에 실패했습니다: {exc}") from exc

        if not _same_file_bytes(source, target):
            raise RuntimeError("자동종료 취소 바로가기 복사에 실패했습니다: 복사한 파일이 원본과 다릅니다.")
        return target

    def check(self) -> AutoShutdownCancelShortcutStatus:
        source = _fallback_source_path(self.resource_resolver)
        target = _current_user_desktop_dir() / AUTO_SHUTDOWN_CANCEL_SHORTCUT_NAME

        try:
            source = self.resource_resolver.resolve(AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE)
        except FileNotFoundError:
            return AutoShutdownCancelShortcutStatus(
                source_path=source,
                desktop_path=target,
                source_exists=False,
                desktop_exists=target.exists(),
                matches=False,
                error=SOURCE_MISSING_MESSAGE,
            )

        source_exists = source.exists()
        desktop_exists = target.exists()
        if not source_exists:
            return AutoShutdownCancelShortcutStatus(
                source_path=source,
                desktop_path=target,
                source_exists=False,
                desktop_exists=desktop_exists,
                matches=False,
                error=SOURCE_MISSING_MESSAGE,
            )
        if not desktop_exists:
            return AutoShutdownCancelShortcutStatus(
                source_path=source,
                desktop_path=target,
                source_exists=True,
                desktop_exists=False,
                matches=False,
                error=DESKTOP_MISSING_MESSAGE,
            )

        try:
            matches = _same_file_bytes(source, target)
        except OSError as exc:
            return AutoShutdownCancelShortcutStatus(
                source_path=source,
                desktop_path=target,
                source_exists=True,
                desktop_exists=True,
                matches=False,
                error=f"자동종료 취소 바로가기 상태를 확인할 수 없습니다: {exc}",
            )

        return AutoShutdownCancelShortcutStatus(
            source_path=source,
            desktop_path=target,
            source_exists=True,
            desktop_exists=True,
            matches=matches,
            error=None if matches else MISMATCH_MESSAGE,
        )


def _current_user_desktop_dir() -> Path:
    known_folder = _known_folder_desktop()
    if known_folder is not None:
        known_folder.mkdir(parents=True, exist_ok=True)
        return known_folder

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        desktop = Path(user_profile) / "Desktop"
    else:
        desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    return desktop


def _known_folder_desktop() -> Path | None:
    if os.name != "nt":
        return None

    class GUID(ctypes.Structure):
        _fields_ = (
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        )

    folder_id_desktop = GUID(
        0xB4BFCC3A,
        0xDB2C,
        0x424C,
        (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
    )
    path_ptr = ctypes.c_void_p()
    try:
        ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folder_id_desktop), 0, None, ctypes.byref(path_ptr))
        if not path_ptr.value:
            return None
        return Path(ctypes.wstring_at(path_ptr.value))
    except Exception:
        return None
    finally:
        try:
            if path_ptr.value:
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        except Exception:
            pass


def _fallback_source_path(resource_resolver: ResourceResolver) -> Path:
    try:
        return resource_resolver.resources_root() / AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE
    except Exception:
        return Path(AUTO_SHUTDOWN_CANCEL_SHORTCUT_RESOURCE)


def _same_file_bytes(source: Path, target: Path) -> bool:
    return source.read_bytes() == target.read_bytes()
