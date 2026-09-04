#!/usr/bin/env python3
"""Fail closed when a GPT Engineer custom-agent name can resolve to the wrong route."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_PARENT_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
EXPECTED = {
    "sol_engineer": ("gpt-5.6-sol", "high", None),
    "terra_explorer": ("gpt-5.6-terra", "medium", None),
    "terra_worker": ("gpt-5.6-terra", "medium", None),
    "luna_worker": ("gpt-5.6-luna", "low", None),
    "luna_max_worker": ("gpt-5.6-luna", "max", "fast"),
    "luna_verifier": ("gpt-5.6-luna", "medium", None),
}
APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
MANAGED_CATALOG = Path("model-catalogs/gpt-engineer-luna-v2.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_profile(path: Path) -> dict[str, object]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise SystemExit(f"Cannot parse custom agent profile {path}: {exc}") from exc
    profile: dict[str, object] = {}
    for field in ("name", "model", "model_reasoning_effort", "service_tier"):
        match = re.search(rf'(?m)^{field}\s*=\s*"([^"]*)"\s*$', text)
        if match:
            profile[field] = match.group(1)
    return profile


def profile_candidates(cwd: Path, codex_home: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for scope, directory in (
        ("project", cwd / ".codex" / "agents"),
        ("user", codex_home / "agents"),
    ):
        if directory.is_dir():
            candidates.extend((scope, path) for path in sorted(directory.glob("*.toml")))
    return candidates


def version_tuple(rendered: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", rendered)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def inspect_codex(source: str, executable: str, codex_home: Path) -> dict[str, object]:
    version_text = "unknown"
    version: tuple[int, ...] = ()
    features: dict[str, bool] = {}
    error: str | None = None
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(codex_home)
    environment.setdefault("TERM", "xterm-256color")
    try:
        version_result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=environment,
        )
        version_text = (version_result.stdout.strip() or version_result.stderr.strip())[:256]
        version = version_tuple(version_text)
        if version_result.returncode != 0:
            error = f"version probe exited {version_result.returncode}: {version_text}"
        else:
            feature_result = subprocess.run(
                [executable, "features", "list"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
                env=environment,
            )
            if feature_result.returncode != 0:
                detail = feature_result.stderr.strip() or feature_result.stdout.strip()
                error = f"config/feature probe exited {feature_result.returncode}: {detail[:512]}"
            else:
                for line in feature_result.stdout.splitlines():
                    fields = line.split()
                    if len(fields) >= 3 and fields[-1] in ("true", "false"):
                        features[fields[0]] = fields[-1] == "true"
    except (OSError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"[:512]
    return {
        "source": source,
        "path": executable,
        "version": version_text,
        "versionTuple": list(version),
        "configAccepted": error is None,
        "multiAgentEnabled": features.get("multi_agent"),
        "fastModeEnabled": features.get("fast_mode"),
        "error": error,
    }


def configured_catalog(config_path: Path) -> str | None:
    if not config_path.exists():
        return None
    section = ""
    values: list[str] = []
    for line in config_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped.split("#", 1)[0].strip()
            continue
        if section or not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = (part.strip() for part in stripped.split("=", 1))
        if key != "model_catalog_json":
            continue
        try:
            value = json.loads(raw.split("#", 1)[0].strip())
        except json.JSONDecodeError as exc:
            raise ValueError("model_catalog_json must be a quoted string") from exc
        if not isinstance(value, str):
            raise ValueError("model_catalog_json must be a quoted string")
        values.append(value)
    if len(values) > 1:
        raise ValueError("duplicate top-level model_catalog_json entries")
    return values[0] if values else None


def managed_catalog_audit(codex_home: Path) -> tuple[dict[str, object], list[str], list[str]]:
    violations: list[str] = []
    warnings: list[str] = []
    managed = (codex_home / MANAGED_CATALOG).resolve()
    try:
        configured = configured_catalog(codex_home / "config.toml")
    except (OSError, ValueError) as exc:
        return (
            {"configured": None, "managedPath": str(managed), "status": "invalid-config"},
            [f"cannot audit model catalog override: {exc}"],
            warnings,
        )
    result: dict[str, object] = {
        "configured": configured,
        "managedPath": str(managed),
        "status": "stock" if configured is None else "custom",
    }
    if configured is None:
        return result, violations, warnings
    configured_path = Path(configured).expanduser().resolve()
    if configured_path != managed:
        violations.append(
            "an unverified custom model_catalog_json is active; pinned-suite routing cannot attest it"
        )
        return result, violations, warnings
    source_path = codex_home / "models_cache.json"
    if not source_path.is_file() or not managed.is_file():
        result["status"] = "missing-managed-catalog"
        violations.append("the managed Luna compatibility catalog or its source cache is missing")
        return result, violations, warnings
    try:
        source = json.loads(source_path.read_text())
        target = json.loads(managed.read_text())
        source_models = {
            item.get("slug"): item
            for item in source.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("slug"), str)
        }
        target_models = {
            item.get("slug"): item
            for item in target.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("slug"), str)
        }
        luna_source = source_models["gpt-5.6-luna"]
        luna_target = target_models["gpt-5.6-luna"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        result["status"] = "invalid-managed-catalog"
        violations.append(f"cannot validate the managed Luna compatibility catalog: {exc}")
        return result, violations, warnings
    if luna_source.get("multi_agent_version") == "v2":
        result["status"] = "obsolete"
        violations.append("the stock catalog supports Luna V2; disable the compatibility override")
        return result, violations, warnings
    comparison = json.loads(json.dumps(target))
    for item in comparison.get("models", []):
        if not isinstance(item, dict):
            continue
        if item.get("slug") == "gpt-5.6-luna":
            item["multi_agent_version"] = luna_source.get("multi_agent_version")
        source_item = source_models.get(item.get("slug"))
        if isinstance(source_item, dict) and "supports_reasoning_summaries" not in source_item:
            item.pop("supports_reasoning_summaries", None)
    if comparison != source or luna_target.get("multi_agent_version") != "v2":
        result["status"] = "stale"
        violations.append(
            "the managed Luna compatibility catalog is stale or changes upstream metadata; disable it"
        )
        return result, violations, warnings
    result["status"] = "active-unsupported-override"
    warnings.append(
        "the Luna V2 compatibility catalog is current but freezes upstream metadata; prefer stock routing or the CLI compatibility adapter"
    )
    return result, violations, warnings


def audit_runtime(
    codex_home: Path,
    explicit_codex: str | None = None,
    candidates: list[tuple[str, str]] | None = None,
) -> dict[str, object]:
    violations: list[str] = []
    warnings: list[str] = []
    if candidates is None:
        discovered: list[tuple[str, str]] = []
        path_codex = shutil.which("codex")
        if path_codex:
            discovered.append(("path", path_codex))
        if APP_CODEX.is_file():
            discovered.append(("chatgpt-app", str(APP_CODEX)))
        candidates = [("explicit", explicit_codex)] if explicit_codex else discovered
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source, executable in candidates:
        resolved = str(Path(executable).expanduser().resolve())
        if resolved not in seen:
            unique.append((source, resolved))
            seen.add(resolved)
    inspected = [inspect_codex(source, executable, codex_home) for source, executable in unique]
    viable = [item for item in inspected if item["versionTuple"]]
    selected = max(viable, key=lambda item: tuple(item["versionTuple"])) if viable else None
    if selected is None:
        violations.append("no versioned Codex runtime was found")
    else:
        if not selected["configAccepted"]:
            violations.append(
                f"preferred Codex runtime rejects the active config: {selected['error']}"
            )
        elif selected["multiAgentEnabled"] is not True:
            violations.append("preferred Codex runtime does not report multi_agent enabled")
        path_runtime = next((item for item in inspected if item["source"] == "path"), None)
        if path_runtime and path_runtime["path"] != selected["path"]:
            warnings.append(
                f"PATH Codex {path_runtime['version']} is older than preferred {selected['version']}"
            )
        if path_runtime and not path_runtime["configAccepted"]:
            warnings.append("PATH Codex rejects the active config; update it or invoke the preferred runtime")
    catalog, catalog_violations, catalog_warnings = managed_catalog_audit(codex_home)
    violations.extend(catalog_violations)
    warnings.extend(catalog_warnings)
    return {
        "status": "passed" if not violations else "failed",
        "selected": selected,
        "candidates": inspected,
        "catalog": catalog,
        "warnings": warnings,
        "violations": violations,
    }


def audit(
    cwd: Path,
    codex_home: Path,
    parent_model: str | None,
    observed_routes: list[str] | None = None,
    include_runtime: bool = False,
    explicit_codex: str | None = None,
) -> dict[str, object]:
    violations: list[str] = []
    warnings: list[str] = []
    if parent_model and parent_model not in ALLOWED_PARENT_MODELS:
        violations.append(f"parent model is outside pinned-suite routing: {parent_model}")

    found: dict[str, list[dict[str, object]]] = {name: [] for name in EXPECTED}
    for scope, path in profile_candidates(cwd, codex_home):
        profile = read_profile(path)
        name = str(profile.get("name", ""))
        if name not in EXPECTED:
            continue
        model = str(profile.get("model", ""))
        effort = str(profile.get("model_reasoning_effort", ""))
        service_tier = str(profile.get("service_tier", "")) or None
        expected_model, expected_effort, expected_tier = EXPECTED[name]
        valid = model == expected_model and effort == expected_effort and service_tier == expected_tier
        found[name].append(
            {
                "scope": scope,
                "path": str(path),
                "sha256": sha256(path),
                "model": model,
                "reasoningEffort": effort,
                "serviceTier": service_tier,
                "valid": valid,
            }
        )
        if not valid:
            violations.append(
                f"{scope} profile {path} declares {name} as {model}/{effort}; "
                f"expected {expected_model}/{expected_effort}/{expected_tier or 'default'}"
            )

    for name, matches in found.items():
        if not matches:
            violations.append(f"missing installed custom agent profile: {name}")

    observed: list[dict[str, object]] = []
    for declaration in observed_routes or []:
        if "=" not in declaration:
            violations.append(
                f"invalid observed route {declaration!r}; expected agent_type=model[:effort]"
            )
            continue
        name, route = (part.strip() for part in declaration.split("=", 1))
        model, separator, effort = route.partition(":")
        expected = EXPECTED.get(name)
        valid = expected is not None and model == expected[0] and (
            not separator or effort == expected[1]
        )
        observed.append(
            {
                "agentType": name,
                "model": model,
                "reasoningEffort": effort if separator else None,
                "valid": valid,
            }
        )
        if expected is None:
            violations.append(f"observed unsupported agent type in pinned-suite mode: {name}")
        elif model != expected[0]:
            violations.append(
                f"observed route for {name} used {model or '(missing)'}; expected {expected[0]}"
            )
        elif separator and effort != expected[1]:
            violations.append(
                f"observed route for {name} used effort {effort or '(missing)'}; "
                f"expected {expected[1]}"
            )

    runtime = audit_runtime(codex_home, explicit_codex) if include_runtime else None
    if runtime:
        violations.extend(runtime["violations"])
        warnings.extend(runtime["warnings"])

    return {
        "status": "passed" if not violations else "failed",
        "cwd": str(cwd),
        "codexHome": str(codex_home),
        "parentModel": parent_model,
        "allowedParentModels": sorted(ALLOWED_PARENT_MODELS),
        "profiles": found,
        "observedRoutes": observed,
        "runtime": runtime,
        "warnings": warnings,
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".", help="Trusted repository root")
    parser.add_argument("--codex-home", help="Override CODEX_HOME")
    parser.add_argument("--parent-model", help="Observed parent model, when the runtime exposes it")
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Also validate the newest available Codex runtime, active config, and catalog override",
    )
    parser.add_argument(
        "--codex",
        help="Exact Codex executable to validate with --runtime instead of auto-selecting the newest",
    )
    parser.add_argument(
        "--observed-route",
        action="append",
        default=[],
        metavar="AGENT_TYPE=MODEL[:EFFORT]",
        help="Validate effective child metadata exported by the runtime; repeat for each child",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).expanduser().resolve()
    codex_home = Path(
        args.codex_home or os.environ.get("CODEX_HOME", "~/.codex")
    ).expanduser().resolve()
    if args.codex and not args.runtime:
        parser.error("--codex requires --runtime")
    result = audit(
        cwd,
        codex_home,
        args.parent_model,
        args.observed_route,
        args.runtime,
        args.codex,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "passed":
        print("GPT Engineer routing profiles passed strict pinned-suite audit.")
        for warning in result["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    else:
        for violation in result["violations"]:
            print(f"error: {violation}", file=sys.stderr)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
