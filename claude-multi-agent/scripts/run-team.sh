#!/usr/bin/env bash
# Synchronous, blocking Opus-orchestrator / Sonnet-subagent run.
# Usage: run-team.sh "<task description>" [worktree-name]
#
# Env overrides:
#   ORCHESTRATOR_MODEL   default: opus
#   PERMISSION_MODE      default: acceptEdits   (see references/SAFETY.md)
#   MAX_TURNS            optional turn cap
#   MAX_BUDGET_USD        optional spend cap
#   CLAUDE_CODE_SUBAGENT_MODEL   default: sonnet (forces every subagent's model)
set -euo pipefail

TASK="${1:?Usage: run-team.sh \"<task>\" [worktree-name]}"
WORKTREE="${2:-team-$(date +%s)}"
STATE_DIR=".claude-team"
mkdir -p "$STATE_DIR"

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"

ARGS=(
  -p "$TASK"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --fallback-model "sonnet,haiku"
  --permission-mode "${PERMISSION_MODE:-acceptEdits}"
  --worktree "$WORKTREE"
  --output-format json
)
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

claude "${ARGS[@]}" | tee "$STATE_DIR/last-result.json"

SESSION_ID=$(jq -r '.session_id' "$STATE_DIR/last-result.json")
echo "$SESSION_ID" > "$STATE_DIR/last-session-id"
printf 'session_id=%s (worktree: %s)\n' "$SESSION_ID" "$WORKTREE" >&2
