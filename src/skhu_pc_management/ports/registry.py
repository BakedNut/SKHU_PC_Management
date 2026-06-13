from __future__ import annotations

from typing import Protocol


class Registry(Protocol):
    def read_value(self, root: str, path: str, name: str) -> object | None:
        """Read a registry value."""

    def list_subkeys(self, root: str, path: str) -> list[str]:
        """List registry subkey names."""

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        """Write a registry value."""
