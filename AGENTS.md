# Repository Rules

* Do not modify `legacy/csharp/`.
* Do not modify `legacy/pcinfocrawler_cpp/`.
* Treat `legacy/csharp/` as read-only C# migration reference material.
* Treat `legacy/pcinfocrawler_cpp/` as read-only C++ PC information crawler reference material.
* Do not call, build, or depend on executables from `legacy/` at runtime.
* Reimplement needed legacy behavior in Python through the proper architecture layers.
* Do not commit real secrets.
* Do not import PySide6 in `domain` or `application`.
* Do not call Windows APIs directly from `domain` or `application`.
* Handle Windows behavior through ports and adapters.
* Keep Windows API, WMI, registry, ctypes, subprocess, and OS-specific behavior inside `infrastructure/windows` adapters.
* Keep the GUI thin.
* Prefer small use cases and testable units.
* Keep `AGENTS.md` visible in Git so automation and reviewers can see these rules.
* Include legacy reference source only when repository policy requires it to be available to GitHub/Codex.
