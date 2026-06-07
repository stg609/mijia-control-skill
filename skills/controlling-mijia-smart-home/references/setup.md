# Setup

## User Fast Path

After the repository is published, most users should need only the Skill install plus runtime setup:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

Then install the runtime from GitHub Releases:

```powershell
irm https://raw.githubusercontent.com/stg609/mijia-control-skill/main/scripts/install-mijiactl.ps1 | iex
```

If the maintainer publishes a dedicated bootstrap script, this one PowerShell command installs both pieces:

```powershell
irm https://raw.githubusercontent.com/stg609/mijia-control-skill/main/install.ps1 | iex
```

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
mijiactl doctor
mijiactl devices --json
```

`mijiactl setup` and `mijiactl doctor` return JSON with `data.next_steps`. Agents should follow those steps instead of guessing what is missing.

## Agent Recovery

- If `mijiactl` is missing, ask the user to approve runtime installation from GitHub Releases.
- If `mijiaAPI` is missing, reinstall with the `[mijia]` extra.
- If auth is missing or expired, run `mijiactl login` and wait for the user to scan the QR code.
- If policy config is missing, run `mijiactl config init`.
- If device capability lookup fails, retry `mijiactl info --model <model> --refresh --json` once before reporting the failure.
