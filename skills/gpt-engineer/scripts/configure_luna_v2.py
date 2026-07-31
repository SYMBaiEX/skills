#!/usr/bin/env python3
"""Install or remove the temporary Luna Multi-Agent V2 catalog compatibility shim."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


MANAGED_CATALOG = "model-catalogs/gpt-engineer-luna-v2.json"
LUNA = "gpt-5.6-luna"
V2_PARENTS = ("gpt-5.6-sol", "gpt-5.6-terra")


def load_catalog(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read model catalog {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("models"), list):
        raise SystemExit(f"Invalid model catalog shape: {path}")
    return value


def model(catalog: dict[str, object], slug: str) -> dict[str, object]:
    matches = [item for item in catalog["models"] if isinstance(item, dict) and item.get("slug") == slug]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {slug} entry; found {len(matches)}")
    return matches[0]


def shim_required(source: dict[str, object]) -> bool:
    luna_version = model(source, LUNA).get("multi_agent_version")
    parent_versions = {model(source, slug).get("multi_agent_version") for slug in V2_PARENTS}
    if luna_version == "v2":
        return False
    if luna_version != "v1" or parent_versions != {"v2"}:
        raise SystemExit(
            "Catalog is not the known Sol/Terra V2 plus Luna V1 mismatch; refusing to patch it."
        )
    return True


def build_shim(source: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(source)
    model(result, LUNA)["multi_agent_version"] = "v2"
    for item in result["models"]:
        if isinstance(item, dict):
            # Codex's cache serialization omits this required custom-catalog field.
            item.setdefault("supports_reasoning_summaries", True)
    comparison = copy.deepcopy(result)
    model(comparison, LUNA)["multi_agent_version"] = "v1"
    for source_item, comparison_item in zip(source["models"], comparison["models"]):
        if isinstance(source_item, dict) and isinstance(comparison_item, dict):
            if "supports_reasoning_summaries" not in source_item:
                comparison_item.pop("supports_reasoning_summaries", None)
    if comparison != source:
        raise SystemExit("Internal error: compatibility catalog changed unexpected fields")
    return result


def resolve_codex() -> str:
    candidates = [shutil.which("codex")]
    app_binary = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    if app_binary.is_file():
        candidates.append(str(app_binary))
    for candidate in candidates:
        if candidate:
            return candidate
    raise SystemExit("Cannot validate custom catalog because the Codex executable was not found")


def validate_catalog_with_codex(catalog: dict[str, object], codex_home: Path) -> None:
    directory = codex_home / "model-catalogs"
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".luna-v2-validation.", suffix=".json", dir=directory)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(catalog, handle)
        path_value = toml_string(temporary)
        result = subprocess.run(
            [resolve_codex(), "-c", f"model_catalog_json={path_value}", "debug", "models"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            detail = (result.stderr.strip() or result.stdout.strip()).splitlines()[-1:]
            raise SystemExit(
                "Codex rejected the generated compatibility catalog"
                + (f": {detail[0]}" if detail else "")
            )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit("Timed out while Codex validated the compatibility catalog") from exc
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def toml_string(value: str) -> str:
    return json.dumps(value)


def replace_top_level(lines: list[str], key: str, value: str | None) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}\s*=")
    indexes: list[int] = []
    first_section = len(lines)
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            first_section = index
            break
        if pattern.match(line):
            indexes.append(index)
    if len(indexes) > 1:
        raise SystemExit(f"Refusing config with duplicate top-level {key} entries")
    result = list(lines)
    if indexes:
        if value is None:
            result.pop(indexes[0])
        else:
            result[indexes[0]] = f"{key} = {toml_string(value)}\n"
        return result
    if value is not None:
        result.insert(first_section, f"{key} = {toml_string(value)}\n")
    return result


def enable_feature(lines: list[str], key: str) -> list[str]:
    header = re.compile(r"^\s*\[features\]\s*(?:#.*)?$")
    key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        if header.match(line.rstrip("\n")):
            if start is not None:
                raise SystemExit("Refusing config with duplicate [features] sections")
            start = index
            continue
        if start is not None and index > start and line.lstrip().startswith("["):
            end = index
            break
    result = list(lines)
    if start is None:
        if result and result[-1].strip():
            result.append("\n")
        result.extend(["[features]\n", f"{key} = true\n"])
        return result
    matches = [index for index in range(start + 1, end) if key_pattern.match(result[index])]
    if len(matches) > 1:
        raise SystemExit(f"Refusing config with duplicate features.{key} entries")
    if matches:
        result[matches[0]] = f"{key} = true\n"
    else:
        result.insert(end, f"{key} = true\n")
    return result


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup_config(config: Path, codex_home: Path) -> Path | None:
    if not config.exists():
        return None
    backup = codex_home / "backups" / (
        f"config.toml.luna-v2.{time.strftime('%Y%m%d-%H%M%S')}.{time.time_ns()}.bak"
    )
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config, backup)
    return backup


def parsed_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise SystemExit(f"Cannot read Codex config {path}: {exc}") from exc
    result: dict[str, object] = {}
    section = ""
    seen_catalog = False
    seen_fast = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped.split("#", 1)[0].strip()
            continue
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = (part.strip() for part in stripped.split("=", 1))
        raw = raw.split("#", 1)[0].strip()
        if not section and key == "model_catalog_json":
            if seen_catalog:
                raise SystemExit("Refusing config with duplicate top-level model_catalog_json entries")
            seen_catalog = True
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit("model_catalog_json must be a quoted string") from exc
            if not isinstance(value, str):
                raise SystemExit("model_catalog_json must be a quoted string")
            result[key] = value
        elif section == "[features]" and key == "fast_mode":
            if seen_fast:
                raise SystemExit("Refusing config with duplicate features.fast_mode entries")
            seen_fast = True
            if raw not in ("true", "false"):
                raise SystemExit("features.fast_mode must be true or false")
            result.setdefault("features", {})["fast_mode"] = raw == "true"
    return result


def check(codex_home: Path, require_fast: bool, validate_runtime: bool = True) -> int:
    source_path = codex_home / "models_cache.json"
    target_path = codex_home / MANAGED_CATALOG
    config_path = codex_home / "config.toml"
    source = load_catalog(source_path)
    if not shim_required(source):
        print("Stock catalog already routes Luna through Multi-Agent V2; the shim is no longer needed.")
        return 1 if parsed_config(config_path).get("model_catalog_json") == str(target_path) else 0
    if not target_path.exists():
        print(f"error: managed catalog is missing: {target_path}", file=sys.stderr)
        return 1
    target = load_catalog(target_path)
    expected = build_shim(source)
    violations: list[str] = []
    if target != expected:
        violations.append("managed catalog is stale or changes fields beyond Luna routing")
    config = parsed_config(config_path)
    if config.get("model_catalog_json") != str(target_path):
        violations.append("model_catalog_json does not point at the managed catalog")
    if require_fast and not bool(dict(config.get("features", {})).get("fast_mode")):
        violations.append("features.fast_mode is not enabled")
    if not violations and validate_runtime:
        validate_catalog_with_codex(target, codex_home)
    if violations:
        for violation in violations:
            print(f"error: {violation}", file=sys.stderr)
        return 1
    print("Luna Multi-Agent V2 compatibility shim is current and active.")
    return 0


def apply(codex_home: Path, enable_fast: bool, validate_runtime: bool = True) -> int:
    source_path = codex_home / "models_cache.json"
    target_path = codex_home / MANAGED_CATALOG
    config_path = codex_home / "config.toml"
    source = load_catalog(source_path)
    if not shim_required(source):
        print("Stock catalog already routes Luna through Multi-Agent V2; no compatibility shim applied.")
        return 0
    shim = build_shim(source)
    if validate_runtime:
        validate_catalog_with_codex(shim, codex_home)
    original = config_path.read_text() if config_path.exists() else ""
    lines = original.splitlines(keepends=True)
    lines = replace_top_level(lines, "model_catalog_json", str(target_path))
    if enable_fast:
        lines = enable_feature(lines, "fast_mode")
    rendered = "".join(lines)
    backup = backup_config(config_path, codex_home) if rendered != original else None
    atomic_write(target_path, json.dumps(shim, indent=2) + "\n", 0o600)
    if rendered != original:
        atomic_write(config_path, rendered, config_path.stat().st_mode & 0o777 if config_path.exists() else 0o600)
    print(f"Active compatibility catalog: {target_path}")
    if backup:
        print(f"Configuration backup: {backup}")
    print("Restart every Codex app/CLI process before testing native Luna subagents.")
    return 0


def disable(codex_home: Path) -> int:
    target_path = codex_home / MANAGED_CATALOG
    config_path = codex_home / "config.toml"
    config = parsed_config(config_path)
    current = config.get("model_catalog_json")
    if current not in (None, str(target_path)):
        raise SystemExit(f"Refusing to remove user-managed model_catalog_json: {current}")
    if config_path.exists() and current == str(target_path):
        original = config_path.read_text()
        rendered = "".join(replace_top_level(original.splitlines(keepends=True), "model_catalog_json", None))
        backup_config(config_path, codex_home)
        atomic_write(config_path, rendered, config_path.stat().st_mode & 0o777)
    if target_path.exists():
        target_path.unlink()
    print("Luna Multi-Agent V2 compatibility shim removed. Restart Codex.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--apply", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--disable", action="store_true")
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    parser.add_argument("--enable-fast-mode", action="store_true")
    args = parser.parse_args(argv)
    codex_home = Path(args.codex_home).expanduser().resolve()
    if args.apply:
        return apply(codex_home, args.enable_fast_mode)
    if args.check:
        return check(codex_home, args.enable_fast_mode)
    if args.enable_fast_mode:
        raise SystemExit("--enable-fast-mode is valid only with --apply or --check")
    return disable(codex_home)


if __name__ == "__main__":
    raise SystemExit(main())
