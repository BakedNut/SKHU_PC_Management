from __future__ import annotations

import ctypes
from ctypes import wintypes

from skhu_pc_management.domain.checks.models import RecycleBinStatus


class _ShQueryRecycleBinInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_longlong),
        ("i64NumItems", ctypes.c_longlong),
    ]


class WindowsRecycleBinReader:
    def read_status(self) -> RecycleBinStatus:
        info = _ShQueryRecycleBinInfo()
        info.cbSize = ctypes.sizeof(_ShQueryRecycleBinInfo)
        try:
            result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        except Exception:
            return RecycleBinStatus(item_count=None, size_bytes=None)

        if result != 0:
            return RecycleBinStatus(item_count=None, size_bytes=None)
        return RecycleBinStatus(item_count=int(info.i64NumItems), size_bytes=int(info.i64Size))
