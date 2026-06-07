from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from .auth import default_data_dir

DEFAULT_SNAPSHOT_TTL_SECONDS = 3 * 24 * 60 * 60


class SnapshotStore:
    def __init__(
        self,
        base_dir: Path | None = None,
        ttl_seconds: int = DEFAULT_SNAPSHOT_TTL_SECONDS,
        now: Callable[[], float] | None = None,
        namespace: str | None = None,
    ):
        self.base_dir = base_dir or default_data_dir() / "snapshots"
        self.ttl_seconds = ttl_seconds
        self.now = now or time.time
        self.namespace = namespace

    def ensure(self, key: str, loader: Callable[[], Any], refresh: bool = False) -> dict[str, Any]:
        cached = self.read(key, refresh=refresh)
        if cached is not None:
            return cached
        return self.write(key, loader(), hit=False)

    def read(self, key: str, refresh: bool = False) -> dict[str, Any] | None:
        if refresh:
            return None
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if self._is_stale(payload):
            return None
        payload["cache"] = self._cache_info(key, payload, hit=True)
        return payload

    def write(self, key: str, data: Any, hit: bool = False) -> dict[str, Any]:
        created_at = int(self.now())
        payload = {
            "version": 1,
            "key": key,
            "created_at": created_at,
            "ttl_seconds": self.ttl_seconds,
            "data": data,
        }
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["cache"] = self._cache_info(key, payload, hit=hit)
        return payload

    def _is_stale(self, payload: dict[str, Any]) -> bool:
        created_at = int(payload.get("created_at") or 0)
        ttl_seconds = int(payload.get("ttl_seconds") or self.ttl_seconds)
        return created_at + ttl_seconds <= int(self.now())

    def _cache_info(self, key: str, payload: dict[str, Any], hit: bool) -> dict[str, Any]:
        created_at = int(payload.get("created_at") or 0)
        ttl_seconds = int(payload.get("ttl_seconds") or self.ttl_seconds)
        return {
            "key": key,
            "hit": hit,
            "created_at": created_at,
            "expires_at": created_at + ttl_seconds,
            "ttl_seconds": ttl_seconds,
        }

    def _path(self, key: str) -> Path:
        namespaced_key = f"{self.namespace}_{key}" if self.namespace else key
        safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", namespaced_key).strip("_") or "snapshot"
        return self.base_dir / f"{safe_key}.json"
