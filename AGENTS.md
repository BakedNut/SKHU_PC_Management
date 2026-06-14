# Repository Rules

- Do not modify `legacy/csharp/`.
- Do not commit real secrets.
- Do not import PySide6 in `domain` or `application`.
- Do not call Windows APIs directly from `domain` or `application`.
- Handle Windows behavior through ports and adapters.
- Keep the GUI thin.
- Prefer small use cases and testable units.
- Keep `AGENTS.md` visible in Git so automation and reviewers can see these rules.
- Treat `legacy/csharp/` as read-only migration reference material; include it only when the repository policy requires legacy reference source to be available to GitHub/Codex.
