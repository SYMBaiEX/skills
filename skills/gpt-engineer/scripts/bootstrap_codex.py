#!/usr/bin/env python3
"""Install GPT Engineer Codex agents and hooks without overwriting conflicts."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets" / "codex"


def repo_root(target: str | None) -> Path:
    if target:
        root = Path(target).expanduser().resolve()
    else:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        root = Path(result.stdout.strip()).resolve()
    if not (root / ".git").exists():
        raise SystemExit(f"Not a Git repository root: {root}")
    return root


def install_file(source: Path, destination: Path, check: bool) -> None:
    if destination.exists():
        if destination.read_bytes() != source.read_bytes():
            raise SystemExit(f"Refusing to overwrite conflicting file: {destination}")
        return
    if check:
        raise SystemExit(f"Missing installed file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def merge_hooks(destination: Path, check: bool) -> None:
    supplied = json.loads((ASSET_ROOT / "hooks.json").read_text())
    current = json.loads(destination.read_text()) if destination.exists() else {"hooks": {}}
    hooks = current.setdefault("hooks", {})

    changed = False
    for event, groups in supplied["hooks"].items():
        target_groups = hooks.setdefault(event, [])
        known = {
            handler.get("command")
            for group in target_groups
            for handler in group.get("hooks", [])
        }
        for group in groups:
            commands = {handler.get("command") for handler in group.get("hooks", [])}
            if commands - known:
                target_groups.append(group)
                known.update(commands)
                changed = True

    if check and changed:
        raise SystemExit(f"GPT Engineer hook entries are missing from: {destination}")
    if changed:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(current, indent=2) + "\n")
        temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", help="Target Git repository root")
    parser.add_argument("--check", action="store_true", help="Verify installation without writing")
    args = parser.parse_args()
    root = repo_root(args.target)

    for source in sorted((ASSET_ROOT / "agents").glob("*.toml")):
        install_file(source, root / ".codex" / "agents" / source.name, args.check)
    for source in sorted((ASSET_ROOT / "hooks").glob("*.py")):
        install_file(source, root / ".codex" / "hooks" / source.name, args.check)
    merge_hooks(root / ".codex" / "hooks.json", args.check)

    action = "Verified" if args.check else "Installed"
    print(f"{action} GPT Engineer Codex profiles and hooks in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
