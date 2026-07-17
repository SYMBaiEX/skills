#!/usr/bin/env bash
# Append workflow/subagent lifecycle events for observability. Never blocks execution.
set -uo pipefail

INPUT=$(cat)
STATE_DIR="${CLAUDE_TEAM_STATE_DIR:-.claude-team}"
mkdir -p "$STATE_DIR"

printf '%s' "$INPUT" | jq -c '{
  hook_event_name,
  session_id,
  tool_name,
  agent_id,
  agent_type,
  task_id,
  workflow_input: (.tool_input | if type == "object" then {
    name,
    scriptPath,
    resumeFromRunId
  } else null end),
  workflow_result: (.tool_response | if type == "object" then {
    status,
    taskId,
    runId,
    transcriptDir,
    scriptPath,
    error
  } else null end)
}' >> "$STATE_DIR/workflow-events.jsonl" 2>/dev/null || true

exit 0
