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
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

Install the latest `mijiactl.exe` from GitHub Releases, then initialize:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression; mijiactl setup; mijiactl login; mijiactl config init
```

`mijiactl login` prints a QR code. Scan it with the Mijia app. Auth is stored at `~/.config/mijiactl/auth.json`; command output never prints token values.

Check the installed runtime version:

```powershell
mijiactl version
```

The command above is a global install. It explicitly targets the agents that support global installation:

`Claude Code`, `OpenClaw`, `Cline`, `Codex`, `Cursor`, `GitHub Copilot`, `Kiro CLI`, `Lingma`, `OpenCode`, `Qwen Code`, `Trae CN`, and `Windsurf`.

PromptScript is intentionally not in the default global target list because the current `skills` CLI reports `PromptScript does not support global skill installation`.

## Examples

List devices for an agent or script:

```powershell
mijiactl devices --json
```

Device, home, and scene lists are cached for 3 days by default. Force a rediscovery after renaming, adding, removing, or moving devices:

```powershell
mijiactl devices --refresh --json
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

Run a MIoT action with input parameters, such as asking a XiaoAI speaker to speak text:

```powershell
mijiactl info --model xiaomi.wifispeaker.lx06 --json
mijiactl action --did <did> --action play-text --arg "I am codex"
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
- Action execution through `run_action`, including ordered MIoT action inputs with repeated `--arg`.
- Scene listing and confirmed scene execution.
- User safety policy with disabled devices/actions and confirmation rules.

## Common Commands

```powershell
mijiactl version
mijiactl doctor
mijiactl setup
mijiactl login
mijiactl config init
mijiactl devices --json
mijiactl devices --refresh --json
mijiactl homes --json
mijiactl homes --refresh --json
mijiactl info --model <model> --json
mijiactl get --did <did> --prop <name>
mijiactl set --did <did> --prop <name> --value <value>
mijiactl action --did <did> --action <name>
mijiactl action --did <did> --action <name> --arg <value>
mijiactl scene list --home-id <home_id>
mijiactl scene list --home-id <home_id> --refresh
```

Use one `--arg` per action input in the same order shown by `mijiactl info --model <model> --json`. Values use the same parser as `set --value`, so `true`, `false`, integers, and floats are converted before calling MIoT.

`devices`, `homes`, and `scene list` include a small `data.cache` object with `hit`, `created_at`, and `expires_at`. Normal control commands also use the fresh device snapshot internally, so agents do not need to rediscover devices before every operation.

## Updating

Update the Agent Skill by rerunning the same `skills add` command:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

Update the `mijiactl` runtime to the latest GitHub Release:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression
mijiactl version
```

If you installed from source for development, update with:

```powershell
uv tool upgrade mijiactl
```

Auth and policy files are stored under `~/.config/mijiactl` and are not removed by updates.

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

For users who prefer one PowerShell command, the bootstrap script installs both the Skill and the latest Release build of `mijiactl.exe`. Inspect the script first if you do not pipe remote scripts directly into PowerShell:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/install.ps1 | Invoke-Expression
```

Add `-Login` if running the script from a local checkout:

```powershell
.\install.ps1 -Login
```

Use `-Agents` to override the default global target list from the bootstrap script. Use `-UseSourceRuntime` only for development installs from source.

If your shell does not provide the `irm` alias, use `Invoke-RestMethod` as shown above. If script piping is blocked by policy, download first and run locally:

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 -OutFile install-mijiactl.ps1
.\install-mijiactl.ps1
```

Manual install is also supported: download `mijiactl-windows-x64.exe` from the latest GitHub Release, rename it to `mijiactl.exe`, place it in `~/.mijiactl/bin`, and add that directory to your user `Path`.

## Runtime Distribution

End users do not need to copy this repository into their skills directory. The intended distribution is:

- Agent instructions: installed from `skills/controlling-mijia-smart-home` by `npx skills add`.
- Runtime: `mijiactl-windows-x64.exe` downloaded from GitHub Releases into `~/.mijiactl/bin`.
- Development fallback: `uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"`.

## Implementation

See [docs/architecture.md](docs/architecture.md) for the runtime design, control flow, safety policy, capability cache, and release packaging.

This project builds on the community around Mijia automation. Thanks to:

- [`Do1e/mijia-api`](https://github.com/Do1e/mijia-api), published as `mijiaAPI`, for the underlying Python Mijia API.
- [`moneshvenkul/mijia-skills`](https://github.com/moneshvenkul/mijia-skills) for earlier Agent Skill-style Mijia organization.
- [`ssttkkl/mijia-skill`](https://github.com/ssttkkl/mijia-skill) and the related MIoT action-control article for clarifying why devices such as washers require MIoT actions.

## License

This repository is licensed as `GPL-3.0-or-later`. The direct runtime dependency `mijiaAPI==3.0.5` is listed on PyPI as `GPL-3.0-or-later`, so the project is not MIT-licensed. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Repository Layout

```text
mijiactl/                                Python package for the mijiactl command
scripts/                                Release install/build helpers
skills/controlling-mijia-smart-home/     Agent Skill installed by npx skills add
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
- Build the Windows executable locally with `.\scripts\build-release.ps1`, or push a `v*` tag and let GitHub Actions publish `mijiactl-windows-x64.exe`.
- Confirm the wheel contains `mijiactl`, `skills/controlling-mijia-smart-home`, `README.md`, `README.zh-CN.md`, and `install.ps1`.
- Test the documented install path from a clean machine or temporary user profile.

## Maintainer Evals

Regression prompts for agents are in `evals/evals.json`. They cover first-time setup, device listing, safe light control, high-risk confirmation, washer action behavior, and parameterized speaker TTS actions.

## Maintainer Notes

- Keep `skills/controlling-mijia-smart-home/SKILL.md` concise. Put setup and safety details in `references/`.
- Keep runtime code under `mijiactl`; reserve `skills/controlling-mijia-smart-home` for the Agent Skill.
- Do not expose auth token values in tests, docs, or command output.
- Add tests for every policy or command behavior change.
- Prefer stable JSON output over prose so agents can branch on `ok` and `error.code`.
