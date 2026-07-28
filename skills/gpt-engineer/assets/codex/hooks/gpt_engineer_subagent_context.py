#!/usr/bin/env python3
import json
import sys


def main() -> int:
    event = json.load(sys.stdin)
    agent_type = event.get("agent_type", "subagent")
    context = (
        f"Before {agent_type} starts: read every applicable AGENTS.md file; capture git status; "
        "treat existing changes as user-owned; stay inside assigned paths; avoid external side effects; "
        "and return a bounded handoff with stage status, file:symbol evidence, changed files, "
        "verification commands, blockers, and one next action."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
