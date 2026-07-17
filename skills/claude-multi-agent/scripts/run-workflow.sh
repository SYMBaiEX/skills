#!/usr/bin/env bash
# Run the bundled saved Claude dynamic workflow synchronously.
# Usage: run-workflow.sh "<engineering goal>" [worktree-name]
set -euo pipefail

TASK="${1:?Usage: run-workflow.sh \"<engineering goal>\" [worktree-name]}"
WORKTREE="${2:-workflow-$(date +%s)-$$}"
if [[ ! "$WORKTREE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: worktree name may contain only letters, numbers, dot, underscore, and hyphen." >&2
  exit 1
fi
if ! REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "error: run-workflow.sh must be invoked inside a Git worktree." >&2
  exit 1
fi
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)
INITIAL_STATUS=$(git -C "$REPO_ROOT" status --porcelain)
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
STATE_DIR_INPUT="${STATE_DIR:-$CLAUDE_HOME/workflow-runs/$WORKTREE}"
mkdir -p "$STATE_DIR_INPUT"
STATE_DIR=$(cd "$STATE_DIR_INPUT" && pwd)
PROJECT_WORKFLOW="$REPO_ROOT/.claude/workflows/gpt-engineer-dynamic.js"
GLOBAL_WORKFLOW="$CLAUDE_HOME/workflows/gpt-engineer-dynamic.js"

if ! command -v claude >/dev/null 2>&1; then
  echo "error: claude CLI is required and was not found on PATH." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required to capture the workflow result." >&2
  exit 1
fi

if [[ "${IN_PLACE:-0}" == "1" ]]; then
  if [[ ! -f "$GLOBAL_WORKFLOW" && ! -f "$PROJECT_WORKFLOW" ]]; then
    echo "error: gpt-engineer-dynamic.js is missing. Run scripts/bootstrap.sh --global or bootstrap the repository." >&2
    exit 1
  fi
else
  if [[ ! -f "$GLOBAL_WORKFLOW" ]]; then
    echo "error: $GLOBAL_WORKFLOW is missing. Run scripts/bootstrap.sh --global before isolated workflow runs." >&2
    exit 1
  fi
  if [[ -f "$PROJECT_WORKFLOW" ]] && ! cmp -s "$GLOBAL_WORKFLOW" "$PROJECT_WORKFLOW"; then
    echo "error: project and global gpt-engineer-dynamic.js definitions conflict; reconcile them before running." >&2
    exit 1
  fi
  if [[ -n "$INITIAL_STATUS" ]]; then
    echo "error: isolated workflow runs require a clean checkout. Commit first or set IN_PLACE=1 explicitly." >&2
    exit 1
  fi
fi

VERSION=$(claude --version | sed -E 's/[^0-9]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
MINIMUM="2.1.154"
if [[ "$(printf '%s\n%s\n' "$MINIMUM" "$VERSION" | sort -V | head -n1)" != "$MINIMUM" ]]; then
  echo "error: Claude Code $MINIMUM or later is required for dynamic workflows (found $VERSION)." >&2
  exit 1
fi

# A global override defeats the workflow's explicit Opus/Sonnet phase routing.
unset CLAUDE_CODE_SUBAGENT_MODEL
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS:-0}"
export CLAUDE_TEAM_STATE_DIR="$STATE_DIR"

ACCEPTANCE_JSON="${WORKFLOW_ACCEPTANCE_JSON:-[]}"
if ! jq -e 'type == "array" and all(.[]; type == "string")' <<<"$ACCEPTANCE_JSON" >/dev/null; then
  echo "error: WORKFLOW_ACCEPTANCE_JSON must be a JSON array of strings." >&2
  exit 1
fi
MAX_CYCLES_VALUE="${MAX_CYCLES:-2}"
if [[ ! "$MAX_CYCLES_VALUE" =~ ^[1-3]$ ]]; then
  echo "error: MAX_CYCLES must be 1, 2, or 3." >&2
  exit 1
fi
PAYLOAD=$(jq -cn \
  --arg goal "$TASK" \
  --arg scope "${WORKFLOW_SCOPE:-the current repository}" \
  --argjson acceptance "$ACCEPTANCE_JSON" \
  --argjson maxCycles "$MAX_CYCLES_VALUE" \
  '{goal: $goal, scope: $scope, acceptance: $acceptance, maxCycles: $maxCycles}')
OUTPUT_SCHEMA='{"type":"object","additionalProperties":true,"properties":{"status":{"enum":["complete","partial","blocked","failed"]},"complete":{"type":"boolean"},"cycles":{"type":"integer"},"gaps":{"type":"array","items":{"type":"string"}},"evidence":{"type":"array","items":{"type":"string"}}},"required":["status","complete","cycles","gaps","evidence"]}'

ARGS=(
  -p "/gpt-engineer-dynamic $PAYLOAD"
  --model "${ORCHESTRATOR_MODEL:-opus}"
  --effort "${WORKFLOW_EFFORT:-xhigh}"
  --permission-mode "${PERMISSION_MODE:-acceptEdits}"
  --output-format stream-json
  --json-schema "$OUTPUT_SCHEMA"
  --verbose
)
[[ -n "${FALLBACK_MODEL:-}" ]] && ARGS+=(--fallback-model "$FALLBACK_MODEL")
[[ -n "${MAX_TURNS:-}" ]] && ARGS+=(--max-turns "$MAX_TURNS")
[[ -n "${MAX_BUDGET_USD:-}" ]] && ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

LOG_FILE="$STATE_DIR/stream.jsonl"
RESULT_FILE="$STATE_DIR/last-result.json"
SEMANTIC_FILE="$STATE_DIR/workflow-result.json"
ENVELOPE_FILE="$STATE_DIR/result-envelope.json"
CHANGED_FILE="$STATE_DIR/changed-paths.json"
DELETED_FILE="$STATE_DIR/deleted-paths.json"
PATCH_FILE="$STATE_DIR/candidate.patch"
: > "$LOG_FILE"

EXECUTION_MODE="in-place"
EXECUTION_DIR="$REPO_ROOT"
CANDIDATE_PARENT=""
if ! BASE_COMMIT=$(git -C "$REPO_ROOT" rev-parse --verify HEAD 2>/dev/null); then
  BASE_COMMIT="unborn"
fi
cleanup() {
  if [[ -n "$CANDIDATE_PARENT" ]]; then
    git -C "$REPO_ROOT" worktree remove --force "$EXECUTION_DIR" >/dev/null 2>&1 || true
    rmdir "$CANDIDATE_PARENT" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ "${IN_PLACE:-0}" != "1" ]]; then
  if [[ "$BASE_COMMIT" == "unborn" ]]; then
    echo "error: isolated workflow runs require at least one commit; commit the baseline or set IN_PLACE=1." >&2
    exit 1
  fi
  EXECUTION_MODE="isolated-worktree"
  CANDIDATE_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/gpt-engineer-${WORKTREE}.XXXXXX")
  EXECUTION_DIR="$CANDIDATE_PARENT/worktree"
  git -C "$REPO_ROOT" worktree add --detach "$EXECUTION_DIR" HEAD >/dev/null
fi

set +e
(
  cd "$EXECUTION_DIR"
  claude "${ARGS[@]}"
) | tee "$LOG_FILE" | jq -c 'select(.type == "result")' > "$RESULT_FILE"
PIPE_CODES=("${PIPESTATUS[@]}")
set -e
CLAUDE_STATUS="${PIPE_CODES[0]}"
CANDIDATE_HEAD="$BASE_COMMIT"
CANDIDATE_COMMIT_VIOLATION=false

if [[ "$EXECUTION_MODE" == "isolated-worktree" ]]; then
  CANDIDATE_HEAD=$(git -C "$EXECUTION_DIR" rev-parse HEAD)
  if [[ "$CANDIDATE_HEAD" != "$BASE_COMMIT" ]]; then
    CANDIDATE_COMMIT_VIOLATION=true
  fi
  git -C "$EXECUTION_DIR" add -N --all
  git -C "$EXECUTION_DIR" diff --binary --no-ext-diff "$BASE_COMMIT" -- > "$PATCH_FILE"
  git -C "$EXECUTION_DIR" diff --name-only "$BASE_COMMIT" -- \
    | jq -Rsc 'split("\n") | map(select(length > 0))' > "$CHANGED_FILE"
  git -C "$EXECUTION_DIR" diff --name-only --diff-filter=D "$BASE_COMMIT" -- \
    | jq -Rsc 'split("\n") | map(select(length > 0))' > "$DELETED_FILE"
else
  if [[ "$BASE_COMMIT" == "unborn" ]]; then
    git -C "$REPO_ROOT" ls-files --cached --others --exclude-standard \
      | sort -u | jq -Rsc 'split("\n") | map(select(length > 0))' > "$CHANGED_FILE"
  else
    {
      git -C "$REPO_ROOT" diff --name-only HEAD --
      git -C "$REPO_ROOT" ls-files --others --exclude-standard
    } | sort -u | jq -Rsc 'split("\n") | map(select(length > 0))' > "$CHANGED_FILE"
  fi
  printf '[]\n' > "$DELETED_FILE"
  : > "$PATCH_FILE"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  echo "error: no final result event captured; inspect $LOG_FILE." >&2
  exit 1
fi

if [[ "$CLAUDE_STATUS" != "0" ]]; then
  echo "error: Claude Code exited with status $CLAUDE_STATUS; inspect $LOG_FILE." >&2
  exit 1
fi

jq -e '.is_error != true' "$RESULT_FILE" >/dev/null
if ! jq -e '.structured_output | type == "object"' "$RESULT_FILE" >/dev/null; then
  echo "error: final event did not contain the required structured workflow result." >&2
  exit 1
fi
jq '.structured_output' "$RESULT_FILE" > "$SEMANTIC_FILE"
WORKFLOW_OK=false
if jq -e '.complete == true and .status == "complete" and (.gaps | length == 0)' "$SEMANTIC_FILE" >/dev/null; then
  WORKFLOW_OK=true
fi
if [[ "$CANDIDATE_COMMIT_VIOLATION" == "true" ]]; then
  WORKFLOW_OK=false
fi
HAS_CHANGES=false
if jq -e 'length > 0' "$CHANGED_FILE" >/dev/null; then
  HAS_CHANGES=true
fi
REQUIRES_INTEGRATION=false
if [[ "$EXECUTION_MODE" == "isolated-worktree" && "$WORKFLOW_OK" == "true" && "$HAS_CHANGES" == "true" ]]; then
  REQUIRES_INTEGRATION=true
fi

jq -n \
  --arg schema "claude-dynamic-workflow/v1" \
  --arg mode "$EXECUTION_MODE" \
  --arg baseCommit "$BASE_COMMIT" \
  --arg candidateHead "$CANDIDATE_HEAD" \
  --arg candidatePatch "$PATCH_FILE" \
  --arg changedPathsFile "$CHANGED_FILE" \
  --arg deletedPathsFile "$DELETED_FILE" \
  --slurpfile workflow "$SEMANTIC_FILE" \
  --slurpfile changedPaths "$CHANGED_FILE" \
  --slurpfile deletedPaths "$DELETED_FILE" \
  --argjson workflowOk "$WORKFLOW_OK" \
  --argjson candidateCommitViolation "$CANDIDATE_COMMIT_VIOLATION" \
  --argjson requiresIntegration "$REQUIRES_INTEGRATION" \
  '{
    schema: $schema,
    status: (if $candidateCommitViolation then "failed" elif $workflowOk and $requiresIntegration then "partial" elif $workflowOk then "complete" elif $workflow[0].status == "complete" then "failed" else $workflow[0].status end),
    complete: ($workflowOk and ($requiresIntegration | not)),
    workflowComplete: $workflowOk,
    cycles: $workflow[0].cycles,
    gaps: (if $candidateCommitViolation then ["Candidate writer created one or more commits; changes were preserved but the run failed closed."] elif $requiresIntegration then ["Candidate changes require main-agent integration and verification."] elif ($workflowOk | not) and ($workflow[0].gaps | length == 0) then ["Semantic completion barrier was not satisfied."] else $workflow[0].gaps end),
    evidence: $workflow[0].evidence,
    executionMode: $mode,
    baseCommit: $baseCommit,
    candidateHeadCommit: $candidateHead,
    candidateCommitViolation: $candidateCommitViolation,
    changedPaths: $changedPaths[0],
    deletedPaths: $deletedPaths[0],
    candidatePatch: (if $mode == "isolated-worktree" then $candidatePatch else null end),
    changedPathsFile: $changedPathsFile,
    deletedPathsFile: $deletedPathsFile,
    requiresMainAgentIntegration: $requiresIntegration,
    semanticResult: $workflow[0]
  }' > "$ENVELOPE_FILE"
jq . "$ENVELOPE_FILE"

if [[ "$WORKFLOW_OK" != "true" ]]; then
  echo "error: workflow finished without satisfying the semantic completion barrier; inspect $SEMANTIC_FILE." >&2
  exit 2
fi
if [[ "$REQUIRES_INTEGRATION" == "true" ]]; then
  echo "candidate ready: integrate $PATCH_FILE, then verify the real checkout; inspect $ENVELOPE_FILE." >&2
  exit 3
fi
