from __future__ import annotations

import sys
from pathlib import Path


class PyInstallerResourceResolver:
    def resolve(self, relative_path: str) -> Path:
        resources_root = self.resources_root()
        path = resources_root / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Resource not found: {path}")
        return path

    def resources_root(self) -> Path:
        candidates = _candidate_resource_roots()
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        searched = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"Resources directory was not found. Searched: {searched}")


def _candidate_resource_roots() -> list[Path]:
    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        candidates.append(base / "resources")
        candidates.append(base)

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        candidates.append(executable_dir / "resources")
        candidates.append(executable_dir / "_internal" / "resources")

    current = Path.cwd().resolve()
    candidates.append(current / "resources")
    candidates.extend(parent / "resources" for parent in current.parents)

    module_path = Path(__file__).resolve()
    candidates.extend(parent / "resources" for parent in module_path.parents)

    return _deduplicate(candidates)


def _deduplicate(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result
