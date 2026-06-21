import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    api_base_url: str
    agent_api_key: str
    timeout_seconds: int = 10
    auto_send_on_startup: bool = False
    max_retry_count: int = 3
    retry_delay_seconds: int = 5
    worker_token_path: str | None = None


def load_agent_config(path: str | Path = "config.json") -> AgentConfig:
    config_path = _resolve_config_path(path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Agent config file not found: {config_path}. "
            "Copy config.example.json to config.json first."
        )

    data = json.loads(config_path.read_text(encoding="utf-8"))

    return AgentConfig(
        api_base_url=str(data["apiBaseUrl"]).rstrip("/"),
        agent_api_key=str(data["agentApiKey"]),
        timeout_seconds=int(data.get("timeoutSeconds", 10)),
        auto_send_on_startup=bool(data.get("autoSendOnStartup", False)),
        max_retry_count=max(1, int(data.get("maxRetryCount", 3))),
        retry_delay_seconds=max(0, int(data.get("retryDelaySeconds", 5))),
        worker_token_path=_normalize_optional_text(data.get("workerTokenPath")),
    )


def resolve_runtime_path(path: str | Path) -> Path:
    requested_path = Path(path)

    if requested_path.is_absolute():
        return requested_path

    return _runtime_dir() / requested_path


def _resolve_config_path(path: str | Path) -> Path:
    requested_path = Path(path)

    if requested_path.is_absolute():
        return requested_path

    candidates = [
        _runtime_dir() / requested_path,
        Path.cwd() / requested_path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path.cwd()


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None