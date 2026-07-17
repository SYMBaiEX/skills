#!/usr/bin/env bash
# Installs the claude-multi-agent subagents, settings, and hooks into a target repo's .claude/.
# Usage: bootstrap.sh [target-repo-path]  (defaults to the current directory)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GLOBAL=0
if [[ "${1:-}" == "--global" ]]; then
  GLOBAL=1
  CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  mkdir -p "$CLAUDE_HOME"
  TARGET_CLAUDE="$(cd "$CLAUDE_HOME" && pwd)"
  TARGET=""
else
  TARGET="$(cd "${1:-.}" && pwd)"
  TARGET_CLAUDE="$TARGET/.claude"
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "warning: 'claude' CLI not found on PATH. Install Claude Code before running the other scripts in this skill." >&2
fi

mkdir -p "$TARGET_CLAUDE/agents" "$TARGET_CLAUDE/workflows"
if [[ "$GLOBAL" == "0" ]]; then
  mkdir -p "$TARGET_CLAUDE/hooks"
fi

install_file() {
  local source="$1"
  local destination="$2"
  if [[ -e "$destination" ]]; then
    if ! cmp -s "$source" "$destination"; then
      echo "error: refusing to overwrite conflicting file: $destination" >&2
      exit 1
    fi
    return
  fi
  cp "$source" "$destination"
}

for source in "$SKILL_DIR"/assets/agents/*.md; do
  install_file "$source" "$TARGET_CLAUDE/agents/$(basename "$source")"
done
for source in "$SKILL_DIR"/assets/workflows/*.js; do
  install_file "$source" "$TARGET_CLAUDE/workflows/$(basename "$source")"
done
if [[ "$GLOBAL" == "0" ]]; then
  for source in "$SKILL_DIR"/scripts/hooks/*.sh; do
    install_file "$source" "$TARGET_CLAUDE/hooks/$(basename "$source")"
  done
  chmod +x "$TARGET_CLAUDE"/hooks/*.sh
fi

if [[ "$GLOBAL" == "1" ]]; then
  echo "Installed Claude subagents and gpt-engineer-dynamic workflow into $TARGET_CLAUDE"
  echo "Project hooks/settings remain opt-in; run bootstrap.sh /path/to/repository for them."
  exit 0
fi

if [[ -f "$TARGET_CLAUDE/settings.json" ]]; then
  echo "warning: $TARGET_CLAUDE/settings.json already exists — not overwriting." >&2
  echo "         merge assets/settings.json by hand: $SKILL_DIR/assets/settings.json" >&2
else
  cp "$SKILL_DIR/assets/settings.json" "$TARGET_CLAUDE/settings.json"
fi

echo "Installed subagents, gpt-engineer-dynamic workflow, settings, and hooks into $TARGET_CLAUDE/"
echo "Next: cd $TARGET && bash $SKILL_DIR/scripts/run-team.sh \"<task>\""
