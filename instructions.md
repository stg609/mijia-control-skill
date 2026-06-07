# Mijia Control Local Instructions

## Setup

Install the local package in editable mode when command entry points are needed:

```powershell
uv pip install -e ".[mijia]"
```

The optional dependency is pinned to `mijiaAPI==3.0.5`. The package is intentionally not imported during tests unless a real command needs Xiaomi access.

## Authentication

Store Xiaomi auth data at:

```text
~/.config/mijiactl/auth.json
```

or set:

```powershell
$env:MIJIA_AUTH_FILE="D:\path\to\auth.json"
```

The expected auth JSON is the dictionary returned by `mijiaLogin.QRlogin()` or an equivalent manual login flow. Do not paste this file into chat. `mijiactl doctor` reports only presence, JSON validity, key count, and fixed required-key presence.

Generate it with:

```powershell
uv run --extra mijia mijiactl login
```

The command prints a QR code in the terminal. Scan it with the Mijia app, using the same Xiaomi account that owns the devices. On success it writes `auth.json` to the path above and prints only redacted status JSON.

## Safety Config

Initialize:

```powershell
mijiactl config init
```

Edit:

```text
~/.config/mijiactl/config.json
```

Use `disabled_devices` for devices that must never be controlled. Use `confirm_required` for operations that require explicit approval.

## Commands

```powershell
mijiactl doctor
mijiactl setup
mijiactl login
mijiactl config init
mijiactl config show
mijiactl devices --json
mijiactl homes --json
mijiactl info --model <model> --json
mijiactl info --model <model> --refresh --json
mijiactl get --did <did> --prop <name>
mijiactl set --did <did> --prop <name> --value <value>
mijiactl action --did <did> --action <name>
mijiactl scene list --home-id <home_id>
mijiactl scene run --id <scene_id> --home-id <home_id>
```

Capabilities are cached under:

```text
~/.config/mijiactl/capabilities/<model>.json
```

Use `--refresh` when an action or property is missing or after firmware/app updates.

## Error Handling

Agents should branch on `error.code`, not message text:

- `AUTH_MISSING`: login has not been stored locally.
- `AUTH_EXPIRED`: stored login is not usable.
- `DEPENDENCY_MISSING`: install the pinned `mijiaAPI` dependency.
- `CAPABILITY_NOT_CACHED`: run `mijiactl info --model <model> --json`.
- `ACTION_NOT_FOUND`: refresh capabilities and retry only if the refreshed model lists the action.
- `PROPERTY_NOT_FOUND`: refresh capabilities and retry only if the refreshed model lists the property.
- `DEVICE_OFFLINE`: stop.
- `AMBIGUOUS_DEVICE`: ask the user to choose one candidate.
- `CONFIRMATION_REQUIRED`: ask the user before rerunning with `--confirm`.

## Washer Acceptance Rule

When the user says "启动洗衣机" or equivalent, do not use `set on=true` as the final operation. Use a discovered MIoT action such as `start-wash`, and require confirmation before execution.
