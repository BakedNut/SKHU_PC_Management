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
        candidates.extend(_resource_dir_candidates(base))
        candidates.append(base)

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        candidates.extend(_resource_dir_candidates(executable_dir))
        candidates.extend(_resource_dir_candidates(executable_dir / "_internal"))

    current = Path.cwd().resolve()
    candidates.extend(_resource_dir_candidates(current))
    for parent in current.parents:
        candidates.extend(_resource_dir_candidates(parent))

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidates.extend(_resource_dir_candidates(parent))

    return _deduplicate(candidates)


def _resource_dir_candidates(base: Path) -> list[Path]:
    return [base / "resources", base / "Resources"]


def _deduplicate(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result
