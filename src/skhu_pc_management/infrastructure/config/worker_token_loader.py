from __future__ import annotations

from pathlib import Path

from skhu_pc_management.infrastructure.config.agent_config_loader import (
    AgentConfig,
    resolve_runtime_path,
)


def load_worker_token(config: AgentConfig) -> str | None:
    if config.worker_token_path is None:
        return None

    token_path = resolve_runtime_path(config.worker_token_path)

    if not token_path.exists():
        return None

    token = token_path.read_text(encoding="utf-8").strip()

    return token or None