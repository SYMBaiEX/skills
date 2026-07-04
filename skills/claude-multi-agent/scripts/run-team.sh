#!/usr/bin/env bash
# Synchronous, blocking Opus-orchestrator / Sonnet-subagent run.
# Usage: run-team.sh "<task description>" [worktree-name]
#
# Env overrides:
#   ORCHESTRATOR_MODEL             default: opus
#   PERMISSION_MODE                default: acceptEdits   (see references/SAFETY.md)
#   MAX_TURNS                      optional turn cap
#   MAX_BUDGET_USD                 optional spend cap
#   CLAUDE_CODE_SUBAGENT_MODEL     default: sonnet (forces every subagent's model)
#   CLAUDE_CODE_DISABLE_BACKGROUND_TASKS   default: 1 (forces subagents to run in the
#                                   foreground so the orchestrator can't end its turn
#                                   while one is still working — see references/HANDOFF-PROTOCOL.md)
#   IN_PLACE                       set to 1 to skip --worktree and operate directly on the
#                                   current checkout, e.g. when it has uncommitted changes
#                                   you need present (see references/SAFETY.md)
set -euo pipefail

TASK="${1:?Usage: run-team.sh \"<task>\" [worktree-name]}"
WORKTREE="${2:-team-$(date +%s)}"
STATE_DIR=".claude-team"
mkdir -p "$STATE_DIR"

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="${CLAUDE_CODE_DISABLE_BACKGROUND_TASKS:-1}"

ARGS=(
  -p "$TASK"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --fallback-model "sonnet,haiku"
  --permission-mode "${PERMISSION_MODE:-acceptEdits}"
  --output-format stream-json
  --verbose
  --append-system-prompt "Subagents you spawn in this session run in the foreground: the Agent tool call itself blocks until the subagent returns a result. Do not poll, sleep, or use Monitor to wait for a subagent to finish — there is nothing to wait for beyond the tool call already returning."
)
if [[ "${IN_PLACE:-0}" != "1" ]]; then
  ARGS+=(--worktree "$WORKTREE")
fi
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

LOG_FILE="$STATE_DIR/stream.jsonl"
: > "$LOG_FILE"

# tee the full turn-by-turn stream to a file Codex (or you) can `tail -f` for a liveness
# signal, while filtering out just the final `result` event for the last-result.json contract.
claude "${ARGS[@]}" | tee "$LOG_FILE" | jq -c 'select(.type == "result")' > "$STATE_DIR/last-result.json"

if [[ ! -s "$STATE_DIR/last-result.json" ]]; then
  echo "error: no final result event captured — the run may have errored or been interrupted." >&2
  echo "       check $LOG_FILE for the full turn-by-turn transcript before assuming it hung." >&2
  exit 1
fi

SESSION_ID=$(jq -r '.session_id' "$STATE_DIR/last-result.json")
echo "$SESSION_ID" > "$STATE_DIR/last-session-id"
if [[ "${IN_PLACE:-0}" == "1" ]]; then
  printf 'session_id=%s (in-place, no worktree)\n' "$SESSION_ID" >&2
else
  printf 'session_id=%s (worktree: %s)\n' "$SESSION_ID" "$WORKTREE" >&2
fi
