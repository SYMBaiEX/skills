#!/usr/bin/env python3
"""Repository-level structural checks for every published skill."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


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

    print(f"Validated {len(names)} skill directories: {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
