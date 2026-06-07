from __future__ import annotations

import argparse
import json
from typing import Any

from .auth import auth_status
from .capabilities import CapabilityStore
from .client import MijiaClient, login_auth
from .config import default_config_path, load_config, write_default_config
from .policy import CommandPolicy, MijiaError
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
    sub.add_parser("login")
    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True, parser_class=JsonArgumentParser)
    config_sub.add_parser("init")
    config_sub.add_parser("show")
    devices = sub.add_parser("devices")
    devices.add_argument("--json", action="store_true")
    homes = sub.add_parser("homes")
    homes.add_argument("--json", action="store_true")

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
    scene_run = scene_sub.add_parser("run")
    scene_run.add_argument("--id", required=True)
    scene_run.add_argument("--home-id", required=True)
    scene_run.add_argument("--confirm")
    return parser


def run_cli(
    argv: list[str],
    client: MijiaClient | None = None,
    store: CapabilityStore | None = None,
    policy: CommandPolicy | None = None,
    auth_path: Any | None = None,
    config_path: Any | None = None,
) -> str:
    store = store or CapabilityStore()
    policy = policy or CommandPolicy(load_config(config_path))

    try:
        args = build_parser().parse_args(argv)
        if args.command == "doctor":
            return success(_doctor_payload(auth_path, config_path))
        if args.command == "setup":
            return success(_setup_payload(auth_path, config_path))
        if args.command == "login":
            return login_auth(auth_path)
        if args.command == "config" and args.config_command == "init":
            path = write_default_config(config_path)
            return success({"config": {"path": str(path), "created_or_exists": True}})
        if args.command == "config" and args.config_command == "show":
            return success({"config": {"path": str(config_path or default_config_path()), "data": load_config(config_path)}})
        client = client or MijiaClient(auth_path=auth_path)
        if args.command == "devices":
            return success({"devices": [device.to_dict() for device in client.devices()]})
        if args.command == "homes":
            return success({"homes": client.homes()})
        if args.command == "info":
            return success(store.ensure_model(args.model, client, refresh=args.refresh))
        if args.command == "get":
            device = client.device_by_did(args.did)
            policy.ensure_device_can_execute(device)
            store.ensure_model(device.model, client)
            prop = store.resolve_property(device.model, args.prop)
            return success({"value": client.get_property(device.did, prop["siid"], prop["piid"])})
        if args.command == "set":
            device = client.device_by_did(args.did)
            policy.ensure_device_can_execute(device)
            policy.ensure_action_allowed(device, f"set-{args.prop}", args.confirm)
            store.ensure_model(device.model, client)
            prop = store.resolve_property(device.model, args.prop)
            result = client.set_property(device.did, prop["siid"], prop["piid"], parse_value(args.value))
            return success({"result": result})
        if args.command == "action":
            device = client.device_by_did(args.did)
            policy.ensure_device_can_execute(device)
            policy.ensure_action_allowed(device, args.action, args.confirm)
            store.ensure_model(device.model, client)
            action = store.resolve_action(device.model, args.action)
            result = client.run_action(device.did, action["siid"], action["aiid"], [parse_value(value) for value in args.arg])
            return success({"result": result})
        if args.command == "scene" and args.scene_command == "list":
            return success({"scenes": client.scenes(args.home_id)})
        if args.command == "scene" and args.scene_command == "run":
            policy.ensure_scene_allowed(args.id, args.home_id, args.confirm)
            return success({"result": client.run_scene(args.id, args.home_id)})
        raise MijiaError("UNKNOWN_COMMAND", "Unknown command.")
    except MijiaError as exc:
        return failure(exc)
    except Exception as exc:
        return failure(MijiaError("UNEXPECTED_ERROR", str(exc)))


def main() -> None:
    import sys

    print(run_cli(sys.argv[1:]))


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


if __name__ == "__main__":
    main()
