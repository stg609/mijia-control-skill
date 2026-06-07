from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .policy import MijiaError


def default_data_dir() -> Path:
    configured = os.environ.get("MIJIACTL_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "mijiactl"


def default_auth_path() -> Path:
    configured = os.environ.get("MIJIA_AUTH_FILE")
    if configured:
        return Path(configured).expanduser()
    return default_data_dir() / "auth.json"


def load_auth(path: Path | None = None) -> dict[str, Any]:
    auth_path = path or default_auth_path()
    if not auth_path.exists():
        raise MijiaError("AUTH_MISSING", f"Authentication file not found at '{auth_path}'.")
    try:
        return json.loads(auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MijiaError("AUTH_INVALID", "Authentication file is not valid JSON.") from exc


def auth_status(path: Path | None = None) -> dict[str, Any]:
    auth_path = path or default_auth_path()
    if not auth_path.exists():
        return {"path": str(auth_path), "present": False, "key_count": 0, "required_keys": {}}
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"path": str(auth_path), "present": True, "valid_json": False, "key_count": 0, "required_keys": {}}
    required = ("serviceToken", "ssecurity", "userId", "deviceId")
    return {
        "path": str(auth_path),
        "present": True,
        "valid_json": True,
        "key_count": len(payload),
        "required_keys": {key: key in payload for key in required},
    }


def auth_cache_namespace(path: Path | None = None) -> str:
    auth_path = path or default_auth_path()
    if not auth_path.exists():
        return "default"
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "default"
    identity = "|".join(str(payload.get(key) or "") for key in ("userId", "deviceId"))
    if not identity.strip("|"):
        return "default"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
