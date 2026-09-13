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
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets"
# Historical profile retirement is intentionally empty: route selection now
# handles legacy roles without requiring a legacy profile to be removed.
RETIRED: dict[str, str] = {}
BUNDLE_VERSION = "2.1.0"
RECEIPT_NAME = ".gpt-engineer-install.json"
RECEIPT_VERSION = 1

# These are exact hashes of prior bundled assets that shipped before receipts
# existed. They are migration evidence, not a license to replace arbitrary
# user files. A file that is neither in this table nor in a trusted receipt is
# preserved on upgrade and uninstall.
KNOWN_BUNDLED_HASHES = {
    "agents/luna-max-worker.toml": {
        "2f6ed7fda853cc5e7ea93f0112d51d61afd4ab39200c8ddec137e93b18d68bdd",
        "c3dc7db4bcedfddebab68b92659161c1125262eef767e3e313017a70bfbbcfcf",
        "f528eae1cb93eef4fe0d3132d28e149d793f238b54e579e75b72c956d0be5a12",
    },
    "agents/luna-verifier.toml": {
        "2f4dedf82f957f256f8d372d182706dd9854953c5863d1e7a1d98d5948e054b3",
        "802de2ca25d1ef0cfe37d1a494ab5dc51286db25e6cdf3cabb78f251079af0a5",
    },
    "agents/luna-worker.toml": {
        "5daa5194184350d6f25b6e523b81f72866f57e5152cc0d5efb97415a6e09c271",
        "06b489562a28c5c8abefaa7afcc8731c32ca418227cb823cc4df3fe37d5b8105",
    },
    "agents/terra-explorer.toml": {
        "8062ea8a602ae195e6f88df847c0a169ac450a7332767f77f699efd895cfcdaf",
        "56f4a2b435d4677021a6af115347e06f05ab1ac373ac0fe3cf8421f00fa94e1a",
    },
    "agents/terra-worker.toml": {
        "af55cc90925428a09f2eb965abbb736f26362b3785f7843bc3d7ac294fe932be",
        "e97f6c5cd4dfc387a9595a9ed5f213fee51842ca85f8c1bb7cb2eafdea5ded80",
    },
    "hooks/gpt_engineer_subagent_context.py": {
        "547091486167a8ca9760392fa2a8210897f2112c6db8cdaf6b9ddcbbf951c0e1",
        "d3b9c75bc7374a07c9f265ceb5a4f8ff21c4e4e6069f6cd4ae16f7012514fc7e",
        "7f574bb78a145a14bb699ca74b608f6f6363a535af166b647214859ce049779c",
        "b28d44a04fdc7173a302d4677a1fb2188e1060733cf25ddd8042167701ac293e",
    },
    "hooks/gpt_engineer_guard.py": {
        "aaebf8661fbbe367e1ee72c109ea2ee23e53eb9044e47d9e1ca61081a366eb76",
    },
}
KNOWN_MANAGED_HOOK_MATCHERS = {
    "SubagentStart": {
        "^(sol_engineer|terra_explorer|terra_worker|luna_verifier)$",
        "^(sol_engineer|terra_explorer|terra_worker|luna_worker|luna_verifier)$",
    },
}
SYSTEM_PATH_ALIASES = {Path("/var"), Path("/tmp")}


def file_hash(path: Path) -> str | None:
    """Hash only regular files; never follow symlinks during ownership checks."""
    if path.is_symlink() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def symlink_component(path: Path) -> Path | None:
    """Return the first existing symlink in a destination path, if any."""
    absolute = path.expanduser()
    if not absolute.is_absolute():
        absolute = Path.cwd() / absolute
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink() and current not in SYSTEM_PATH_ALIASES:
            return current
    return None


def ensure_safe_destination(destination: Path) -> None:
    link = symlink_component(destination)
    if link is not None:
        raise SystemExit(f"Refusing managed install through symlink path: {link}")


@contextmanager
def lifecycle_lock(destination: Path):
    """Serialize setup and lifecycle mutations for one destination."""
    ensure_safe_destination(destination)
    lock_path = destination.parent / f".{destination.name}.gpt-engineer.lock"
    ensure_safe_destination(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError as exc:
        raise SystemExit(f"Unable to acquire GPT Engineer lifecycle lock: {lock_path}: {exc}") from exc
    with os.fdopen(fd, "a+") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: Path, content: str) -> None:
    if path.is_symlink():
        raise SystemExit(f"Refusing to replace symlink path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_copy_file(source: Path, destination: Path) -> None:
    """Copy a bundled regular file without ever opening a destination symlink."""
    if destination.is_symlink():
        raise SystemExit(f"Refusing to replace symlink path: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as source_stream, os.fdopen(fd, "wb") as target_stream:
            shutil.copyfileobj(source_stream, target_stream)
            target_stream.flush()
            os.fsync(target_stream.fileno())
        shutil.copystat(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def receipt_path(destination: Path) -> Path:
    return destination / RECEIPT_NAME


def load_receipt(destination: Path) -> dict:
    path = receipt_path(destination)
    if not path.exists() or path.is_symlink():
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        print(f"warning: Ignoring invalid GPT Engineer receipt: {path}", file=sys.stderr)
        return {}
    if not isinstance(value, dict) or value.get("version") != RECEIPT_VERSION:
        print(f"warning: Ignoring unsupported GPT Engineer receipt: {path}", file=sys.stderr)
        return {}
    files = value.get("files", {})
    hooks = value.get("hooks", [])
    if not isinstance(files, dict) or not isinstance(hooks, list):
        print(f"warning: Ignoring malformed GPT Engineer receipt: {path}", file=sys.stderr)
        return {}
    return value


def write_receipt(destination: Path, receipt: dict) -> None:
    path = receipt_path(destination)
    if path.is_symlink():
        print(f"warning: Preserving symlink receipt: {path}", file=sys.stderr)
        return
    atomic_write_text(path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def source_files(project: bool) -> dict[str, Path]:
    files = {
        f"agents/{source.name}": source
        for source in sorted((ASSET_ROOT / "codex" / "agents").glob("*.toml"))
    }
    if project:
        files.update(
            {
                f"hooks/{source.name}": source
                for source in sorted((ASSET_ROOT / "codex" / "hooks").glob("*.py"))
            }
        )
    return files


def trusted_hashes(relative: str, source: Path, receipt: dict) -> set[str]:
    values = set(KNOWN_BUNDLED_HASHES.get(relative, set()))
    recorded = receipt.get("files", {}).get(relative)
    if isinstance(recorded, str):
        values.add(recorded)
    current = file_hash(source)
    if current:
        values.add(current)
    return values


def retire_profiles(destination: Path, check: bool, upgrade: bool) -> None:
    for name, digest in RETIRED.items():
        path = destination / "agents" / name
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            print(
                f"warning: Preserving customized or symlink retired profile: {path}; "
                "it is not an allowed GPT Engineer dispatch target",
                file=sys.stderr,
            )
            continue
        if check or not upgrade:
            raise SystemExit(f"Retired profile remains installed; use --upgrade: {path}")
        backup = destination / "retired-agent-backups" / (name + "." + digest)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.is_symlink() or (backup.exists() and backup.read_bytes() != path.read_bytes()):
            raise SystemExit(f"Retired profile backup conflicts: {backup}")
        shutil.copy2(path, backup)
        path.unlink()


def repo_root(target: str | None) -> Path:
    if target:
        root = Path(target).expanduser().absolute()
        ensure_safe_destination(root)
    else:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        root = Path(result.stdout.strip()).absolute()
    ensure_safe_destination(root)
    if not (root / ".git").exists():
        raise SystemExit(f"Not a Git repository root: {root}")
    return root


def install_file(
    source: Path,
    destination: Path,
    check: bool,
    upgrade: bool = False,
    *,
    relative: str | None = None,
    receipt: dict | None = None,
) -> bool:
    """Install one asset while preserving unknown regular files and symlinks."""
    ensure_safe_destination(destination.parent)
    relative = relative or destination.name
    receipt = receipt or {}
    if destination.exists() or destination.is_symlink():
        current = file_hash(destination)
        expected = file_hash(source)
        if current is not None and current == expected:
            return True
        if check:
            raise SystemExit(f"Installed file differs from bundled profile: {destination}")
        if not upgrade:
            raise SystemExit(f"Refusing to overwrite conflicting file: {destination}")
        if current is None or current not in trusted_hashes(relative, source, receipt):
            print(
                f"warning: Preserving customized or symlink file: {destination}; "
                "it is not a known GPT Engineer asset",
                file=sys.stderr,
            )
            return False
        atomic_copy_file(source, destination)
        return True
    if check:
        raise SystemExit(f"Missing installed file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_copy_file(source, destination)
    return True


def merge_codex_hooks(destination: Path, check: bool) -> bool:
    supplied = json.loads((ASSET_ROOT / "codex" / "hooks.json").read_text())
    ensure_safe_destination(destination.parent)
    if destination.is_symlink():
        print(f"warning: Preserving symlink hook config: {destination}", file=sys.stderr)
        if check:
            raise SystemExit(f"Refusing to verify symlink hook config: {destination}")
        return False
    if destination.exists():
        try:
            current = json.loads(destination.read_text())
        except (OSError, json.JSONDecodeError):
            print(f"warning: Preserving invalid hook config: {destination}", file=sys.stderr)
            if check:
                raise SystemExit(f"Invalid hook config: {destination}")
            return False
    else:
        current = {"hooks": {}}
    if not isinstance(current, dict) or not isinstance(current.get("hooks", {}), dict):
        print(f"warning: Preserving unsupported hook config: {destination}", file=sys.stderr)
        if check:
            raise SystemExit(f"Unsupported hook config: {destination}")
        return False
    hooks = current.setdefault("hooks", {})

    changed = False
    for event, groups in supplied["hooks"].items():
        target_groups = hooks.setdefault(event, [])
        if not isinstance(target_groups, list) or any(
            not isinstance(group, dict) or not isinstance(group.get("hooks"), list)
            or any(not isinstance(handler, dict) for handler in group.get("hooks", []))
            for group in target_groups
        ):
            print(f"warning: Preserving unsupported hook entries: {destination}", file=sys.stderr)
            if check:
                raise SystemExit(f"Unsupported hook entries: {destination}")
            return False
        for group in groups:
            matcher = group.get("matcher")
            for handler in group.get("hooks", []):
                if handler.get("type") != "command":
                    continue
                handler_id = json.dumps(handler, sort_keys=True)
                current_id = (event, matcher, handler_id)
                old_matchers = KNOWN_MANAGED_HOOK_MATCHERS.get(event, set())
                old_ids = {(event, old, handler_id) for old in old_matchers}
                all_ids = {
                    (event, existing.get("matcher"), json.dumps(item, sort_keys=True))
                    for existing in target_groups
                    for item in existing.get("hooks", [])
                }
                old_matches = old_ids & all_ids
                if old_matches:
                    # Migrate only an exact handler under an evidence-backed
                    # historical matcher. Do not rewrite arbitrary custom scopes.
                    for existing in target_groups:
                        if existing.get("matcher") in {identity[1] for identity in old_matches}:
                            existing["hooks"] = [
                                item for item in existing["hooks"]
                                if json.dumps(item, sort_keys=True) != handler_id
                            ]
                    changed = True
                if current_id in all_ids:
                    continue
                target = next((existing for existing in target_groups if existing.get("matcher") == matcher), None)
                if target is None:
                    target_groups.append({"matcher": matcher, "hooks": [handler]})
                else:
                    target.setdefault("hooks", []).append(handler)
                changed = True

        # Repeated setup must be idempotent. Keep one exact managed group and
        # handler identity per event while preserving unrelated handlers.
        managed_ids = {
            (event, group.get("matcher"), json.dumps(handler, sort_keys=True))
            for group in groups
            for handler in group.get("hooks", [])
            if handler.get("type") == "command"
        }
        historical_ids = {
            (event, matcher, json.dumps(handler, sort_keys=True))
            for matcher in KNOWN_MANAGED_HOOK_MATCHERS.get(event, set())
            for group in groups
            for handler in group.get("hooks", [])
            if handler.get("type") == "command"
        }
        managed_ids |= historical_ids
        seen_managed: set[tuple] = set()
        deduped_groups = []
        for group in target_groups:
            handlers = []
            for handler in group.get("hooks", []):
                identity = json.dumps(handler, sort_keys=True)
                full_id = (event, group.get("matcher"), identity)
                if full_id in managed_ids:
                    if full_id in seen_managed:
                        changed = True
                        continue
                    seen_managed.add(full_id)
                handlers.append(handler)
            if handlers:
                if len(handlers) != len(group.get("hooks", [])):
                    changed = True
                deduped_groups.append({**group, "hooks": handlers})
            else:
                changed = True
        if len(deduped_groups) != len(target_groups):
            changed = True
        hooks[event] = deduped_groups

    if check and changed:
        raise SystemExit(f"GPT Engineer hook entries are missing from: {destination}")
    if changed:
        atomic_write_text(destination, json.dumps(current, indent=2) + "\n")
    return changed


def install_agents(
    source_dir: Path,
    destination_dir: Path,
    pattern: str,
    check: bool,
    upgrade: bool,
    receipt: dict | None = None,
) -> None:
    sources = sorted(source_dir.glob(pattern))
    if not sources:
        raise SystemExit(f"No agent assets found in: {source_dir}")
    for source in sources:
        install_file(
            source,
            destination_dir / source.name,
            check,
            upgrade,
            relative=f"agents/{source.name}",
            receipt=receipt,
        )


def managed_hook_descriptors() -> list[dict]:
    supplied = json.loads((ASSET_ROOT / "codex" / "hooks.json").read_text())
    descriptors = []
    for event, groups in supplied.get("hooks", {}).items():
        for group in groups:
            for handler in group.get("hooks", []):
                if isinstance(handler, dict) and handler.get("type") == "command" and isinstance(handler.get("command"), str):
                    descriptors.append(
                        {
                            "event": event,
                            "matcher": group.get("matcher"),
                            "handler": handler,
                        }
                    )
    return descriptors


def installed_hook_descriptors(destination: Path) -> list[dict]:
    path = destination / "hooks.json"
    ensure_safe_destination(path.parent)
    if path.is_symlink() or not path.is_file():
        return []
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(value, dict) or not isinstance(value.get("hooks"), dict):
        return []
    result = []
    for event, groups in value["hooks"].items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                continue
            for handler in group["hooks"]:
                if isinstance(handler, dict) and handler.get("type") == "command" and isinstance(handler.get("command"), str):
                    result.append({"event": event, "matcher": group.get("matcher"), "handler": handler})
    return result


def _save_codex_receipt(destination: Path, project: bool, previous: dict) -> None:
    # A profiles-only upgrade must not discard ownership of existing hook files.
    files = {
        relative: digest for relative, digest in previous.get("files", {}).items()
        if relative in source_files(True) and file_hash(destination / relative) == digest
    }
    for relative, source in source_files(project).items():
        installed = destination / relative
        current = file_hash(installed)
        if current is None:
            continue
        prior = previous.get("files", {}).get(relative)
        if current == file_hash(source) or current == prior:
            files[relative] = current
    receipt = {
        "version": RECEIPT_VERSION,
        "bundle_version": BUNDLE_VERSION,
        "files": files,
        "hooks": (
            [
                descriptor
                for descriptor in managed_hook_descriptors()
                if descriptor in installed_hook_descriptors(destination)
            ]
            if project
            else [descriptor for descriptor in previous.get("hooks", [])
                  if descriptor in installed_hook_descriptors(destination)]
        ),
    }
    write_receipt(destination, receipt)


def install_codex(destination: Path, check: bool, project: bool, upgrade: bool) -> None:
    ensure_safe_destination(destination)
    with nullcontext() if check else lifecycle_lock(destination):
        _install_codex(destination, check, project, upgrade)


def _install_codex(destination: Path, check: bool, project: bool, upgrade: bool) -> None:
    receipt = load_receipt(destination)
    retire_profiles(destination, check, upgrade)
    install_agents(
        ASSET_ROOT / "codex" / "agents",
        destination / "agents",
        "*.toml",
        check,
        upgrade,
        receipt,
    )
    if not project:
        if not check:
            _save_codex_receipt(destination, project, receipt)
        return
    for source in sorted((ASSET_ROOT / "codex" / "hooks").glob("*.py")):
        install_file(
            source,
            destination / "hooks" / source.name,
            check,
            upgrade,
            relative=f"hooks/{source.name}",
            receipt=receipt,
        )
    merge_codex_hooks(destination / "hooks.json", check)
    if not check:
        _save_codex_receipt(destination, project, receipt)


def _rewrite_codex_hooks(destination: Path, check: bool) -> bool:
    path = destination / "hooks.json"
    ensure_safe_destination(path.parent)
    if not path.exists() or path.is_symlink():
        return False
    try:
        current = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        print(f"warning: Preserving invalid or symlink hook config: {path}", file=sys.stderr)
        return False
    receipt = load_receipt(destination)
    descriptors = receipt.get("hooks") or managed_hook_descriptors()
    targets = {
        (
            descriptor.get("event"),
            descriptor.get("matcher"),
            json.dumps(descriptor.get("handler", {}), sort_keys=True),
        )
        for descriptor in descriptors
        if isinstance(descriptor, dict)
    }
    changed = False
    hooks = current.get("hooks", {}) if isinstance(current, dict) else {}
    if not isinstance(hooks, dict):
        return False
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            continue
        remaining_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                remaining_groups.append(group)
                continue
            remaining = []
            for handler in group["hooks"]:
                identity = (event, group.get("matcher"), json.dumps(handler, sort_keys=True))
                if identity in targets:
                    changed = True
                    continue
                remaining.append(handler)
            if remaining:
                remaining_groups.append({**group, "hooks": remaining})
            elif group.get("hooks"):
                changed = True
        if remaining_groups:
            hooks[event] = remaining_groups
        else:
            hooks.pop(event, None)
    if not changed:
        return False
    if check:
        raise SystemExit(f"Managed GPT Engineer hooks are present in: {path}")
    atomic_write_text(path, json.dumps(current, indent=2) + "\n")
    return True


def disable_codex(destination: Path, project: bool) -> None:
    ensure_safe_destination(destination)
    with lifecycle_lock(destination):
        _disable_codex(destination, project)


def _disable_codex(destination: Path, project: bool) -> None:
    if not project:
        print("No project hooks to disable; global installs contain profiles only.")
        return
    if _rewrite_codex_hooks(destination, False):
        print(f"Disabled managed GPT Engineer hooks in {destination / 'hooks.json'}")
    else:
        print("No managed GPT Engineer hooks found to disable.")


def uninstall_codex(destination: Path, project: bool) -> None:
    ensure_safe_destination(destination)
    with lifecycle_lock(destination):
        _uninstall_codex(destination, project)


def _uninstall_codex(destination: Path, project: bool) -> None:
    # Unknown registration state must not leave handlers pointing to deleted scripts.
    # Fail before any mutation; the user can repair/review this config explicitly.
    hook_config = destination / "hooks.json"
    if project and (hook_config.exists() or hook_config.is_symlink()):
        if hook_config.is_symlink():
            raise SystemExit("Cannot safely uninstall with a symlink hook config; preserved all assets")
        try:
            value = json.loads(hook_config.read_text())
            valid = isinstance(value, dict) and isinstance(value.get("hooks", {}), dict)
            if valid:
                valid = all(
                    isinstance(groups, list) and all(
                        isinstance(group, dict) and isinstance(group.get("hooks"), list)
                        and all(isinstance(handler, dict) for handler in group["hooks"])
                        for group in groups
                    ) for groups in value.get("hooks", {}).values()
                )
        except (OSError, json.JSONDecodeError):
            valid = False
        if not valid:
            raise SystemExit("Cannot safely uninstall with invalid hook config; preserved all assets")
    receipt = load_receipt(destination)
    removed = 0
    if project and _rewrite_codex_hooks(destination, False):
        removed += 1
    active_hook_commands = {
        descriptor["handler"].get("command", "")
        for descriptor in installed_hook_descriptors(destination)
        if isinstance(descriptor.get("handler"), dict)
    }
    for relative, source in source_files(project).items():
        path = destination / relative
        ensure_safe_destination(path.parent)
        if project and relative.startswith("hooks/") and any(
            source.name in command for command in active_hook_commands if isinstance(command, str)
        ):
            print(f"warning: Preserving hook script referenced by a remaining handler: {path}", file=sys.stderr)
            continue
        current = file_hash(path)
        if current is None:
            if path.is_symlink():
                print(f"warning: Preserving symlink file: {path}", file=sys.stderr)
            continue
        if current not in trusted_hashes(relative, source, receipt):
            print(f"warning: Preserving customized file: {path}", file=sys.stderr)
            continue
        path.unlink()
        removed += 1
    receipt_file = receipt_path(destination)
    if receipt_file.exists() and not receipt_file.is_symlink():
        receipt_file.unlink()
        removed += 1
    print(f"Uninstalled {removed} managed GPT Engineer item(s); customized files were preserved.")


def install_claude(destination: Path, check: bool, upgrade: bool) -> None:
    ensure_safe_destination(destination)
    with nullcontext() if check else lifecycle_lock(destination):
        _install_claude(destination, check, upgrade)


def _install_claude(destination: Path, check: bool, upgrade: bool) -> None:
    receipt = load_receipt(destination)
    forced_model = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "").strip()
    if forced_model and forced_model.lower() != "inherit":
        print(
            "warning: CLAUDE_CODE_SUBAGENT_MODEL is set; verify version-specific resolution "
            f"for {forced_model!r}. It is not a universal force guarantee; inspect FORCE separately.",
            file=sys.stderr,
        )
    install_agents(
        ASSET_ROOT / "claude" / "agents",
        destination / "agents",
        "*.md",
        check,
        upgrade,
        receipt,
    )
    if not check:
        files = {}
        for source in (ASSET_ROOT / "claude" / "agents").glob("*.md"):
            relative = "agents/" + source.name
            digest = file_hash(destination / relative)
            if digest and digest in trusted_hashes(relative, source, receipt):
                files[relative] = digest
        write_receipt(destination, {"version": RECEIPT_VERSION, "bundle_version": BUNDLE_VERSION,
                                    "files": files, "hooks": []})


def uninstall_claude(destination: Path) -> None:
    """Core bootstrap installs Claude profiles only, never Claude hooks/settings."""
    ensure_safe_destination(destination)
    with lifecycle_lock(destination):
        receipt = load_receipt(destination)
        for source in (ASSET_ROOT / "claude" / "agents").glob("*.md"):
            relative = "agents/" + source.name
            path = destination / relative
            ensure_safe_destination(path.parent)
            digest = file_hash(path)
            if digest and digest in trusted_hashes(relative, source, receipt):
                path.unlink()
            elif path.exists() or path.is_symlink():
                print(f"warning: Preserving customized or symlink profile: {path}", file=sys.stderr)
        receipt_file = receipt_path(destination)
        if receipt_file.is_file() and not receipt_file.is_symlink():
            receipt_file.unlink()
    print("Removed unchanged GPT Engineer Claude profiles; other settings and hooks preserved.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("target", nargs="?", help="Target Git repository root")
    scope.add_argument("--global", dest="global_install", action="store_true", help="Install user-level agents")
    parser.add_argument("--provider", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--check", action="store_true", help="Verify installation without writing")
    parser.add_argument("--diagnose", action="store_true", help="Alias for --check")
    parser.add_argument("--with-hooks", action="store_true", help="Explicitly install/verify project Codex hooks; default is profiles only")
    lifecycle = parser.add_mutually_exclusive_group()
    lifecycle.add_argument("--disable", action="store_true", help="Disable managed Codex hooks only")
    lifecycle.add_argument("--uninstall", action="store_true", help="Remove unchanged managed assets for one selected provider")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Replace differing bundled agent profiles; never changes provider config",
    )
    args = parser.parse_args(argv)

    if args.diagnose:
        args.check = True
    if (args.disable or args.uninstall) and args.check:
        parser.error("--check/--diagnose cannot be combined with --disable or --uninstall")
    if args.disable and args.provider != "codex":
        parser.error("hook disable requires --provider codex; no Claude hooks are installed")
    if args.uninstall and args.provider == "all":
        parser.error("uninstall requires one explicit --provider codex or claude")
    if args.with_hooks and (args.global_install or args.provider == "claude" or args.disable or args.uninstall):
        parser.error("--with-hooks applies only to project Codex setup/verification")

    if args.global_install:
        destinations = {
            "codex": Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().absolute(),
            "claude": Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser().absolute(),
        }
        project = False
    else:
        root = repo_root(args.target)
        destinations = {"codex": root / ".codex", "claude": root / ".claude"}
        project = True

    if args.disable or args.uninstall:
        destination = destinations[args.provider]
        if args.disable:
            disable_codex(destination, project)
        elif args.provider == "claude":
            uninstall_claude(destination)
        else:
            uninstall_codex(destination, project)
        return 0

    providers = ("codex", "claude") if args.provider == "all" else (args.provider,)
    for provider in providers:
        destination = destinations[provider]
        if provider == "codex":
            install_codex(destination, args.check, project and args.with_hooks, args.upgrade)
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
