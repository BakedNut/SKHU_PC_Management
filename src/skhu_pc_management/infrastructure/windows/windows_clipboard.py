from __future__ import annotations

import ctypes
from ctypes import wintypes


class WindowsClipboard:
    def set_text(self, text: str) -> None:
        _configure_ctypes()
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        data = text + "\0"
        buffer = ctypes.create_unicode_buffer(data)
        size = ctypes.sizeof(buffer)

        if not user32.OpenClipboard(None):
            raise RuntimeError("Failed to open clipboard.")

        handle = None
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(0x0002, size)
            if not handle:
                raise RuntimeError("Failed to allocate clipboard memory.")

            locked = kernel32.GlobalLock(handle)
            if not locked:
                raise RuntimeError("Failed to lock clipboard memory.")

            try:
                ctypes.memmove(locked, ctypes.addressof(buffer), size)
            finally:
                kernel32.GlobalUnlock(handle)

            if not user32.SetClipboardData(13, handle):
                raise RuntimeError("Failed to set clipboard data.")
            handle = None
        finally:
            user32.CloseClipboard()
            if handle:
                kernel32.GlobalFree(handle)


_CTYPES_CONFIGURED = False


def _configure_ctypes() -> None:
    global _CTYPES_CONFIGURED
    if _CTYPES_CONFIGURED:
        return

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    handle_type = wintypes.HANDLE

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, handle_type]
    user32.SetClipboardData.restype = handle_type
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = handle_type
    kernel32.GlobalLock.argtypes = [handle_type]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [handle_type]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [handle_type]
    kernel32.GlobalFree.restype = handle_type

    _CTYPES_CONFIGURED = True
