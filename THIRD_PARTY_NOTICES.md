# Third-Party Notices

This project is distributed as a local control wrapper around third-party Xiaomi/Mijia libraries and public MIoT metadata.

## Runtime Dependencies

| Dependency | Use | License notes |
| --- | --- | --- |
| `mijiaAPI==3.0.5` | Xiaomi/Mijia login, device listing, property control, action execution, scenes | PyPI lists `GPL-3.0-or-later` for current `mijiaAPI` releases. Because the Windows release executable bundles this dependency, this repository is licensed as `GPL-3.0-or-later`, not MIT. |
| `requests` | Transitive dependency used by `mijiaAPI` | Apache-2.0 in installed package metadata. |
| `pycryptodome` | Transitive crypto dependency used by `mijiaAPI` | BSD/Public Domain in installed package metadata. |
| `qrcode` | Transitive QR-code dependency used by `mijiaAPI` login | BSD in installed package metadata. |
| `Pillow` | Transitive image dependency used by QR-code rendering | Pillow license; see the package distribution for full terms. |

## Build-Time Dependencies

| Dependency | Use | License notes |
| --- | --- | --- |
| `uv` | Development, tests, package builds | See the `uv` project license. |
| `hatchling` | Python build backend | See the `hatchling` project license. |
| `PyInstaller` | Windows executable build | GPL with a bootloader exception; see the `PyInstaller` project license. |

## Project Acknowledgements

This project was informed by the shape and lessons of these community projects and articles:

- `moneshvenkul/mijia-skills`: earlier Agent Skill-style organization around Mijia scripts.
- `ssttkkl/mijia-skill` and the related article about MIoT action control: the washer example clarified why complex devices often require `run_action` instead of property-only control.
- `Do1e/mijia-api` / `mijiaAPI`: the Python Mijia API used by `mijiactl` for login and cloud control.

The implementation in this repository is a new local CLI/runtime plus Agent Skill wrapper, with policy checks, JSON output, capability caching, and release packaging designed for agent use.
