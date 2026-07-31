#!/usr/bin/env python3
"""Repository-level structural checks for every published skill."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LATEST_ONLY = {
    "gpt-engineer",
    "gpt-orchestration",
    "gpt-orchestration-auto",
    "gpt-orchestration-build",
}
FLEET_LIFECYCLE = {
    "claude-multi-agent",
    "gpt-engineer",
    "gpt-engineer-spark",
    "gpt-orchestration",
    "gpt-orchestration-auto",
    "gpt-orchestration-build",
}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    names: set[str] = set()
    paths = sorted(SKILLS.glob("*/SKILL.md"))
    if not paths:
        fail("no skills found")

    for path in paths:
        text = path.read_text()
        match = re.match(r"^---\n(?P<frontmatter>.*?)\n---\n", text, re.S)
        if not match:
            fail(f"missing YAML frontmatter: {path}")
        name_match = re.search(r"^name:\s*['\"]?([^'\"\n]+)", match.group("frontmatter"), re.M)
        if not name_match:
            fail(f"missing name: {path}")
        name = name_match.group(1).strip()
        if name != path.parent.name:
            fail(f"name {name!r} does not match directory {path.parent.name!r}")
        if name in names:
            fail(f"duplicate skill name: {name}")
        names.add(name)
        if "[TODO" in text:
            fail(f"template TODO remains: {path}")
        if len(text.splitlines()) > 500:
            fail(f"SKILL.md exceeds 500 lines: {path}")

        metadata = path.parent / "agents" / "openai.yaml"
        if not metadata.exists():
            fail(f"missing agents/openai.yaml: {path.parent}")
        metadata_text = metadata.read_text()
        if f"${name}" not in metadata_text:
            fail(f"default prompt does not invoke ${name}: {metadata}")
        if name in LATEST_ONLY:
            lowered = text.lower()
            for required in (
                "latest-only is the default",
                "gpt-5.6-sol",
                "gpt-5.6-terra",
                "gpt-5.6-luna",
            ):
                if required not in lowered:
                    fail(f"latest-only contract missing {required!r}: {path}")
            for forbidden in (
                "use generic subagents only",
                "behavioral profiles only",
                "disclose same-model inheritance",
            ):
                if forbidden in lowered:
                    fail(f"fail-open routing phrase remains {forbidden!r}: {path}")
        if name == "gpt-engineer":
            for required in ("**fast:**", "delta-only", "explicitly"):
                if required not in text.lower():
                    fail(f"GPT Engineer fast-path contract missing {required!r}: {path}")
        if name == "gpt-engineer-spark":
            for required in ("explicitly requests spark", "not a gpt-5.6 latest-only route"):
                if required not in text.lower():
                    fail(f"Spark opt-in contract missing {required!r}: {path}")
        if name in FLEET_LIFECYCLE:
            lowered = text.lower()
            for required in ("teardown", "shared mcp"):
                if required not in lowered:
                    fail(f"fleet lifecycle contract missing {required!r}: {path}")

    sol_profile = SKILLS / "gpt-engineer" / "assets" / "codex" / "agents" / "sol-engineer.toml"
    if 'model = "gpt-5.6-sol"' not in sol_profile.read_text():
        fail(f"Sol profile is not explicitly pinned to gpt-5.6-sol: {sol_profile}")
    codex_runner = SKILLS / "gpt-engineer" / "scripts" / "run_codex_agent.py"
    if '"model": "gpt-5.6-sol"' not in codex_runner.read_text():
        fail(f"Codex fallback is not explicitly pinned to gpt-5.6-sol: {codex_runner}")
    luna_max = SKILLS / "gpt-engineer" / "assets" / "codex" / "agents" / "luna-max-worker.toml"
    luna_max_text = luna_max.read_text()
    for required in ('model = "gpt-5.6-luna"', 'model_reasoning_effort = "max"', 'service_tier = "fast"'):
        if required not in luna_max_text:
            fail(f"Luna Max/Fast profile is missing {required!r}: {luna_max}")

    print(f"Validated {len(names)} skill directories: {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
