from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


class MijiaError(Exception):
    def __init__(self, code: str, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}

    def to_payload(self) -> dict[str, Any]:
        return {"ok": False, "error": {"code": self.code, "message": self.message, "data": self.data}}


@dataclass(frozen=True)
class Confirmation:
    required: bool
    token: str | None = None


class CommandPolicy:
    HIGH_RISK_TERMS = (
        "lock",
        "camera",
        "security",
        "washer",
        "wash",
        "air-conditioner",
        "air_conditioner",
        "airconditioner",
        "ac",
    )
    HIGH_RISK_ACTIONS = ("start", "run", "start-wash", "start_wash", "wash", "unlock", "record")

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def resolve_device(self, devices: list[Any], query: str) -> Any:
        matches = [
            device
            for device in devices
            if query == getattr(device, "did", "")
            or query.lower() in getattr(device, "name", "").lower()
            or query.lower() in getattr(device, "model", "").lower()
        ]
        if not matches:
            raise MijiaError("DEVICE_NOT_FOUND", f"No device matched '{query}'.")
        if len(matches) > 1:
            raise MijiaError(
                "AMBIGUOUS_DEVICE",
                f"Multiple devices matched '{query}'.",
                {"candidates": [device.to_dict() for device in matches]},
            )
        return matches[0]

    def ensure_device_can_execute(self, device: Any) -> None:
        if self._matches_any(device, self.config.get("disabled_devices", [])):
            raise MijiaError(
                "POLICY_BLOCKED",
                f"Device '{getattr(device, 'name', device)}' is disabled by policy.",
                {"device": getattr(device, "did", None)},
            )
        if not getattr(device, "online", False):
            raise MijiaError("DEVICE_OFFLINE", f"Device '{getattr(device, 'name', device)}' is offline.")

    def ensure_action_allowed(self, device: Any, action: str, confirm: str | None) -> None:
        if self._matches_any(device, self.config.get("disabled_actions", []), action=action):
            raise MijiaError(
                "POLICY_BLOCKED",
                f"Action '{action}' on '{device.name}' is disabled by policy.",
                {"device": getattr(device, "did", None), "action": action},
            )
        confirmation = self.confirmation_for(device, action)
        if confirmation.required and confirm != confirmation.token:
            raise MijiaError(
                "CONFIRMATION_REQUIRED",
                f"Action '{action}' on '{device.name}' requires confirmation.",
                {"confirm": confirmation.token},
            )

    def confirmation_for(self, device: Any, action: str) -> Confirmation:
        if self._matches_any(device, self.config.get("confirm_required", []), action=action):
            return Confirmation(required=True, token=self._confirmation_token(device, action))
        haystack = f"{getattr(device, 'name', '')} {getattr(device, 'model', '')} {action}".lower()
        risky_device = any(term in haystack for term in self.HIGH_RISK_TERMS)
        risky_action = any(term in action.lower() for term in self.HIGH_RISK_ACTIONS)
        if not (risky_device or risky_action):
            return Confirmation(required=False)
        return Confirmation(required=True, token=self._confirmation_token(device, action))

    def ensure_scene_allowed(self, scene_id: str, home_id: str, confirm: str | None) -> None:
        token = f"scene:{scene_id}"
        if confirm != token:
            raise MijiaError(
                "CONFIRMATION_REQUIRED",
                f"Running scene '{scene_id}' requires confirmation.",
                {"confirm": token, "scene_id": scene_id, "home_id": home_id},
            )

    def _confirmation_token(self, device: Any, action: str) -> str:
        if action in {"unlock", "record"}:
            return hashlib.sha256(f"{device.did}:{action}".encode("utf-8")).hexdigest()[:8]
        return action

    def _matches_any(self, device: Any, patterns: list[dict[str, Any]], action: str | None = None) -> bool:
        return any(self._matches_pattern(device, pattern, action=action) for pattern in patterns)

    def _matches_pattern(self, device: Any, pattern: dict[str, Any], action: str | None = None) -> bool:
        if "did" in pattern and str(pattern["did"]) != str(getattr(device, "did", "")):
            return False
        if "name" in pattern and str(pattern["name"]).lower() not in str(getattr(device, "name", "")).lower():
            return False
        if "model" in pattern and str(pattern["model"]).lower() not in str(getattr(device, "model", "")).lower():
            return False
        if "action" in pattern and action is None:
            return False
        if "action" in pattern and str(pattern["action"]).lower() not in str(action).lower():
            return False
        return any(key in pattern for key in ("did", "name", "model", "action"))
