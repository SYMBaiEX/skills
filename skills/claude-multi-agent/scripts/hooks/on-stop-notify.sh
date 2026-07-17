#!/usr/bin/env bash
# Stop hook: signals that the orchestrator session has finished. This is the file a walk-away
# poller (Codex or otherwise) should watch for instead of scraping `claude logs` output.
set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

STATE_DIR="${CLAUDE_TEAM_STATE_DIR:-.claude-team}"
mkdir -p "$STATE_DIR"

jq -n --arg id "$SESSION_ID" '{session_id: $id, status: "done"}' \
  > "$STATE_DIR/done-${SESSION_ID}.json" 2>/dev/null

exit 0
