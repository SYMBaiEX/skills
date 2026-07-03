#!/usr/bin/env bash
# True "give it a task and walk away" run: starts a background Claude Code session and returns
# immediately. Check back with check-team.sh, `claude logs <id>`, or `claude attach <id>`.
# Usage: launch-team-bg.sh "<task description>" [worktree-name]
#
# Defaults PERMISSION_MODE to bypassPermissions because a walk-away session with no human
# watching will otherwise stall forever the first time it hits a permission prompt.
# Read references/SAFETY.md before pointing this at anything with production credentials.
set -euo pipefail

TASK="${1:?Usage: launch-team-bg.sh \"<task>\" [worktree-name]}"
WORKTREE="${2:-team-$(date +%s)}"
STATE_DIR=".claude-team"
mkdir -p "$STATE_DIR"

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"

ARGS=(
  --bg "$TASK"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --fallback-model "sonnet,haiku"
  --permission-mode "${PERMISSION_MODE:-bypassPermissions}"
  --worktree "$WORKTREE"
)
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

claude "${ARGS[@]}" | tee "$STATE_DIR/last-bg-launch.log"

echo >&2
echo "Session launched in the background (worktree: $WORKTREE)." >&2
echo "Poll with: bash \"$(dirname "${BASH_SOURCE[0]}")/check-team.sh\" [session-id]" >&2
echo "Completion marker will appear at: $STATE_DIR/done-<session_id>.json" >&2
