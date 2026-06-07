# Device Catalog Hints

This file is a human-maintained supplement. Dynamic capabilities from `mijiactl info --model <model> --json` are the source of truth.

## Washer

- `on` usually means standby/power state.
- Program start should be a MIoT action, commonly named `start-wash`, `start`, or similar depending on model capability data.
- Starting a washer is high risk and should require `--confirm`.

## Common Properties

- `switch-status`: boolean power state for many lights/fans.
- `brightness`: numeric light brightness.
- `color-temperature`: light color temperature.

## Common Actions

- `toggle`: toggles a device state when present.
- `start-wash`: starts a washer program when present.
- `pause`: pauses a current program when supported.
- `stop`: stops a current program when supported.
