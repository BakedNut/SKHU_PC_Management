from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from skhu_pc_management.domain.settings.definitions import HKCU, HKLM
from skhu_pc_management.domain.settings.models import SettingStatus
from skhu_pc_management.ports.command_runner import CommandRunner
from skhu_pc_management.ports.registry import Registry
from skhu_pc_management.ports.resource_resolver import ResourceResolver


@dataclass(frozen=True)
class DefaultWallpaperStatusProvider:
    registry: Registry

    def check(self, setting_id: str) -> SettingStatus:
        label = "기본 배경화면 설정"
        try:
            current = self.registry.read_value(HKCU, r"Control Panel\Desktop", "Wallpaper")
            expected = str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Web" / "Wallpaper" / "Windows" / "img0.jpg")
        except Exception as exc:
            return _unknown(setting_id, label, f"배경화면 상태를 확인할 수 없습니다: {exc}")

        configured = _same_path(current, expected)
        return SettingStatus(
            setting_id=setting_id,
            label=label,
            name=label,
            expected_value=expected,
            actual_value=current,
            is_configured=configured,
            is_applied=configured,
            severity="ok" if configured else "warning",
            status_text="configured" if configured else "not_configured",
            current_value="" if current is None else str(current),
            detail=f"현재 배경화면: {current or '없음'} / 기본값: {expected}",
        )


@dataclass(frozen=True)
class EdgeShortcutStatusProvider:
    registry: Registry

    def check(self, setting_id: str) -> SettingStatus:
        label = "바탕화면 Edge 바로가기 삭제"
        public_shortcut = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop" / "Microsoft Edge.lnk"
        user_shortcut = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Microsoft Edge.lnk"
        try:
            policy = self.registry.read_value(
                HKLM,
                r"SOFTWARE\Policies\Microsoft\EdgeUpdate",
                "CreateDesktopShortcutDefault",
            )
        except Exception as exc:
            return _unknown(setting_id, label, f"Edge 바로가기 정책을 확인할 수 없습니다: {exc}")

        existing = [path for path in (public_shortcut, user_shortcut) if path.exists()]
        configured = not existing and str(policy) == "0"
        detail = f"남은 바로가기: {', '.join(str(path) for path in existing) or '없음'} / 정책값: {policy}"
        return SettingStatus(
            setting_id=setting_id,
            label=label,
            name=label,
            expected_value="바로가기 없음, 정책값 0",
            actual_value=detail,
            is_configured=configured,
            is_applied=configured,
            severity="ok" if configured else "warning",
            status_text="configured" if configured else "not_configured",
            current_value=detail,
            detail=detail,
        )


@dataclass(frozen=True)
class TaskbarLayoutStatusProvider:
    resource_resolver: ResourceResolver

    def check(self, setting_id: str) -> SettingStatus:
        label = "작업표시줄 아이콘 설정"
        try:
            source_dir = self.resource_resolver.resolve("TaskBar")
            source_names = _shortcut_names(source_dir)
            target_dir = _taskbar_target_dir()
            target_names = _shortcut_names(target_dir) if target_dir.exists() else set()
        except Exception as exc:
            return _unknown(setting_id, label, f"작업표시줄 리소스 상태를 확인할 수 없습니다: {exc}")

        missing = sorted(source_names - target_names)
        extra = sorted(target_names - source_names)
        configured = not missing and not extra and bool(source_names)
        detail = (
            f"소스={sorted(source_names)}, 대상={sorted(target_names)}, "
            f"누락={missing or '없음'}, 추가={extra or '없음'}; 실제 pin 상태는 Windows Shell 정책에 따라 다를 수 있습니다."
        )
        return SettingStatus(
            setting_id=setting_id,
            label=label,
            name=label,
            expected_value=tuple(sorted(source_names)),
            actual_value=tuple(sorted(target_names)),
            is_configured=configured,
            is_applied=configured,
            severity="ok" if configured else "warning",
            status_text="configured" if configured else "not_configured",
            current_value=", ".join(sorted(target_names)),
            detail=detail,
        )


@dataclass(frozen=True)
class PasswordExpirationStatusProvider:
    command_runner: CommandRunner

    def check(self, setting_id: str) -> SettingStatus:
        label = "사용자 계정 암호 만료 비활성화"
        try:
            output = self.command_runner.run(
                (
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "Get-LocalUser | Select-Object Name, Enabled, PasswordNeverExpires | ConvertTo-Json -Depth 3",
                )
            )
            users = _json_items(output)
        except Exception as exc:
            return _unknown(setting_id, label, f"로컬 사용자 암호 만료 상태를 확인할 수 없습니다: {exc}")

        enabled_users = [user for user in users if bool(user.get("Enabled"))]
        expiring_users = [str(user.get("Name")) for user in enabled_users if not bool(user.get("PasswordNeverExpires"))]
        configured = not expiring_users
        detail = "암호 만료 대상 사용자: " + (", ".join(expiring_users) if expiring_users else "없음")
        return SettingStatus(
            setting_id=setting_id,
            label=label,
            name=label,
            expected_value="Enabled users PasswordNeverExpires=True",
            actual_value=detail,
            is_configured=configured,
            is_applied=configured,
            severity="ok" if configured else "warning",
            status_text="configured" if configured else "not_configured",
            current_value=detail,
            detail=detail,
        )


def _unknown(setting_id: str, label: str, detail: str) -> SettingStatus:
    return SettingStatus(
        setting_id=setting_id,
        label=label,
        name=label,
        severity="unknown",
        status_text="unknown",
        detail=detail,
        current_value=detail,
    )


def _same_path(left: object, right: str) -> bool:
    if left is None:
        return False
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(right))


def _shortcut_names(directory: Path) -> set[str]:
    if not directory.exists() or not directory.is_dir():
        return set()
    return {path.name for path in directory.glob("*.lnk")}


def _taskbar_target_dir() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"


def _json_items(output: str) -> list[dict[str, Any]]:
    if not output.strip():
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []
