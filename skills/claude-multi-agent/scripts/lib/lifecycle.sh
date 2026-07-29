#!/usr/bin/env bash
# Shared lifecycle handling for wrappers that start a Claude process themselves.
# It deliberately acts only on the recorded direct child and descendants observed
# from that child; it never searches by command name or touches shared MCP servers.

CLAUDE_TEAM_CHILD_PID=""
CLAUDE_TEAM_STATE_DIR=""
CLAUDE_TEAM_TEARDOWN_DONE=0

claude_team_lifecycle_event() {
  local event="$1"
  local detail="${2:-}"
  [[ -n "$CLAUDE_TEAM_STATE_DIR" ]] || return 0
  mkdir -p "$CLAUDE_TEAM_STATE_DIR"
  jq -cn --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg event "$event" --arg detail "$detail" \
    '{at: $at, event: $event, detail: $detail}' >> "$CLAUDE_TEAM_STATE_DIR/lifecycle.jsonl" 2>/dev/null || true
}

claude_team_init_lifecycle() {
  CLAUDE_TEAM_STATE_DIR="$1"
  mkdir -p "$CLAUDE_TEAM_STATE_DIR"
  claude_team_lifecycle_event "runner_started" "pid=$$"
}

claude_team_owned_descendants() {
  local parent="$1"
  local child
  while read -r child; do
    [[ -n "$child" ]] || continue
    claude_team_owned_descendants "$child"
    printf '%s\n' "$child"
  done < <(ps -axo pid=,ppid= | awk -v parent="$parent" '$2 == parent { print $1 }')
}

claude_team_terminate_owned_child() {
  local pid="$CLAUDE_TEAM_CHILD_PID"
  [[ -n "$pid" ]] || return 0
  if ! kill -0 "$pid" 2>/dev/null; then
    return 0
  fi

  local -a owned=()
  while read -r child; do
    [[ -n "$child" ]] && owned+=("$child")
  done < <(claude_team_owned_descendants "$pid")
  owned+=("$pid")
  claude_team_lifecycle_event "child_termination_requested" "root=$pid owned=${owned[*]}"
  kill -TERM "${owned[@]}" 2>/dev/null || true

  local deadline=$((SECONDS + ${CLAUDE_TEAM_TEARDOWN_TIMEOUT_SECONDS:-10}))
  while kill -0 "$pid" 2>/dev/null && (( SECONDS < deadline )); do
    sleep 0.1
  done
  if kill -0 "$pid" 2>/dev/null; then
    claude_team_lifecycle_event "child_termination_escalated" "root=$pid owned=${owned[*]}"
    kill -KILL "${owned[@]}" 2>/dev/null || true
  fi
  wait "$pid" 2>/dev/null || true
  CLAUDE_TEAM_CHILD_PID=""
  claude_team_lifecycle_event "child_reaped" "root=$pid"
}

claude_team_run_child() {
  local stdout_file="$1"
  local stderr_file="$2"
  shift 2
  "$@" >"$stdout_file" 2>"$stderr_file" &
  CLAUDE_TEAM_CHILD_PID=$!
  claude_team_lifecycle_event "child_started" "pid=$CLAUDE_TEAM_CHILD_PID command=$1"
}

claude_team_wait_for_child() {
  local pid="$CLAUDE_TEAM_CHILD_PID"
  [[ -n "$pid" ]] || return 0
  local status=0
  wait "$pid" || status=$?
  CLAUDE_TEAM_CHILD_PID=""
  claude_team_lifecycle_event "child_exited" "pid=$pid status=$status"
  return "$status"
}

claude_team_release_resources() {
  :
}

claude_team_teardown() {
  local status="$1"
  (( CLAUDE_TEAM_TEARDOWN_DONE == 0 )) || return 0
  CLAUDE_TEAM_TEARDOWN_DONE=1
  claude_team_terminate_owned_child
  claude_team_release_resources
  claude_team_lifecycle_event "runner_teardown_complete" "status=$status"
}

claude_team_handle_signal() {
  local signal="$1"
  local status="$2"
  claude_team_lifecycle_event "signal_received" "$signal"
  claude_team_teardown "$status"
  trap - EXIT
  exit "$status"
}

claude_team_install_lifecycle_traps() {
  trap 'claude_team_handle_signal INT 130' INT
  trap 'claude_team_handle_signal TERM 143' TERM
  trap 'claude_team_handle_signal HUP 129' HUP
  trap 'claude_team_teardown "$?"' EXIT
}
