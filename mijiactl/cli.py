from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable

from . import __version__
from .auth import auth_cache_namespace, auth_status
from .capabilities import CapabilityStore
from .client import Device, MijiaClient, login_auth
from .config import default_config_dir, default_config_path, load_config, write_default_config
from .policy import CommandPolicy, MijiaError
from .snapshots import SnapshotStore
from .values import parse_value


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise MijiaError("ARGUMENT_ERROR", message)


def success(data: dict[str, Any] | list[Any] | str | None = None) -> str:
    return json.dumps({"ok": True, "error": None, "data": data}, ensure_ascii=False)


def failure(exc: MijiaError) -> str:
    return json.dumps(exc.to_payload(), ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="mijiactl")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)

    sub.add_parser("doctor")
    sub.add_parser("setup")
    sub.add_parser("version")
    sub.add_parser("login")
    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True, parser_class=JsonArgumentParser)
    config_sub.add_parser("init")
    config_sub.add_parser("show")
    devices = sub.add_parser("devices")
    devices.add_argument("--json", action="store_true")
    devices.add_argument("--refresh", action="store_true")
    homes = sub.add_parser("homes")
    homes.add_argument("--json", action="store_true")
    homes.add_argument("--refresh", action="store_true")

    info = sub.add_parser("info")
    info.add_argument("--model", required=True)
    info.add_argument("--refresh", action="store_true")
    info.add_argument("--json", action="store_true")

    get = sub.add_parser("get")
    get.add_argument("--did", required=True)
    get.add_argument("--prop", required=True)

    set_cmd = sub.add_parser("set")
    set_cmd.add_argument("--did", required=True)
    set_cmd.add_argument("--prop", required=True)
    set_cmd.add_argument("--value", required=True)
    set_cmd.add_argument("--confirm")

    action = sub.add_parser("action")
    action.add_argument("--did", required=True)
    action.add_argument("--action", required=True)
    action.add_argument("--arg", action="append", default=[])
    action.add_argument("--confirm")

    scene = sub.add_parser("scene")
    scene_sub = scene.add_subparsers(dest="scene_command", required=True, parser_class=JsonArgumentParser)
    scene_list = scene_sub.add_parser("list")
    scene_list.add_argument("--home-id")
    scene_list.add_argument("--refresh", action="store_true")
    scene_run = scene_sub.add_parser("run")
    scene_run.add_argument("--id", required=True)
    scene_run.add_argument("--home-id", required=True)
    scene_run.add_argument("--confirm")
    return parser


def run_cli(
    argv: list[str],
    client: MijiaClient | None = None,
    store: CapabilityStore | None = None,
    snapshots: SnapshotStore | None = None,
    policy: CommandPolicy | None = None,
    auth_path: Any | None = None,
    config_path: Any | None = None,
) -> str:
    store = store or CapabilityStore()
    snapshots = snapshots or SnapshotStore(namespace=auth_cache_namespace(auth_path))
    policy = policy or CommandPolicy(load_config(config_path))
    client_instance = client

    def get_client() -> MijiaClient:
        nonlocal client_instance
        if client_instance is None:
            client_instance = MijiaClient(auth_path=auth_path)
        return client_instance

    try:
        args = build_parser().parse_args(argv)
        if args.command == "doctor":
            return success(_doctor_payload(auth_path, config_path))
        if args.command == "setup":
            return success(_setup_payload(auth_path, config_path))
        if args.command == "version":
            return success(_version_payload(auth_path, config_path))
        if args.command == "login":
            return login_auth(auth_path)
        if args.command == "config" and args.config_command == "init":
            path = write_default_config(config_path)
            return success({"config": {"path": str(path), "created_or_exists": True}})
        if args.command == "config" and args.config_command == "show":
            return success({"config": {"path": str(config_path or default_config_path()), "data": load_config(config_path)}})
        if args.command == "devices":
            snapshot = _device_snapshot(get_client, snapshots, refresh=args.refresh)
            return success({"devices": snapshot["data"], "cache": snapshot["cache"]})
        if args.command == "homes":
            snapshot = snapshots.ensure("homes", lambda: get_client().homes(), refresh=args.refresh)
            return success({"homes": snapshot["data"], "cache": snapshot["cache"]})
        if args.command == "info":
            if not args.refresh:
                cached = store.get_model(args.model)
                if cached is not None:
                    return success(cached)
            return success(store.ensure_model(args.model, get_client(), refresh=args.refresh))
        if args.command == "get":
            device = _device_by_did(get_client, snapshots, args.did)
            policy.ensure_device_can_execute(device)
            prop = _resolve_property(store, get_client, device.model, args.prop)
            return success({"value": get_client().get_property(device.did, prop["siid"], prop["piid"])})
        if args.command == "set":
            device = _device_by_did(get_client, snapshots, args.did)
            policy.ensure_device_can_execute(device)
            policy.ensure_action_allowed(device, f"set-{args.prop}", args.confirm)
            prop = _resolve_property(store, get_client, device.model, args.prop)
            result = get_client().set_property(device.did, prop["siid"], prop["piid"], parse_value(args.value))
            return success({"result": result})
        if args.command == "action":
            device = _device_by_did(get_client, snapshots, args.did)
            policy.ensure_device_can_execute(device)
            policy.ensure_action_allowed(device, args.action, args.confirm)
            action = _resolve_action(store, get_client, device.model, args.action)
            result = get_client().run_action(device.did, action["siid"], action["aiid"], [parse_value(value) for value in args.arg])
            return success({"result": result})
        if args.command == "scene" and args.scene_command == "list":
            snapshot = snapshots.ensure(_scene_snapshot_key(args.home_id), lambda: get_client().scenes(args.home_id), refresh=args.refresh)
            return success({"scenes": snapshot["data"], "cache": snapshot["cache"]})
        if args.command == "scene" and args.scene_command == "run":
            policy.ensure_scene_allowed(args.id, args.home_id, args.confirm)
            return success({"result": get_client().run_scene(args.id, args.home_id)})
        raise MijiaError("UNKNOWN_COMMAND", "Unknown command.")
    except MijiaError as exc:
        return failure(exc)
    except Exception as exc:
        return failure(MijiaError("UNEXPECTED_ERROR", str(exc)))


def main() -> None:
    print(run_cli(sys.argv[1:]))


def _version_payload(auth_path: Any | None, config_path: Any | None) -> dict[str, Any]:
    return {
        "name": "mijiactl",
        "version": __version__,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "config_dir": str(default_config_dir()),
        "auth_path": str(auth_path or auth_status(auth_path)["path"]),
        "config_path": str(config_path or default_config_path()),
    }


def _doctor_payload(auth_path: Any | None, config_path: Any | None) -> dict[str, Any]:
    auth = auth_status(auth_path)
    next_steps = []
    if not auth.get("present"):
        next_steps.append("mijiactl login")
    elif auth.get("valid_json") is False:
        next_steps.append("delete or replace invalid auth.json, then run mijiactl login")
    if not _config_path(config_path).exists():
        next_steps.append("mijiactl config init")
    if not next_steps:
        next_steps.append("mijiactl devices --json")
    return {
        "python": "ok",
        "mijiaapi": "deferred",
        "auth": auth,
        "config": _config_status(config_path),
        "next_steps": next_steps,
    }


def _setup_payload(auth_path: Any | None, config_path: Any | None) -> dict[str, Any]:
    auth = auth_status(auth_path)
    next_steps = []
    if not auth.get("present") or auth.get("valid_json") is False:
        next_steps.append("mijiactl login")
    if not _config_path(config_path).exists():
        next_steps.append("mijiactl config init")
    next_steps.append("mijiactl devices --json")
    return {
        "install": {
            "recommended": "Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression",
            "development": "uv tool install \"mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git\"",
            "local": "uv tool install --editable .[mijia]",
        },
        "auth": auth,
        "config": _config_status(config_path),
        "next_steps": next_steps,
    }


def _config_status(config_path: Any | None) -> dict[str, Any]:
    path = _config_path(config_path)
    return {"path": str(path), "present": path.exists()}


def _config_path(config_path: Any | None):
    return config_path or default_config_path()


def _device_snapshot(get_client: Callable[[], MijiaClient], snapshots: SnapshotStore, refresh: bool = False) -> dict[str, Any]:
    return snapshots.ensure("devices", lambda: [device.to_dict() for device in get_client().devices()], refresh=refresh)


def _device_by_did(get_client: Callable[[], MijiaClient], snapshots: SnapshotStore, did: str) -> Device:
    snapshot = _device_snapshot(get_client, snapshots)
    for item in snapshot["data"]:
        device = Device.from_dict(item)
        if device.did == did:
            return device
    raise MijiaError("DEVICE_NOT_FOUND", f"No device with did '{did}'. Run `mijiactl devices --refresh --json` if the device list changed.")


def _resolve_property(store: CapabilityStore, get_client: Callable[[], MijiaClient], model: str, prop_name: str) -> dict[str, Any]:
    try:
        return store.resolve_property(model, prop_name)
    except MijiaError as exc:
        if exc.code != "CAPABILITY_NOT_CACHED":
            raise
        store.ensure_model(model, get_client())
        return store.resolve_property(model, prop_name)


def _resolve_action(store: CapabilityStore, get_client: Callable[[], MijiaClient], model: str, action_name: str) -> dict[str, Any]:
    try:
        return store.resolve_action(model, action_name)
    except MijiaError as exc:
        if exc.code != "CAPABILITY_NOT_CACHED":
            raise
        store.ensure_model(model, get_client())
        return store.resolve_action(model, action_name)


def _scene_snapshot_key(home_id: str | None) -> str:
    return f"scenes_{home_id or 'all'}"


if __name__ == "__main__":
    main()
