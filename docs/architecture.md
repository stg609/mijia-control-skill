# Architecture

`mijia-control-skill` is split into two layers: an Agent Skill and a local runtime.

## Layers

### Agent Skill

Path:

```text
skills/controlling-mijia-smart-home/
```

The Skill contains instructions for agents. It tells an agent when to use Mijia control, how to discover devices, when to ask for confirmation, and which `mijiactl` commands are allowed.

The Skill does not contain account credentials, device credentials, or direct Python API snippets. Agents should not read `auth.json` and should not call `mijiaAPI` directly.

### Runtime CLI

Path:

```text
mijiactl/
```

`mijiactl` is the deterministic local execution layer. It wraps third-party Mijia APIs and exposes stable JSON responses:

```json
{"ok": true, "error": null, "data": {}}
```

or:

```json
{"ok": false, "error": {"code": "ERROR_CODE", "message": "...", "data": {}}, "data": null}
```

Agents branch on `ok` and `error.code` instead of parsing prose.

## Runtime Components

### `MijiaClient`

File:

```text
mijiactl/client.py
```

Responsibilities:

- Load `mijiaAPI` with the configured auth file.
- List devices, homes, and scenes.
- Normalize device/home/scene shapes into stable dictionaries.
- Read and set MIoT properties.
- Execute MIoT actions through `run_action`.
- Trigger scene execution when confirmed.

### `CapabilityStore`

File:

```text
mijiactl/capabilities.py
```

Responsibilities:

- Cache model capabilities under `~/.config/mijiactl/capabilities/`.
- Normalize MIoT property/action shapes into `name -> siid/piid/aiid` mappings.
- Resolve user-facing property/action names such as `switch-status` or `start-wash`.
- Support refresh when firmware or MIoT metadata changes.

### `CommandPolicy`

File:

```text
mijiactl/policy.py
```

Responsibilities:

- Reject offline devices.
- Reject disabled devices/actions from user policy.
- Require confirmation tokens for high-risk operations.
- Prevent ambiguous fuzzy device matches from executing automatically.

### Auth and Config

Files:

```text
mijiactl/auth.py
mijiactl/config.py
```

Default locations:

```text
~/.config/mijiactl/auth.json
~/.config/mijiactl/config.json
```

`mijiactl doctor`, `setup`, and `version` report paths and health status. Auth output is redacted: it reports only presence, JSON validity, key count, and fixed required-key presence.

## Control Flow

Typical device control:

1. Agent runs `mijiactl doctor` or `mijiactl setup`.
2. Agent follows `data.next_steps`.
3. Agent runs `mijiactl devices --json`.
4. Agent selects exactly one device, or asks the user to choose.
5. Agent runs `mijiactl info --model <model> --json` if capability data is not cached.
6. Agent calls `get`, `set`, or `action`.
7. `CommandPolicy` blocks, confirms, or allows the request.
8. `MijiaClient` executes the cloud call through `mijiaAPI`.
9. `mijiactl` returns structured JSON.

Scene control:

1. Agent runs `mijiactl homes --json`.
2. Agent runs `mijiactl scene list --home-id <home_id>`.
3. Scene execution requires `--confirm scene:<scene_id>`.

## Distribution

The repository is not copied wholesale into a user's skills directory.

User installation has two parts:

- `npx skills add ... --skill controlling-mijia-smart-home` installs only the Skill.
- `scripts/install-mijiactl.ps1` downloads the latest `mijiactl-windows-x64.exe` release asset to `~/.mijiactl/bin`.

Development installation can still use:

```powershell
uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"
```

## Why Actions Matter

Many MIoT devices expose both properties and actions. A washer can have an `on` or standby-like property, but starting a washing program is an action such as `start-wash`. The Skill explicitly tells agents not to treat `set on=true` as equivalent to starting an appliance program.
