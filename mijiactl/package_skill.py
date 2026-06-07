from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "controlling-mijia-smart-home"
CANONICAL_SKILL_DIR = PROJECT_ROOT / "skills" / SKILL_NAME


def export_skill_package(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(CANONICAL_SKILL_DIR, output_dir)
    _copy(PROJECT_ROOT / "README.md", output_dir / "README.md")
    _copy(PROJECT_ROOT / "README.zh-CN.md", output_dir / "README.zh-CN.md")
    _copy(PROJECT_ROOT / "uninstall.ps1", output_dir / "uninstall.ps1")

    return {
        "skill": SKILL_NAME,
        "path": str(output_dir),
        "files": sorted(str(path.relative_to(output_dir)) for path in output_dir.rglob("*") if path.is_file()),
    }


def _copy(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, dst)


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="mijiactl-export-skill")
    parser.add_argument("--out", type=Path, default=Path("dist") / SKILL_NAME)
    args = parser.parse_args()
    print(json.dumps(export_skill_package(args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
