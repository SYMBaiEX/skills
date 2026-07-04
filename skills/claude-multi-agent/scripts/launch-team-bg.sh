#!/usr/bin/env bash
# True "give it a task and walk away" run: starts a background Claude Code session and returns
# immediately. Check back with check-team.sh, `claude logs <id>`, or `claude attach <id>`.
# Usage: launch-team-bg.sh "<task description>" [worktree-name]
#
# Defaults PERMISSION_MODE to bypassPermissions because a walk-away session with no human
# watching will otherwise stall forever the first time it hits a permission prompt.
# Read references/SAFETY.md before pointing this at anything with production credentials.
#
# Env overrides: see run-team.sh — IN_PLACE, CLAUDE_CODE_DISABLE_BACKGROUND_TASKS,
# CLAUDE_CODE_SUBAGENT_MODEL, MAX_TURNS, MAX_BUDGET_USD all apply here too.
set -euo pipefail

TASK="${1:?Usage: launch-team-bg.sh \"<task>\" [worktree-name]}"
WORKTREE="${2:-team-$(date +%s)}"
STATE_DIR=".claude-team"
mkdir -p "$STATE_DIR"

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="${CLAUDE_CODE_DISABLE_BACKGROUND_TASKS:-1}"

ARGS=(
  --bg "$TASK"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --fallback-model "sonnet,haiku"
  --permission-mode "${PERMISSION_MODE:-bypassPermissions}"
  --append-system-prompt "Subagents you spawn in this session run in the foreground: the Agent tool call itself blocks until the subagent returns a result. Do not poll, sleep, or use Monitor to wait for a subagent to finish — there is nothing to wait for beyond the tool call already returning."
)
if [[ "${IN_PLACE:-0}" != "1" ]]; then
  ARGS+=(--worktree "$WORKTREE")
fi
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

claude "${ARGS[@]}" | tee "$STATE_DIR/last-bg-launch.log"

echo >&2
if [[ "${IN_PLACE:-0}" == "1" ]]; then
  echo "Session launched in the background (in-place, no worktree)." >&2
else
  echo "Session launched in the background (worktree: $WORKTREE)." >&2
fi
echo "Poll with: bash \"$(dirname "${BASH_SOURCE[0]}")/check-team.sh\" [session-id]" >&2
echo "Completion marker will appear at: $STATE_DIR/done-<session_id>.json" >&2
echo "That marker means the orchestrator's own turn ended, not necessarily that every subagent" >&2
echo "it spawned has finished — see references/HANDOFF-PROTOCOL.md for why this default now" >&2
echo "forces subagents to run in the foreground instead of relying on the marker alone." >&2
