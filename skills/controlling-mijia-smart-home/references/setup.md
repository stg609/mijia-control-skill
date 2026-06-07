# Setup

## User Fast Path

After the repository is published, most users should need only the Skill install plus runtime setup:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

Then install the runtime from GitHub Releases:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression
```

If the maintainer publishes a dedicated bootstrap script, this one PowerShell command installs both pieces:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/install.ps1 | Invoke-Expression
```

If `Invoke-RestMethod` or script piping is blocked, download and run the installer explicitly:

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 -OutFile install-mijiactl.ps1
.\install-mijiactl.ps1
```

Manual install is also supported: download `mijiactl-windows-x64.exe` from the latest GitHub Release, rename it to `mijiactl.exe`, place it in `~/.mijiactl/bin`, and add that directory to the user `Path`.

The runtime uses `~/.config/mijiactl` for auth/config and installs the executable to `~/.mijiactl/bin` by default.

This is a global install. The command lists global-capable agent adapters explicitly so the installer does not target PromptScript, which currently does not support global installation.

## First Authorization

```powershell
mijiactl setup
mijiactl login
mijiactl config init
```

`mijiactl login` prints a QR code. Scan it with the Mijia app. Auth is stored at `~/.config/mijiactl/auth.json` for new installs.

Verify:

```powershell
mijiactl version
mijiactl doctor
mijiactl devices --json
```

`mijiactl setup` and `mijiactl doctor` return JSON with `data.next_steps`. Agents should follow those steps instead of guessing what is missing.

Device, home, and scene snapshots are cached for 3 days. Use refresh only when the user asks to rescan/sync, when a device was renamed/added/removed/moved, or when cached results look wrong:

```powershell
mijiactl devices --refresh --json
mijiactl homes --refresh --json
mijiactl scene list --home-id <home_id> --refresh
```

## Agent Recovery

- If `mijiactl` is missing, ask the user to approve runtime installation from GitHub Releases.
- If the user asks how to update, rerun `npx skills add ... --skill controlling-mijia-smart-home` for the Skill and rerun `scripts/install-mijiactl.ps1` for the runtime.
- If the user asks how to uninstall, use `uninstall.ps1` for Skill + runtime, or `scripts/uninstall-mijiactl.ps1` for runtime only.
- If the user asks what is installed, run `mijiactl version`.
- If `mijiaAPI` is missing, reinstall with the `[mijia]` extra.
- If auth is missing or expired, run `mijiactl login` and wait for the user to scan the QR code.
- If policy config is missing, run `mijiactl config init`.
- If device capability lookup fails, retry `mijiactl info --model <model> --refresh --json` once before reporting the failure.
- If device, home, room, or scene inventory looks stale, refresh the relevant snapshot instead of rerunning every discovery command repeatedly.

## Uninstall and Cleanup

Runtime-only uninstall keeps auth, policy, and cache data:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/uninstall-mijiactl.ps1 | Invoke-Expression
```

Skill + runtime uninstall:

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/uninstall.ps1 | Invoke-Expression
```

Complete cleanup deletes local auth, policy, capability cache, and snapshot cache:

```powershell
& ([ScriptBlock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/uninstall.ps1))) -PurgeData
```

Warn the user before `-PurgeData`: reinstalling after this requires `mijiactl login` and QR authorization again.

Manual cleanup paths:

- `~/.mijiactl/bin/mijiactl.exe`
- `~/.mijiactl`
- `~/.config/mijiactl`
- `controlling-mijia-smart-home` in each agent's skills directory, if the `skills` CLI cannot remove it automatically.
