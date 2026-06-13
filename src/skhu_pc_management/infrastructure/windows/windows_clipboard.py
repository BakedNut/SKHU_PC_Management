from __future__ import annotations

import ctypes


class WindowsClipboard:
    def set_text(self, text: str) -> None:
        data = text + "\0"
        buffer = ctypes.create_unicode_buffer(data)
        size = ctypes.sizeof(buffer)

        if not ctypes.windll.user32.OpenClipboard(None):
            raise RuntimeError("Failed to open clipboard.")

        handle = None
        try:
            ctypes.windll.user32.EmptyClipboard()
            handle = ctypes.windll.kernel32.GlobalAlloc(0x0002, size)
            if not handle:
                raise RuntimeError("Failed to allocate clipboard memory.")

            locked = ctypes.windll.kernel32.GlobalLock(handle)
            if not locked:
                raise RuntimeError("Failed to lock clipboard memory.")

            try:
                ctypes.memmove(locked, ctypes.addressof(buffer), size)
            finally:
                ctypes.windll.kernel32.GlobalUnlock(handle)

            if not ctypes.windll.user32.SetClipboardData(13, handle):
                raise RuntimeError("Failed to set clipboard data.")
            handle = None
        finally:
            ctypes.windll.user32.CloseClipboard()
            if handle:
                ctypes.windll.kernel32.GlobalFree(handle)
