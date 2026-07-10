#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_REF_REV="38a2ff82958afee88dadf4831509e6f7e9d8ef4e"
SKILLS_CLI_VERSION="1.5.15"

python3 "$ROOT/scripts/check-skills.py"
python3 "$ROOT/skills/gpt-engineer/scripts/test_bootstrap_codex.py"

for skill in "$ROOT"/skills/*; do
  if [[ -f "$skill/SKILL.md" ]]; then
    uvx --from "git+https://github.com/agentskills/agentskills.git@${SKILLS_REF_REV}#subdirectory=skills-ref" \
      skills-ref validate "$skill"
  fi
done

discovery="$(npx --yes "skills@${SKILLS_CLI_VERSION}" add "$ROOT" --list)"
for skill in "$ROOT"/skills/*; do
  if [[ -f "$skill/SKILL.md" ]]; then
    name="$(basename "$skill")"
    if ! grep -q "$name" <<<"$discovery"; then
      echo "skills CLI did not discover $name" >&2
      exit 1
    fi
  fi
done

echo "All skill validation checks passed."
