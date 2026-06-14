from __future__ import annotations

import winreg


_ROOTS = {
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
}

_VALUE_TYPES = {
    "REG_DWORD": winreg.REG_DWORD,
    "REG_SZ": winreg.REG_SZ,
    "REG_STRING": winreg.REG_SZ,
}


class WinregRegistry:
    def read_value(self, root: str, path: str, name: str) -> object | None:
        try:
            with winreg.OpenKey(_resolve_root(root), path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except PermissionError:
            raise
        except (FileNotFoundError, OSError):
            return None

    def list_subkeys(self, root: str, path: str) -> list[str]:
        with winreg.OpenKey(_resolve_root(root), path) as key:
            subkeys: list[str] = []
            index = 0
            while True:
                try:
                    subkeys.append(winreg.EnumKey(key, index))
                except OSError:
                    return subkeys
                index += 1

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        with winreg.CreateKeyEx(_resolve_root(root), path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, _resolve_value_type(value_type), value)


def _resolve_root(root: str) -> int:
    try:
        return _ROOTS[root]
    except KeyError as exc:
        raise ValueError(f"Unsupported registry root: {root}") from exc


def _resolve_value_type(value_type: str) -> int:
    try:
        return _VALUE_TYPES[value_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported registry value type: {value_type}") from exc
