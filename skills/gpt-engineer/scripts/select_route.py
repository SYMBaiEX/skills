#!/usr/bin/env python3
"""Plan a native route from caller-supplied runtime evidence; never spawn or change config.

This validates evidence structure, not its authenticity. Collect evidence from the owning runtime.
Saved settings and SubagentStart/Stop common fields cannot attest the active child model.
"""
from __future__ import annotations

import argparse
import json
import sys

from routes import SUPPORTED_MODELS

MAX_INPUT = 32768
PARENT_EVENTS = frozenset({"SessionStart", "SessionEnd", "PreToolUse", "PostToolUse",
                          "PermissionRequest", "UserPromptSubmit", "Stop", "Interrupt",
                          "PreCompact", "PostCompact"})


def hook_identity(event: dict) -> dict:
    """Whitelist metadata only. Never return transcript, prompt, command or arbitrary fields."""
    if not isinstance(event, dict):
        raise ValueError("hook payload must be an object")
    name = event.get("hook_event_name")
    model = event.get("model")
    scoped = name in PARENT_EVENTS
    return {"scope": "parent" if scoped else "unavailable",
            "source": "codex-hook" if scoped else "unavailable",
            "hookEventName": name if scoped else None,
            "model": model if scoped and model in SUPPORTED_MODELS else None,
            "effort": None, "serviceTier": None}


def _object(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object")
    return value


def plan(document: dict) -> dict:
    _object(document, "request")
    policy = document.get("policy", "same-model")
    if policy not in ("same-model", "mixed-model"):
        raise ValueError("policy must be same-model or mixed-model")
    parent = _object(document.get("parent", {}), "parent")
    child = _object(document.get("child", {}), "child")
    capabilities = _object(document.get("capabilities", {}), "capabilities")
    effective = _object(document.get("effectiveChild", {}), "effectiveChild")
    # A saved preference or claimed identity is not evidence of this turn's model.
    trusted = parent.get("source") in ("runtime-session", "runtime-turn", "codex-hook")
    if parent.get("source") == "codex-hook":
        trusted = parent.get("hookEventName") in PARENT_EVENTS
    parent_model = parent.get("model") if trusted else None
    for label, value in (("parent", parent_model), ("child", child.get("model"))):
        if value is not None and value not in SUPPORTED_MODELS:
            raise ValueError(label + " model outside supported contract")
    model = child.get("model") or (parent_model if policy == "same-model" else None)
    if policy == "same-model" and parent_model and model != parent_model:
        raise ValueError("same-model child differs from observed parent")
    if policy == "mixed-model" and not child.get("model"):
        raise ValueError("mixed-model requires an explicit child model")
    result = {"schema": "gpt-engineer-route/v1", "policy": policy,
              "parent": {"effectiveModel": parent_model, "source": parent.get("source", "unavailable")},
              "requested": {"model": model, "effort": child.get("effort"),
                            "serviceTier": child.get("serviceTier")},
              "effectiveChild": {"model": None, "effort": None, "serviceTier": None},
              "action": "parent-only", "spawn": None, "reason": None}
    if policy == "same-model" and parent_model is None:
        result["reason"] = "active parent model unavailable; do not guess a child route"
        return result
    models = capabilities.get("models", [])
    efforts = _object(capabilities.get("efforts", {}), "capabilities.efforts")
    tiers = capabilities.get("serviceTiers", [])
    if not isinstance(models, list) or not isinstance(tiers, list):
        raise ValueError("capability models and serviceTiers must be lists")
    effort = child.get("effort")
    if effort is None and trusted:
        effort = parent.get("effort")
    result["requested"]["effort"] = effort
    if not capabilities.get("modelSelector") or model not in models:
        result["reason"] = "exact model selector or requested model unavailable"
        return result
    if not capabilities.get("effortSelector") or not isinstance(effort, str) or effort not in efforts.get(model, []):
        result["reason"] = "choose an explicit supported effort; do not inherit an unintended default"
        return result
    if model == "gpt-6-astra" and effort in ("none", "minimal"):
        raise ValueError("Astra does not support none/minimal")
    tier = child.get("serviceTier")
    if tier is not None and (not capabilities.get("tierSelector") or tier not in tiers):
        result["reason"] = "explicit service tier unavailable; do not silently drop it"
        return result
    spawn = {"model": model, "reasoning_effort": effort, "fork_turns": "none"}
    if tier is not None:
        spawn["service_tier"] = tier
    if effective:
        # Require an independently identified child; parent-session metadata is insufficient.
        subject = effective.get("subjectId")
        expected_child = document.get("childId")
        if effective.get("source") not in ("runtime-child", "runtime-child-turn") or not expected_child or subject != expected_child or subject == parent.get("subjectId"):
            raise ValueError("effective child evidence is not independently attributed")
        for field, requested in (("model", model), ("effort", effort), ("serviceTier", tier)):
            value = effective.get(field)
            if value is not None and requested is not None and value != requested:
                raise ValueError("observed child route mismatch: " + field)
            result["effectiveChild"][field] = value
    result.update(action="native-direct", spawn=spawn, reason="supported explicit request; effective fields remain unavailable unless independently exported")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook-identity", action="store_true", help="Normalize one Codex hook payload without persisting it")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("input exceeds 32 KiB")
        request = json.loads(raw)
        result = hook_identity(request) if args.hook_identity else plan(request)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
