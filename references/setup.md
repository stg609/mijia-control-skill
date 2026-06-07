# Setup

Canonical copy: `skills/controlling-mijia-smart-home/references/setup.md`.

Use `mijiactl setup` first. If `mijiactl` is missing, install it:

```powershell
uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"
```

The canonical GitHub flow is:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g -y
```

Then authorize:

```powershell
mijiactl login
```

Scan the QR code with the Mijia app. Verify:

```powershell
mijiactl doctor
mijiactl devices --json
```
