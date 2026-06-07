# Mijia Control Skill

[简体中文](README.zh-CN.md) | English

Agent-friendly Xiaomi Mijia smart-home control with a safe local CLI runtime.

This repository contains two separate pieces:

- `skills/controlling-mijia-smart-home`: the installable Agent Skill for `npx skills add`.
- `mijiactl`: the Python package that provides the `mijiactl` command.

The split is intentional. The Skill teaches agents when and how to act; `mijiactl` performs the local, policy-checked Mijia operation and always returns stable JSON.

## Quick Start

Install the Agent Skill:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g -y
```

Install and initialize the runtime:

```powershell
uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"; mijiactl setup; mijiactl login; mijiactl config init
```

`mijiactl login` prints a QR code. Scan it with the Mijia app. Auth is stored at `~/.config/mijiactl/auth.json`; command output never prints token values.

## Examples

List devices for an agent or script:

```powershell
mijiactl devices --json
```

Turn on a light after inspecting its model capabilities:

```powershell
mijiactl info --model wlg.light.wy0a05 --json
mijiactl set --did <did> --prop switch-status --value true
```

Read the current value of a property:

```powershell
mijiactl get --did <did> --prop switch-status
```

Run a MIoT action such as starting a washer program. This is intentionally different from `set on=true`:

```powershell
mijiactl info --model <washer_model> --json
mijiactl action --did <did> --action start-wash --confirm start-wash
```

List and run a scene. Scene runs require confirmation by default:

```powershell
mijiactl homes --json
mijiactl scene list --home-id <home_id>
mijiactl scene run --id <scene_id> --home-id <home_id> --confirm scene:<scene_id>
```

## What Works

- QR login and redacted auth checks.
- Home, room, scene, and device listing.
- MIoT capability lookup with cache and JSON fallback.
- Property get/set.
- Action execution through `run_action`.
- Scene listing and confirmed scene execution.
- User safety policy with disabled devices/actions and confirmation rules.

## Common Commands

```powershell
mijiactl doctor
mijiactl setup
mijiactl login
mijiactl config init
mijiactl devices --json
mijiactl homes --json
mijiactl info --model <model> --json
mijiactl get --did <did> --prop <name>
mijiactl set --did <did> --prop <name> --value <value>
mijiactl action --did <did> --action <name>
mijiactl scene list --home-id <home_id>
```

Every command returns:

```json
{"ok": true, "error": null, "data": {}}
```

or:

```json
{"ok": false, "error": {"code": "ERROR_CODE", "message": "...", "data": {}}, "data": null}
```

## Safety Policy

Initialize policy:

```powershell
mijiactl config init
```

Edit:

```text
~/.config/mijiactl/config.json
```

Policy fields:

- `disabled_devices`: devices that must never be controlled.
- `disabled_actions`: actions/properties that must never execute.
- `confirm_required`: devices/actions requiring explicit approval.

By default, high-risk categories include locks, cameras, doorbells, scene runs, appliance starts, vacuum starts, and plug power changes.

## Bootstrap Alternative

For users who prefer one PowerShell command, the bootstrap script installs both the Skill and `mijiactl`. Inspect the script first if you do not pipe remote scripts directly into PowerShell:

```powershell
irm https://raw.githubusercontent.com/stg609/mijia-control-skill/main/install.ps1 | iex
```

Add `-Login` if running the script from a local checkout:

```powershell
.\install.ps1 -RepoUrl "git+https://github.com/stg609/mijia-control-skill.git" -Login
```

## Repository Layout

```text
mijiactl/                                Python package for the mijiactl command
skills/controlling-mijia-smart-home/     Agent Skill installed by npx skills add
references/               Compatibility docs pointing to the canonical Skill docs
evals/                    Maintainer regression prompts for agent behavior
tests/                    Unit and package tests
```

## Skill Distribution

The canonical skill directory is:

```text
skills/controlling-mijia-smart-home/
```

Export a standalone copy:

```powershell
mijiactl-export-skill --out dist/controlling-mijia-smart-home
```

Validate before publishing:

```powershell
uv run --no-project python -m unittest discover -s tests
uv run --no-project --with pyyaml python <path-to-quick_validate.py> skills/controlling-mijia-smart-home
```

## Publishing Checklist

- Run a secret scan for terms such as `serviceToken`, `ssecurity`, `passToken`, `userId`, and `deviceId`; only documentation and test fixtures should match.
- Confirm no repository-owner placeholders remain in install commands.
- Run unit tests: `uv run --no-project python -m unittest discover -s tests`.
- Validate the Skill directory with the target agent's Skill validator.
- Build the Python package: `uv build`.
- Confirm the wheel contains `mijiactl`, `skills/controlling-mijia-smart-home`, `README.md`, `README.zh-CN.md`, and `install.ps1`.
- Test the documented install path from a clean machine or temporary user profile.

## Maintainer Evals

Regression prompts for agents are in `evals/evals.json`. They cover first-time setup, device listing, safe light control, high-risk confirmation, and washer action behavior.

## Maintainer Notes

- Keep `skills/controlling-mijia-smart-home/SKILL.md` concise. Put setup and safety details in `references/`.
- Keep runtime code under `mijiactl`; reserve `skills/controlling-mijia-smart-home` for the Agent Skill.
- Do not expose auth token values in tests, docs, or command output.
- Add tests for every policy or command behavior change.
- Prefer stable JSON output over prose so agents can branch on `ok` and `error.code`.
