from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .auth import default_data_dir


def default_config_dir() -> Path:
    configured = os.environ.get("MIJIACTL_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser()
    return default_data_dir()


def default_config_path() -> Path:
    configured = os.environ.get("MIJIA_CONFIG_FILE")
    if configured:
        return Path(configured).expanduser()
    return default_config_dir() / "config.json"


def default_config() -> dict[str, Any]:
    return {
        "disabled_devices": [{"model": "lock"}, {"model": "camera"}, {"model": "cateye"}],
        "disabled_actions": [],
        "confirm_required": [
            {"action": "scene-run"},
            {"action": "start"},
            {"action": "run"},
            {"action": "unlock"},
            {"action": "record"},
            {"model": "plug", "action": "set"},
            {"model": "washer"},
            {"model": "dishwasher"},
            {"model": "vacuum"},
        ],
    }


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or default_config_path()
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def write_default_config(path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(json.dumps(default_config(), ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path
