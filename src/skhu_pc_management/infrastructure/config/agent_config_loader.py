import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    api_base_url: str
    agent_api_key: str
    timeout_seconds: int = 10


def load_agent_config(path: str | Path = "config.json") -> AgentConfig:
    config_path = Path(path)

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
    )