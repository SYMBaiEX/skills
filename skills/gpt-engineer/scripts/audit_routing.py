#!/usr/bin/env python3
"""Fail closed when a GPT Engineer custom-agent name can resolve to the wrong route."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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


def audit(cwd: Path, codex_home: Path, parent_model: str | None) -> dict[str, object]:
    violations: list[str] = []
    if parent_model and parent_model not in ALLOWED_PARENT_MODELS:
        violations.append(f"parent model is outside latest-only routing: {parent_model}")

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

    return {
        "status": "passed" if not violations else "failed",
        "cwd": str(cwd),
        "codexHome": str(codex_home),
        "parentModel": parent_model,
        "allowedParentModels": sorted(ALLOWED_PARENT_MODELS),
        "profiles": found,
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".", help="Trusted repository root")
    parser.add_argument("--codex-home", help="Override CODEX_HOME")
    parser.add_argument("--parent-model", help="Observed parent model, when the runtime exposes it")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).expanduser().resolve()
    codex_home = Path(
        args.codex_home or os.environ.get("CODEX_HOME", "~/.codex")
    ).expanduser().resolve()
    result = audit(cwd, codex_home, args.parent_model)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "passed":
        print("GPT Engineer routing profiles passed strict latest-only audit.")
    else:
        for violation in result["violations"]:
            print(f"error: {violation}", file=sys.stderr)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
