# Safety Policy

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

Default high-risk categories include locks, cameras, doorbells, scenes, appliance starts, vacuum starts, and plug power changes.

Example:

```json
{
  "disabled_devices": [
    {"model": "lock"},
    {"model": "camera"},
    {"name": "front door"}
  ],
  "disabled_actions": [
    {"model": "doorbell"},
    {"action": "unlock"}
  ],
  "confirm_required": [
    {"action": "scene"},
    {"model": "washer", "action": "start"},
    {"model": "airconditioner"},
    {"model": "plug", "action": "set-on"}
  ]
}
```

Never bypass `POLICY_BLOCKED`. When `CONFIRMATION_REQUIRED` is returned, show the confirmation token to the user and wait for approval.

Confirmation tokens are intentionally explicit. For example, if a scene run returns token `scene:12345`, rerun only after the user approves:

```powershell
mijiactl scene run --id 12345 --home-id <home_id> --confirm scene:12345
```
