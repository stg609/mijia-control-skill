# Device Catalog Hints

Canonical copy: `skills/controlling-mijia-smart-home/references/device_catalogs.md`.

This file is a human-maintained supplement. It is not the source of truth for execution.

Use dynamic capabilities from:

```powershell
mijiactl info --model <model> --json
```

## Washer

- `on` usually means standby/power state.
- Program start should be a MIoT action, commonly named `start-wash`, `start`, or similar depending on model capability data.
- Starting a washer is high risk and should require `--confirm`.

## Common Properties

- `on`: boolean power/standby state.
- `target-temperature`: numeric target temperature on climate devices.
- `brightness`: numeric light brightness.

## Common Actions

- `start-wash`: starts a washer program when present in model capability data.
- `pause`: pauses a current program when supported.
- `stop`: stops a current program when supported.
