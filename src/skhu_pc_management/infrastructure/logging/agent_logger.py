from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def create_agent_logger() -> logging.Logger:
    logs_dir = _runtime_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("skhu_pc_management.agent")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler = RotatingFileHandler(
        logs_dir / "agent.log",
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    logger.addHandler(handler)

    return logger


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path.cwd()