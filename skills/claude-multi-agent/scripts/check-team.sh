#!/usr/bin/env bash
# Check on background sessions started with launch-team-bg.sh.
# Usage:
#   check-team.sh                 # list all sessions (running + completed) for this repo
#   check-team.sh <session-id>    # tail that session's recent output
set -euo pipefail

ID="${1:-}"

if [[ -n "$ID" ]]; then
  claude logs "$ID"
else
  claude agents --json --cwd "$(pwd)" --all
fi
