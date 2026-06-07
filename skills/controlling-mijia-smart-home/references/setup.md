# Setup

## User Fast Path

After the repository is published, most users should need only the Skill install plus runtime setup:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g -y
```

Then install the runtime:

```powershell
uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"
```

If the maintainer publishes a dedicated bootstrap script, this one PowerShell command installs both pieces:

```powershell
irm https://raw.githubusercontent.com/stg609/mijia-control-skill/main/install.ps1 | iex
```

The runtime uses `~/.config/mijiactl`.

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

- If `mijiactl` is missing, ask the user to approve runtime installation with `uv tool install`.
- If `mijiaAPI` is missing, reinstall with the `[mijia]` extra.
- If auth is missing or expired, run `mijiactl login` and wait for the user to scan the QR code.
- If policy config is missing, run `mijiactl config init`.
- If device capability lookup fails, retry `mijiactl info --model <model> --refresh --json` once before reporting the failure.
