#!/usr/bin/env bash
# True "give it a task and walk away" run: detaches a lifecycle-managed foreground runner and
# returns immediately. The runner owns its Claude child and handles INT/TERM/HUP/EXIT safely.
# Usage: launch-team-bg.sh "<task description>" [worktree-name]
#
# Defaults PERMISSION_MODE to bypassPermissions because a walk-away session with no human
# watching will otherwise stall forever the first time it hits a permission prompt.
# Read references/SAFETY.md before pointing this at anything with production credentials.
#
# Env overrides: see run-team.sh — IN_PLACE, CLAUDE_CODE_DISABLE_BACKGROUND_TASKS,
# CLAUDE_CODE_SUBAGENT_MODEL, MAX_TURNS, MAX_BUDGET_USD all apply here too.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

TASK="${1:?Usage: launch-team-bg.sh \"<task>\" [worktree-name]}"
WORKTREE="${2:-team-$(date +%s)}"
STATE_DIR=".claude-team"
mkdir -p "$STATE_DIR"

export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-sonnet}"
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="${CLAUDE_CODE_DISABLE_BACKGROUND_TASKS:-1}"

RUNNER_LOG="$STATE_DIR/bg-runner-${WORKTREE}.log"
nohup env \
  ORCHESTRATOR_MODEL="${ORCHESTRATOR_MODEL:-opus}" \
  PERMISSION_MODE="${PERMISSION_MODE:-bypassPermissions}" \
  CLAUDE_CODE_SUBAGENT_MODEL="$CLAUDE_CODE_SUBAGENT_MODEL" \
  CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="$CLAUDE_CODE_DISABLE_BACKGROUND_TASKS" \
  MAX_TURNS="${MAX_TURNS:-}" \
  MAX_BUDGET_USD="${MAX_BUDGET_USD:-}" \
  IN_PLACE="${IN_PLACE:-0}" \
  bash "$SCRIPT_DIR/run-team.sh" "$TASK" "$WORKTREE" > "$RUNNER_LOG" 2>&1 < /dev/null &
RUNNER_PID=$!
jq -n \
  --argjson pid "$RUNNER_PID" \
  --arg worktree "$WORKTREE" \
  --arg log "$RUNNER_LOG" \
  '{runnerPid: $pid, worktree: $worktree, log: $log, status: "running"}' \
  > "$STATE_DIR/background-runner.json"

echo >&2
echo "Lifecycle-managed runner launched (pid: $RUNNER_PID)." >&2
echo "Follow progress with: tail -f $RUNNER_LOG" >&2
echo "Before handoff, wait for the runner to exit and require last-result.json plus" >&2
echo "lifecycle.jsonl's runner_teardown_complete event; see references/HANDOFF-PROTOCOL.md." >&2
