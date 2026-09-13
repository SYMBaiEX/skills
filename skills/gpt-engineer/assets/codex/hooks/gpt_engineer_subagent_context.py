#!/usr/bin/env python3
import json
import sys


ALLOWED_ROLES = frozenset(
    {
        "astra_engineer",
        "astra_explorer",
        "astra_worker",
        "astra_verifier",
        "terra_explorer",
        "terra_worker",
        "luna_worker",
        "luna_max_worker",
        "luna_verifier",
    }
)
MAX_CONTEXT_BYTES = 1200
MAX_INPUT_BYTES = 16_384


def _read_event():
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _bounded_context(role: str) -> str:
    context = (
        f"Before {role} starts: read every applicable AGENTS.md file; capture git status; "
        "treat existing changes as user-owned; stay inside assigned paths; perform only authorized "
        "external side effects; and return a bounded handoff with stage status, file:symbol evidence, "
        "changed files, verification commands with pass/fail/skip/not-run truth, relevant requirement "
        "and gate IDs, blockers, documentation disposition when assigned, and one next action."
    )
    encoded = context.encode("utf-8")
    if len(encoded) <= MAX_CONTEXT_BYTES:
        return context
    return encoded[:MAX_CONTEXT_BYTES].decode("utf-8", "ignore")


def main() -> int:
    try:
        event = _read_event()
    except (json.JSONDecodeError, OSError, TypeError, UnicodeDecodeError):
        return 0
    if not isinstance(event, dict) or event.get("hook_event_name") != "SubagentStart":
        return 0
    role = event.get("agent_type")
    if not isinstance(role, str) or role not in ALLOWED_ROLES:
        return 0
    context = _bounded_context(role)
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
