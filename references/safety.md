# Safety Policy

Canonical copy: `skills/controlling-mijia-smart-home/references/safety.md`.

Initialize policy:

```powershell
mijiactl config init
```

Edit `~/.config/mijiactl/config.json`.

Use `disabled_devices` for devices that must never be controlled, such as door locks or cameras.

Use `confirm_required` for operations that can change safety, security, power, appliance state, or run scenes.

Never bypass `POLICY_BLOCKED`. When `CONFIRMATION_REQUIRED` is returned, show the confirmation token to the user and wait for approval.
