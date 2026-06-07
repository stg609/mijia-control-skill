from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .auth import default_data_dir
from .policy import MijiaError


class CapabilityStore:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or default_data_dir() / "capabilities"

    def get_model(self, model: str) -> dict[str, Any] | None:
        path = self._path_for(model)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_model(self, model: str, payload: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        normalized = self._normalize_model_info(model, payload)
        self._path_for(model).write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_model(self, model: str, client: Any, refresh: bool = False) -> dict[str, Any]:
        cached = None if refresh else self.get_model(model)
        if cached is not None:
            return cached
        payload = client.get_device_info(model)
        self.write_model(model, payload)
        return self.get_model(model) or {}

    def resolve_action(self, model: str, action_name: str) -> dict[str, Any]:
        info = self.get_model(model)
        if info is None:
            raise MijiaError("CAPABILITY_NOT_CACHED", f"Capabilities for '{model}' are not cached.")
        for action in info.get("actions", []):
            if self._same_name(action.get("name"), action_name):
                return {"name": action["name"], "siid": int(action["siid"]), "aiid": int(action["aiid"])}
        raise MijiaError("ACTION_NOT_FOUND", f"Action '{action_name}' was not found for '{model}'. Refresh capabilities.")

    def resolve_property(self, model: str, property_name: str) -> dict[str, Any]:
        info = self.get_model(model)
        if info is None:
            raise MijiaError("CAPABILITY_NOT_CACHED", f"Capabilities for '{model}' are not cached.")
        for prop in info.get("properties", []):
            if self._same_name(prop.get("name"), property_name):
                return {"name": prop["name"], "siid": int(prop["siid"]), "piid": int(prop["piid"])}
        raise MijiaError("PROPERTY_NOT_FOUND", f"Property '{property_name}' was not found for '{model}'. Refresh capabilities.")

    def _normalize_model_info(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        services = payload.get("services", [])
        if "actions" in payload or "properties" in payload:
            return {
                "model": payload.get("model", model),
                "properties": [self._normalize_property(prop) for prop in payload.get("properties", [])],
                "actions": [self._normalize_action(action) for action in payload.get("actions", [])],
            }

        properties: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        for service in services:
            siid = service.get("siid") or service.get("iid")
            for prop in service.get("properties", []):
                properties.append({"name": self._name(prop), "siid": siid, "piid": prop.get("piid") or prop.get("iid")})
            for action in service.get("actions", []):
                actions.append({"name": self._name(action), "siid": siid, "aiid": action.get("aiid") or action.get("iid")})
        return {"model": model, "properties": properties, "actions": actions, "raw": payload}

    def _path_for(self, model: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
        return self.base_dir / f"{safe}.json"

    def _same_name(self, left: str | None, right: str) -> bool:
        return self._slug(left or "") == self._slug(right)

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def _name(self, item: dict[str, Any]) -> str:
        desc = item.get("description") or item.get("desc") or item.get("name") or item.get("type") or "unknown"
        return self._slug(str(desc))

    def _normalize_property(self, prop: dict[str, Any]) -> dict[str, Any]:
        method = prop.get("method", {})
        normalized = dict(prop)
        if "siid" not in normalized and "siid" in method:
            normalized["siid"] = method["siid"]
        if "piid" not in normalized and "piid" in method:
            normalized["piid"] = method["piid"]
        return normalized

    def _normalize_action(self, action: dict[str, Any]) -> dict[str, Any]:
        method = action.get("method", {})
        normalized = dict(action)
        if "siid" not in normalized and "siid" in method:
            normalized["siid"] = method["siid"]
        if "aiid" not in normalized and "aiid" in method:
            normalized["aiid"] = method["aiid"]
        return normalized
