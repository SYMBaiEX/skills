#!/usr/bin/env bash
# Follow-up round on the most recent run-team.sh session — this is the "Codex acts as the user
# reviewing design/work" step. Resumes the same session so the orchestrator keeps full context;
# it does not re-plan from scratch.
# Usage: resume-team.sh "<feedback or next instruction>"
#
# Must be run from the same working directory as the original run-team.sh call (session lookup
# is scoped to cwd and its git worktrees).
set -euo pipefail

FEEDBACK="${1:?Usage: resume-team.sh \"<feedback or next instruction>\"}"
STATE_DIR=".claude-team"
SESSION_FILE="$STATE_DIR/last-session-id"

if [[ ! -f "$SESSION_FILE" ]]; then
  echo "error: no prior session found at $SESSION_FILE. Run run-team.sh first." >&2
  exit 1
fi
SESSION_ID=$(cat "$SESSION_FILE")

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"

ARGS=(
  -p "$FEEDBACK"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --fallback-model "sonnet,haiku"
  --permission-mode "${PERMISSION_MODE:-acceptEdits}"
  --resume "$SESSION_ID"
  --output-format json
)
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

claude "${ARGS[@]}" | tee "$STATE_DIR/last-result.json"

jq -r '.session_id' "$STATE_DIR/last-result.json" > "$SESSION_FILE"
