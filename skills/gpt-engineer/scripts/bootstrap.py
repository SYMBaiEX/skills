#!/usr/bin/env python3
"""Install GPT Engineer agent profiles without overwriting conflicts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets"


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


def merge_codex_hooks(destination: Path, check: bool) -> None:
    supplied = json.loads((ASSET_ROOT / "codex" / "hooks.json").read_text())
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


def install_agents(source_dir: Path, destination_dir: Path, pattern: str, check: bool) -> None:
    sources = sorted(source_dir.glob(pattern))
    if not sources:
        raise SystemExit(f"No agent assets found in: {source_dir}")
    for source in sources:
        install_file(source, destination_dir / source.name, check)


def install_codex(destination: Path, check: bool, project: bool) -> None:
    install_agents(ASSET_ROOT / "codex" / "agents", destination / "agents", "*.toml", check)
    if not project:
        return
    for source in sorted((ASSET_ROOT / "codex" / "hooks").glob("*.py")):
        install_file(source, destination / "hooks" / source.name, check)
    merge_codex_hooks(destination / "hooks.json", check)


def install_claude(destination: Path, check: bool) -> None:
    forced_model = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "").strip()
    if forced_model and forced_model.lower() != "inherit":
        print(
            "warning: CLAUDE_CODE_SUBAGENT_MODEL overrides every Claude agent profile "
            f"with {forced_model!r}",
            file=sys.stderr,
        )
    install_agents(ASSET_ROOT / "claude" / "agents", destination / "agents", "*.md", check)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("target", nargs="?", help="Target Git repository root")
    scope.add_argument("--global", dest="global_install", action="store_true", help="Install user-level agents")
    parser.add_argument("--provider", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--check", action="store_true", help="Verify installation without writing")
    args = parser.parse_args(argv)

    if args.global_install:
        destinations = {
            "codex": Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve(),
            "claude": Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser().resolve(),
        }
        project = False
    else:
        root = repo_root(args.target)
        destinations = {"codex": root / ".codex", "claude": root / ".claude"}
        project = True

    providers = ("codex", "claude") if args.provider == "all" else (args.provider,)
    for provider in providers:
        destination = destinations[provider]
        if provider == "codex":
            install_codex(destination, args.check, project)
        else:
            install_claude(destination, args.check)

    action = "Verified" if args.check else "Installed"
    scope_name = "user-level" if args.global_install else "project-level"
    print(f"{action} {scope_name} GPT Engineer profiles for {', '.join(providers)}")
    if not args.check:
        print("Restart the selected agent and start a new task before testing profile routing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
