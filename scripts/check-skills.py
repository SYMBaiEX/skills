#!/usr/bin/env python3
"""Structural validation only; behavioral guarantees belong in executable tests/evaluations."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


def fail(message):
    raise SystemExit("error: " + message)


def main():
    names = set()
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        text = path.read_text()
        front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not front:
            fail(f"missing frontmatter: {path}")
        name_match = re.search(r"^name:\s*['\"]?([^'\"\n]+)", front.group(1), re.M)
        if not name_match or name_match.group(1).strip() != path.parent.name:
            fail(f"name does not match directory: {path}")
        name = path.parent.name
        if name in names:
            fail(f"duplicate name: {name}")
        names.add(name)
        if "[TODO" in text:
            fail(f"unfinished template: {path}")
        if len(text.splitlines()) > 500:
            fail(f"entrypoint exceeds 500 lines: {path}")
        metadata = path.parent / "agents" / "openai.yaml"
        if not metadata.is_file() or f"$" + name not in metadata.read_text():
            fail(f"missing invoking UI metadata: {metadata}")
        # Validate real links, not particular prose/heading choices.
        for relative in re.findall(r"\]\(([^)]+)\)", text):
            if relative.startswith(("http:", "https:", "#", "mailto:", "codex:", "/")):
                continue
            target = relative.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                fail(f"broken local reference {relative}: {path}")
    if not names:
        fail("no skills found")

    sys.path.insert(0, str(SKILLS / "gpt-engineer" / "scripts"))
    from routes import ROLES, SUPPORTED_MODELS
    from audit_routing import read_profile
    agents = SKILLS / "gpt-engineer" / "assets" / "codex" / "agents"
    if {p.name for p in agents.glob("*.toml")} != {r["profile"] for r in ROLES.values()}:
        fail("agent assets disagree with route registry")
    for name, route in ROLES.items():
        profile = read_profile(agents / route["profile"])
        if (profile.get("name"), profile.get("model"), profile.get("model_reasoning_effort"), profile.get("service_tier")) != (
            name.replace("-", "_"), route["model"], route["effort"], route.get("service_tier")
        ):
            fail(f"profile disagrees with registry: {name}")
        if route["model"] not in SUPPORTED_MODELS:
            fail(f"unsupported active model: {name}")
    schema = json.loads((SKILLS / "gpt-engineer" / "assets" / "codex" / "handoff.schema.json").read_text())
    if not {"requirement_ids", "gate_results", "docs_disposition"}.issubset(schema["required"]):
        fail("handoff schema omits evidence fields")
    if "skipped" not in schema["properties"]["gate_results"]["items"]["properties"]["status"]["enum"]:
        fail("handoff schema cannot report skipped checks")
    print(f"Validated {len(names)} skill structures and bundled route schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
