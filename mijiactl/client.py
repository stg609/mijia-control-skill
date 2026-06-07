from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .auth import auth_status, default_auth_path
from .miot_spec import fetch_model_spec
from .policy import MijiaError


@dataclass(frozen=True)
class Device:
    did: str
    name: str
    model: str
    online: bool
    room: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"did": self.did, "name": self.name, "model": self.model, "online": self.online, "room": self.room}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Device":
        return cls(
            did=str(data.get("did") or ""),
            name=str(data.get("name") or data.get("did") or "unknown"),
            model=str(data.get("model") or ""),
            online=bool(data.get("online", False)),
            room=data.get("room"),
        )


class MijiaClient:
    def __init__(self, api: Any | None = None, auth_path: Path | None = None):
        self.api = api if api is not None else self._load_real_api(auth_path)

    def devices(self) -> list[Device]:
        raw_devices = list(self._call_first("get_devices_list", "get_devices") or [])
        shared = self._call_optional("get_shared_devices_list")
        if shared:
            raw_devices.extend(shared)
        return [self._normalize_device(item) for item in raw_devices]

    def device_by_did(self, did: str) -> Device:
        for device in self.devices():
            if device.did == did:
                return device
        raise MijiaError("DEVICE_NOT_FOUND", f"No device with did '{did}'.")

    def homes(self) -> list[dict[str, Any]]:
        if hasattr(self.api, "get_homes_list"):
            return [self._normalize_home(home) for home in list(self.api.get_homes_list() or [])]
        return []

    def get_device_info(self, model: str) -> dict[str, Any]:
        info = None
        try:
            info = self._call_first(("get_device_info", "get_spec"), model)
        except Exception:
            try:
                info = self._get_device_info_from_package(model)
            except Exception:
                try:
                    info = fetch_model_spec(model)
                except Exception as exc:
                    raise MijiaError(
                        "CAPABILITY_LOOKUP_FAILED",
                        f"Capability lookup failed for model '{model}': {exc}",
                    ) from exc
        if not info:
            try:
                info = fetch_model_spec(model)
            except Exception as exc:
                raise MijiaError(
                    "CAPABILITY_LOOKUP_FAILED",
                    f"Capability lookup failed for model '{model}': {exc}",
                ) from exc
        return info

    def get_property(self, did: str, siid: int, piid: int) -> Any:
        payload = {"did": did, "siid": siid, "piid": piid}
        if hasattr(self.api, "get_devices_prop"):
            return self.api.get_devices_prop([payload])
        return self._call_first(("get_prop", "get_property"), payload)

    def set_property(self, did: str, siid: int, piid: int, value: Any) -> Any:
        payload = {"did": did, "siid": siid, "piid": piid, "value": value}
        if hasattr(self.api, "set_devices_prop"):
            return self.api.set_devices_prop([payload])
        return self._call_first(("set_prop", "set_property"), payload)

    def run_action(self, did: str, siid: int, aiid: int, args: list[Any] | None = None) -> Any:
        payload = {"did": did, "siid": siid, "aiid": aiid}
        if args:
            payload["in"] = args
        return self._call_first(("run_action",), payload)

    def scenes(self, home_id: str | None = None) -> list[dict[str, Any]]:
        if hasattr(self.api, "get_scenes_list"):
            return [self._normalize_scene(scene) for scene in list(self.api.get_scenes_list(home_id) or [])]
        return [self._normalize_scene(scene) for scene in list(self._call_first(("get_scenes", "get_scene_list"), home_id) or [])]

    def run_scene(self, scene_id: str, home_id: str) -> Any:
        if hasattr(self.api, "run_scene"):
            return self.api.run_scene(scene_id, home_id)
        return self._call_first(("execute_scene",), scene_id, home_id)

    def _load_real_api(self, auth_path: Path | None = None) -> Any:
        try:
            try:
                from mijiaapi import mijiaAPI  # type: ignore
            except Exception:
                from mijiaAPI import mijiaAPI  # type: ignore
        except Exception as exc:
            raise MijiaError("DEPENDENCY_MISSING", "Install the pinned mijiaapi dependency before controlling devices.") from exc
        resolved_auth_path = auth_path or default_auth_path()
        status = auth_status(resolved_auth_path)
        if not status.get("present"):
            raise MijiaError("AUTH_MISSING", f"Authentication file not found at '{resolved_auth_path}'.")
        if status.get("valid_json") is False:
            raise MijiaError("AUTH_INVALID", "Authentication file is not valid JSON.")
        api = mijiaAPI(str(resolved_auth_path))
        if hasattr(api, "available") and not api.available:
            raise MijiaError("AUTH_EXPIRED", "Mijia authentication is unavailable or expired.")
        return api

    def _call_first(self, *names_and_args: Any) -> Any:
        if names_and_args and isinstance(names_and_args[0], tuple):
            names = list(names_and_args[0])
            args = list(names_and_args[1:])
        else:
            args = []
            names = []
            for item in names_and_args:
                if isinstance(item, str):
                    names.append(item)
                else:
                    args.append(item)
        for name in names:
            fn = getattr(self.api, name, None)
            if fn:
                return fn(*args)
        raise MijiaError("API_METHOD_MISSING", f"None of these API methods exist: {', '.join(names)}.")

    def _call_optional(self, name: str) -> Any:
        fn = getattr(self.api, name, None)
        return fn() if fn else None

    def _normalize_device(self, item: dict[str, Any]) -> Device:
        return Device(
            did=str(item.get("did") or item.get("id") or ""),
            name=str(item.get("name") or item.get("desc") or item.get("did") or "unknown"),
            model=str(item.get("model") or ""),
            online=bool(item.get("online", item.get("isOnline", item.get("is_online", False)))),
            room=item.get("room") or item.get("room_name"),
        )

    def _normalize_home(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(item.get("id") or ""),
            "name": item.get("name"),
            "rooms": [
                {"id": str(room.get("id") or ""), "name": room.get("name"), "dids": room.get("dids", [])}
                for room in item.get("roomlist", [])
            ],
        }

    def _normalize_scene(self, item: dict[str, Any]) -> dict[str, Any]:
        scene_id = item.get("scene_id") or item.get("id")
        return {
            "scene_id": str(scene_id or ""),
            "name": item.get("name"),
            "home_id": str(item.get("home_id") or ""),
            "enable": item.get("enable"),
        }

    def _get_device_info_from_package(self, model: str) -> dict[str, Any]:
        try:
            from mijiaAPI.devices import get_device_info  # type: ignore
        except Exception as exc:
            raise MijiaError("API_METHOD_MISSING", "No get_device_info provider is available.") from exc
        return get_device_info(model)


def login_auth(auth_path: Path | None = None, api_factory: Any | None = None) -> str:
    from .cli import failure, success

    resolved_auth_path = auth_path or default_auth_path()
    try:
        factory = api_factory or _load_mijiaapi_factory()
        api = factory(str(resolved_auth_path))
        api.login()
        return success({"auth": auth_status(resolved_auth_path)})
    except MijiaError as exc:
        return failure(exc)


def _load_mijiaapi_factory() -> Any:
    try:
        try:
            from mijiaapi import mijiaAPI  # type: ignore
        except Exception:
            from mijiaAPI import mijiaAPI  # type: ignore
    except Exception as exc:
        raise MijiaError("DEPENDENCY_MISSING", "Install the pinned mijiaAPI dependency before logging in.") from exc
    return mijiaAPI


class FakeMijiaApi:
    def __init__(
        self,
        devices: list[dict[str, Any]] | None = None,
        shared_devices: list[dict[str, Any]] | None = None,
        device_infos: dict[str, dict[str, Any]] | None = None,
    ):
        self._devices = devices or []
        self._shared_devices = shared_devices or []
        self._device_infos = device_infos or {}
        self.actions_run: list[dict[str, Any]] = []
        self.properties_set: list[dict[str, Any]] = []

    def get_devices_list(self) -> list[dict[str, Any]]:
        return self._devices

    def get_shared_devices_list(self) -> list[dict[str, Any]]:
        return self._shared_devices

    def get_device_info(self, model: str) -> dict[str, Any]:
        return self._device_infos[model]

    def run_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.actions_run.append(payload)
        return {"result": "ok"}

    def set_prop(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.properties_set.append(payload)
        return {"result": "ok"}
