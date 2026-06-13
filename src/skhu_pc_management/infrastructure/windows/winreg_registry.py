from __future__ import annotations


class WinregRegistry:
    def read_value(self, root: str, path: str, name: str) -> object | None:
        raise NotImplementedError(f"Registry read is not implemented yet: {root}\\{path}\\{name}")

    def write_value(self, root: str, path: str, name: str, value: object, value_type: str) -> None:
        raise NotImplementedError(f"Registry write is not implemented yet: {root}\\{path}\\{name}")
