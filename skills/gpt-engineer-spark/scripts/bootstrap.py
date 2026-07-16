#!/usr/bin/env python3
"""Install GPT Engineer Spark Codex profiles without overwriting conflicts."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
AGENT_ASSETS = SKILL_ROOT / "assets" / "codex" / "agents"


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
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("target", nargs="?", help="Target Git repository root")
    scope.add_argument("--global", dest="global_install", action="store_true", help="Install user-level agents")
    parser.add_argument("--check", action="store_true", help="Verify installation without writing")
    args = parser.parse_args(argv)

    sources = sorted(AGENT_ASSETS.glob("*.toml"))
    if not sources:
        raise SystemExit(f"No Spark agent assets found in: {AGENT_ASSETS}")
    if args.global_install:
        destination = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve() / "agents"
        scope_name = "user-level"
    else:
        destination = repo_root(args.target) / ".codex" / "agents"
        scope_name = "project-level"

    for source in sources:
        install_file(source, destination / source.name, args.check)

    action = "Verified" if args.check else "Installed"
    print(f"{action} {scope_name} GPT Engineer Spark profiles")
    if not args.check:
        print("Restart Codex and start a new task before testing Spark routing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
