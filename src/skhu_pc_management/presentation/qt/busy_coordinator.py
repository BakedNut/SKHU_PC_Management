from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator


BusyListener = Callable[[bool, str], None]


@dataclass
class BusyCoordinator:
    is_busy: bool = False
    message: str = ""
    _listeners: list[BusyListener] = field(default_factory=list)

    def add_listener(self, listener: BusyListener) -> None:
        self._listeners.append(listener)

    def begin(self, message: str) -> None:
        if self.is_busy:
            raise RuntimeError("다른 작업이 진행 중입니다.")
        self.is_busy = True
        self.message = message
        self._notify()

    def try_begin(self, message: str) -> bool:
        if self.is_busy:
            return False
        self.begin(message)
        return True

    def end(self, message: str = "") -> None:
        self.is_busy = False
        self.message = message
        self._notify()

    @contextmanager
    def guard(self, message: str, done_message: str = "") -> Iterator[bool]:
        if not self.try_begin(message):
            yield False
            return
        try:
            yield True
        finally:
            self.end(done_message)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener(self.is_busy, self.message)
