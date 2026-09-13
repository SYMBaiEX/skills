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
MAX_INPUT_BYTES = 16_384


def _read_event():
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def main() -> int:
    try:
        event = _read_event()
    except (json.JSONDecodeError, OSError, TypeError, UnicodeDecodeError):
        return 0
    if not isinstance(event, dict):
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return 0
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
