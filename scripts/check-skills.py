#!/usr/bin/env python3
"""Repository-level structural checks for every published skill."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LATEST_ONLY = {
    "gpt-engineer",
    "gpt-engineer-mem",
    "gpt-orchestration",
    "gpt-orchestration-auto",
    "gpt-orchestration-build",
}
FLEET_LIFECYCLE = {
    "claude-multi-agent",
    "gpt-engineer",
    "gpt-engineer-mem",
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
            for required in (
                "**fast:**",
                "delta-only",
                "explicitly",
                "scripts/plan_fleet.py",
                "scripts/run_journal.py",
                "scripts/cache_gates.py",
                "scripts/join_fleet_outcomes.py",
                "references/run-journal.md",
                "six for a broad read-heavy wave",
                "--team-qualified",
                "--routes-attested",
                "--lanes-independent",
                "--paired-comparison",
                "native 5.6 custom agents for normal interactive fleets",
                "codex sdk/app-server",
                "--compatibility-reason",
                "audit_routing.py --cwd <repo> --runtime",
                "do not spend a separate synthetic model turn merely to test routing",
            ):
                if required not in text.lower():
                    fail(f"GPT Engineer fast-path contract missing {required!r}: {path}")
        if name == "gpt-engineer-spark":
            for required in ("explicitly requests spark", "not a gpt-5.6 latest-only route"):
                if required not in text.lower():
                    fail(f"Spark opt-in contract missing {required!r}: {path}")
        if name == "gpt-engineer-mem":
            lowered = text.lower()
            for required in (
                "search` → `timeline`",
                "memory is an optional accelerator",
                "do not directly write to",
                "shared mcp services",
            ):
                if required not in lowered:
                    fail(f"GPT Engineer Mem contract missing {required!r}: {path}")
        if name in FLEET_LIFECYCLE:
            lowered = text.lower()
            for required in ("teardown", "shared mcp"):
                if required not in lowered:
                    fail(f"fleet lifecycle contract missing {required!r}: {path}")

    sol_profile = SKILLS / "gpt-engineer" / "assets" / "codex" / "agents" / "sol-engineer.toml"
    if 'model = "gpt-5.6-sol"' not in sol_profile.read_text():
        fail(f"Sol profile is not explicitly pinned to gpt-5.6-sol: {sol_profile}")
    codex_runner = SKILLS / "gpt-engineer" / "scripts" / "run_codex_agent.py"
    codex_runner_text = codex_runner.read_text()
    if '"model": "gpt-5.6-sol"' not in codex_runner_text:
        fail(f"Codex compatibility adapter is not explicitly pinned to gpt-5.6-sol: {codex_runner}")
    for required in (
        "--compatibility-reason",
        "codex-cli-compatibility-adapter",
        "native-routing-unavailable",
        '"routeAttestation": "requested-only"',
        '"providerEffectiveModelAttested": False',
    ):
        if required not in codex_runner_text:
            fail(f"Codex compatibility adapter is missing {required!r}: {codex_runner}")
    fleet_planner = SKILLS / "gpt-engineer" / "scripts" / "plan_fleet.py"
    if not fleet_planner.is_file():
        fail(f"GPT Engineer adaptive fleet planner is missing: {fleet_planner}")
    fleet_auditor = SKILLS / "gpt-engineer" / "scripts" / "audit_fleet.py"
    if not fleet_auditor.is_file():
        fail(f"GPT Engineer fleet auditor is missing: {fleet_auditor}")
    for relative in (
        "scripts/run_journal.py",
        "scripts/cache_gates.py",
        "scripts/join_fleet_outcomes.py",
        "references/run-journal.md",
    ):
        required_path = SKILLS / "gpt-engineer" / relative
        if not required_path.is_file():
            fail(f"GPT Engineer durable-state resource is missing: {required_path}")
    engineering_standards = (
        SKILLS / "gpt-engineer" / "references" / "engineering-standards.md"
    )
    if not engineering_standards.is_file():
        fail(f"GPT Engineer standards reference is missing: {engineering_standards}")
    handoff_schema = (
        SKILLS / "gpt-engineer" / "assets" / "codex" / "handoff.schema.json"
    )
    schema = json.loads(handoff_schema.read_text())
    required_handoff = {
        "requirement_ids",
        "gate_results",
        "docs_disposition",
    }
    if not required_handoff.issubset(set(schema.get("required", []))):
        fail(f"GPT Engineer handoff evidence fields are not required: {handoff_schema}")
    gate_statuses = set(
        schema["properties"]["gate_results"]["items"]["properties"]["status"]["enum"]
    )
    if "skipped" not in gate_statuses:
        fail(f"GPT Engineer gate results cannot report skipped checks: {handoff_schema}")
    luna_max = SKILLS / "gpt-engineer" / "assets" / "codex" / "agents" / "luna-max-worker.toml"
    luna_max_text = luna_max.read_text()
    for required in ('model = "gpt-5.6-luna"', 'model_reasoning_effort = "max"', 'service_tier = "fast"'):
        if required not in luna_max_text:
            fail(f"Luna Max/Fast profile is missing {required!r}: {luna_max}")

    print(f"Validated {len(names)} skill directories: {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
