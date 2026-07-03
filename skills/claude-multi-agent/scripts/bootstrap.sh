#!/usr/bin/env bash
# Installs the claude-multi-agent subagents, settings, and hooks into a target repo's .claude/.
# Usage: bootstrap.sh [target-repo-path]  (defaults to the current directory)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$(cd "${1:-.}" && pwd)"

if ! command -v claude >/dev/null 2>&1; then
  echo "warning: 'claude' CLI not found on PATH. Install Claude Code before running the other scripts in this skill." >&2
fi

mkdir -p "$TARGET/.claude/agents" "$TARGET/.claude/hooks"

cp "$SKILL_DIR"/assets/agents/*.md "$TARGET/.claude/agents/"
cp "$SKILL_DIR"/scripts/hooks/*.sh "$TARGET/.claude/hooks/"
chmod +x "$TARGET"/.claude/hooks/*.sh

if [[ -f "$TARGET/.claude/settings.json" ]]; then
  echo "warning: $TARGET/.claude/settings.json already exists — not overwriting." >&2
  echo "         merge assets/settings.json by hand: $SKILL_DIR/assets/settings.json" >&2
else
  cp "$SKILL_DIR/assets/settings.json" "$TARGET/.claude/settings.json"
fi

echo "Installed subagents (planner, engineer, reviewer, tester) + settings + hooks into $TARGET/.claude/"
echo "Next: cd $TARGET && bash $SKILL_DIR/scripts/run-team.sh \"<task>\""
