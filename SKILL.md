---
name: controlling-mijia-smart-home
description: Compatibility entrypoint for the Controlling Mijia Smart Home Skill. Prefer installing the canonical skill at skills/controlling-mijia-smart-home with npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home.
---

# Controlling Mijia Smart Home

The canonical distributable Skill lives at `skills/controlling-mijia-smart-home`.

For GitHub distribution, install with:

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g -y
```

Then install the local runtime:

```powershell
uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"
```

After that, follow `skills/controlling-mijia-smart-home/SKILL.md`.
