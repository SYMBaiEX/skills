#!/usr/bin/env python3
"""Install GPT Engineer agent profiles without overwriting conflicts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets"
RETIRED = {"sol-engineer.toml": "4807e2754006d0da7b5cc3b9d5de2449c0fdfb94bc37976cedca187b3ec479e0"}


def retire_profiles(destination: Path, check: bool, upgrade: bool) -> None:
    for name, digest in RETIRED.items():
        path = destination / "agents" / name
        if not path.exists():
            continue
        if check or not upgrade:
            raise SystemExit(f"Retired profile remains installed; use --upgrade: {path}")
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f"Refusing to remove modified retired profile: {path}")
        backup = destination / "retired-agent-backups" / (name + "." + digest)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.is_symlink() or (backup.exists() and backup.read_bytes() != path.read_bytes()):
            raise SystemExit(f"Retired profile backup conflicts: {backup}")
        shutil.copy2(path, backup)
        path.unlink()


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


def install_file(source: Path, destination: Path, check: bool, upgrade: bool = False) -> None:
    if destination.exists():
        if destination.read_bytes() == source.read_bytes():
            return
        if check:
            raise SystemExit(f"Installed file differs from bundled profile: {destination}")
        if not upgrade:
            raise SystemExit(f"Refusing to overwrite conflicting file: {destination}")
        shutil.copy2(source, destination)
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
            # Managed identity is the exact bundled command, not a matcher that
            # changes when the route catalog changes. Preserve unrelated handlers.
            for existing in list(target_groups):
                existing_commands = {handler.get("command") for handler in existing.get("hooks", [])}
                if existing_commands == commands and existing.get("matcher") != group.get("matcher"):
                    existing["matcher"] = group.get("matcher")
                    changed = True
                elif commands.issubset(existing_commands) and existing.get("matcher") != group.get("matcher"):
                    managed = [handler for handler in existing["hooks"] if handler.get("command") in commands]
                    existing["hooks"] = [handler for handler in existing["hooks"] if handler.get("command") not in commands]
                    target_groups.append({**existing, "matcher": group.get("matcher"), "hooks": managed})
                    changed = True
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


def install_agents(
    source_dir: Path,
    destination_dir: Path,
    pattern: str,
    check: bool,
    upgrade: bool,
) -> None:
    sources = sorted(source_dir.glob(pattern))
    if not sources:
        raise SystemExit(f"No agent assets found in: {source_dir}")
    for source in sources:
        install_file(source, destination_dir / source.name, check, upgrade)


def install_codex(destination: Path, check: bool, project: bool, upgrade: bool) -> None:
    retire_profiles(destination, check, upgrade)
    install_agents(
        ASSET_ROOT / "codex" / "agents",
        destination / "agents",
        "*.toml",
        check,
        upgrade,
    )
    if not project:
        return
    for source in sorted((ASSET_ROOT / "codex" / "hooks").glob("*.py")):
        install_file(source, destination / "hooks" / source.name, check, upgrade)
    merge_codex_hooks(destination / "hooks.json", check)


def install_claude(destination: Path, check: bool, upgrade: bool) -> None:
    forced_model = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "").strip()
    if forced_model and forced_model.lower() != "inherit":
        print(
            "warning: CLAUDE_CODE_SUBAGENT_MODEL overrides every Claude agent profile "
            f"with {forced_model!r}",
            file=sys.stderr,
        )
    install_agents(
        ASSET_ROOT / "claude" / "agents",
        destination / "agents",
        "*.md",
        check,
        upgrade,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("target", nargs="?", help="Target Git repository root")
    scope.add_argument("--global", dest="global_install", action="store_true", help="Install user-level agents")
    parser.add_argument("--provider", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--check", action="store_true", help="Verify installation without writing")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Replace differing bundled agent profiles; never changes provider config",
    )
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
            install_codex(destination, args.check, project, args.upgrade)
        else:
            install_claude(destination, args.check, args.upgrade)

    action = "Verified" if args.check else "Installed"
    scope_name = "user-level" if args.global_install else "project-level"
    print(f"{action} {scope_name} GPT Engineer profiles for {', '.join(providers)}")
    if not args.check:
        print("Restart the selected agent and start a new task before testing profile routing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
