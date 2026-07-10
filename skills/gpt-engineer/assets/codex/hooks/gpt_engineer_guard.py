#!/usr/bin/env python3
import json
import re
import sys


BLOCKED = (
    (re.compile(r"(?:^|[;&|]\s*)git\s+reset\s+--hard(?:\s|$)", re.I), "git reset --hard"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+checkout\s+--(?:\s|$)", re.I), "git checkout --"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+clean\s+[^\n;&|]*-[a-z]*f[a-z]*(?:\s|$)", re.I), "forced git clean"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+push\s+[^\n;&|]*(?:--force(?:-with-lease)?|-f)(?:\s|$)", re.I), "forced git push"),
)


def main() -> int:
    event = json.load(sys.stdin)
    command = str(event.get("tool_input", {}).get("command", ""))
    for pattern, label in BLOCKED:
        if pattern.search(command):
            json.dump(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"GPT Engineer guard blocked {label}. Use a non-destructive command or disable the project hook after explicit human review."
                        ),
                    }
                },
                sys.stdout,
            )
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
