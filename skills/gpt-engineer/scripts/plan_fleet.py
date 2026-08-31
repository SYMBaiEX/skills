#!/usr/bin/env python3
"""Produce a bounded GPT Engineer wave plan from live capacity and ready work."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

MODE_CEILINGS = {"fast": 1, "standard": 3, "broad": 6, "team": 8}


def invalidate_gates(changed_paths, gate_scopes):
    """Pure deterministic invalidation for exact paths, globs, global and unknown scopes."""
    changed = tuple(sorted({str(path) for path in changed_paths}))
    if not changed:
        return ()
    if any(
        not ((scopes,) if isinstance(scopes, str) else tuple(scopes or ()))
        or any(
            scope in ("*", "global", "unknown")
            for scope in ((scopes,) if isinstance(scopes, str) else tuple(scopes or ()))
        )
        for scopes in gate_scopes.values()
    ):
        return tuple(sorted(gate_scopes))
    invalid = []
    for gate, scopes in sorted(gate_scopes.items()):
        values = (scopes,) if isinstance(scopes, str) else tuple(scopes or ())
        if any(
            any(
                fnmatch.fnmatch(path, scope)
                or path == scope
                or path.startswith(scope.rstrip("/") + "/")
                or scope.startswith(path.rstrip("/") + "/")
                for path in changed
            )
            for scope in values
        ):
            invalid.append(gate)
    return tuple(invalid)


def resume_plan(stages, gate_truth, changed_paths=(), gate_scopes=None):
    """Determine a stable next wave while refusing unsafe graph/scope states.

    Stages are mappings with ``id``, optional ``deps``, ``kind`` (read/write),
    and optional ``scope``/``writer_scope``.  gate_truth maps ids to passed
    truth records/bools.  The returned counts feed :func:`plan_fleet`.
    """
    gate_scopes = gate_scopes or {}
    indexed = {}
    for stage in stages:
        item = dict(stage)
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in indexed:
            raise ValueError("stages require unique non-empty ids")
        if item.get("kind", "read") not in ("read", "write"):
            raise ValueError("stage kind must be read or write")
        if item.get("status", "pending") not in (
            "pending",
            "ready",
            "running",
            "completed",
            "failed",
            "blocked",
            "interrupted",
        ):
            raise ValueError("invalid stage status")
        indexed[identifier] = item

    def deps(stage):
        values = stage.get("dependencies", stage.get("deps", ()))
        if isinstance(values, str) or not isinstance(values, (list, tuple)):
            raise ValueError("stage dependencies must be a list")
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("stage dependencies must contain non-empty ids")
        return tuple(values)

    for identifier, stage in indexed.items():
        for dependency in deps(stage):
            if dependency not in indexed:
                raise ValueError("missing dependency: " + str(dependency))
    visiting, visited = set(), set()

    def visit(identifier):
        if identifier in visiting:
            raise ValueError("cycle detected")
        if identifier not in visited:
            visiting.add(identifier)
            for dependency in deps(indexed[identifier]):
                visit(dependency)
            visiting.remove(identifier)
            visited.add(identifier)

    for identifier in sorted(indexed):
        visit(identifier)
    invalidated = set(invalidate_gates(changed_paths, gate_scopes))

    def passed(identifier):
        value = gate_truth.get(identifier)
        return value is True or (
            isinstance(value, dict)
            and value.get("exit_code") == 0
            and value.get("complete") is True
            and not value.get("truncated")
            and value.get("status") in ("passed", "success")
        )

    # A stage's historical completion is invalid only through its output gates.
    requeued = {
        identifier
        for identifier, stage in indexed.items()
        if (set(stage.get("produces_gates", ())) | {identifier}) & invalidated
    }
    completed = {
        identifier
        for identifier, stage in indexed.items()
        if stage.get("status") == "completed"
        or ("status" not in stage and passed(identifier))
    }
    completed -= requeued
    running = {
        identifier
        for identifier, stage in indexed.items()
        if stage.get("status") == "running"
    }
    terminal_bad = {
        identifier
        for identifier, stage in indexed.items()
        if stage.get("status") in ("failed", "blocked")
        or (
            isinstance(gate_truth.get(identifier), dict)
            and gate_truth[identifier].get("status") in ("failed", "blocked")
        )
    }
    ready_stages, deferred, blocked = [], [], []
    for identifier in sorted(indexed):
        stage = indexed[identifier]
        if identifier in completed:
            continue
        if identifier in running:
            deferred.append(identifier)
            continue
        if identifier in terminal_bad:
            blocked.append(identifier)
            continue
        dependencies = deps(stage)
        if any(dep in terminal_bad for dep in dependencies):
            blocked.append(identifier)
            continue
        if not all(dep in completed for dep in dependencies):
            deferred.append(identifier)
            continue
        required = set(stage.get("required_gates", ()))
        if any(gate in invalidated or not passed(gate) for gate in required):
            failed = any(
                isinstance(gate_truth.get(gate), dict)
                and gate_truth[gate].get("status") in ("failed", "blocked")
                for gate in required
            )
            (blocked if failed else deferred).append(identifier)
            continue
        ready_stages.append(stage)
    writers = [stage for stage in ready_stages if stage.get("kind", "read") == "write"]
    scopes = []
    for stage in writers:
        stage_scopes = stage.get(
            "writer_scopes", (stage.get("writer_scope", stage.get("scope", "unknown")),)
        )
        if isinstance(stage_scopes, str):
            stage_scopes = (stage_scopes,)
        if not stage_scopes or not all(
            isinstance(scope, str) and scope for scope in stage_scopes
        ):
            raise ValueError("writers require non-empty path scopes")
        for scope in stage_scopes:
            for old, owner in scopes:
                if owner == stage["id"]:
                    continue
                if (
                    scope == "unknown"
                    or old == "unknown"
                    or scope == old
                    or fnmatch.fnmatch(scope, old)
                    or fnmatch.fnmatch(old, scope)
                    or scope.startswith(old.rstrip("/") + "/")
                    or old.startswith(scope.rstrip("/") + "/")
                ):
                    raise ValueError("overlapping active writer scopes")
            scopes.append((scope, stage["id"]))
    ready = tuple(stage["id"] for stage in ready_stages)
    return {
        "ready": ready,
        "deferred": tuple(deferred),
        "blocked": tuple(blocked),
        "completed": tuple(sorted(completed)),
        "invalidated": tuple(sorted(invalidated)),
        "ready_reads": sum(
            stage.get("kind", "read") != "write" for stage in ready_stages
        ),
        "ready_writers": len(writers),
    }


@dataclass(frozen=True)
class FleetPlan:
    mode: str
    runtime_child_cap: int
    policy_ceiling: int
    team_qualified: bool
    routes_attested: bool
    lanes_independent: bool
    paired_comparison: bool
    read_slots: int
    writer_slots: int
    active_children: int
    deferred_reads: int
    deferred_writers: int
    reasons: tuple[str, ...]


def plan_fleet(
    *,
    mode: str,
    runtime_child_cap: int,
    ready_reads: int,
    ready_writers: int,
    writers_isolated: bool = False,
    team_qualified: bool = False,
    routes_attested: bool = False,
    lanes_independent: bool = False,
    paired_comparison: bool = False,
    resource_pressure: bool = False,
    previous_failure_rate: float = 0.0,
) -> FleetPlan:
    if mode not in MODE_CEILINGS:
        raise ValueError(f"unsupported mode: {mode}")
    for name, value in (
        ("runtime_child_cap", runtime_child_cap),
        ("ready_reads", ready_reads),
        ("ready_writers", ready_writers),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    if not 0.0 <= previous_failure_rate <= 1.0:
        raise ValueError("previous_failure_rate must be between 0 and 1")
    if mode == "team":
        if not team_qualified:
            raise ValueError("team mode requires explicit qualification")
        if not routes_attested:
            raise ValueError("team mode requires exact route attestation")
        if not lanes_independent:
            raise ValueError("team mode requires independent decision-bearing lanes")
        if not paired_comparison:
            raise ValueError("team mode requires a paired outcome comparison")
        if ready_writers:
            raise ValueError("team mode is read-only; plan writers in a broad wave")
        if ready_reads < 7:
            raise ValueError(
                "team mode requires at least seven independent ready reads"
            )
        if runtime_child_cap < 7:
            raise ValueError(
                "team mode requires live capacity for at least seven children"
            )
        if resource_pressure:
            raise ValueError(
                "team mode is unavailable under resource pressure; use broad mode"
            )
        if previous_failure_rate >= 0.20:
            raise ValueError(
                "team mode requires a previous failure rate below 20%; use broad mode"
            )

    reasons: list[str] = []
    policy_ceiling = min(runtime_child_cap, MODE_CEILINGS[mode])
    if ready_writers:
        write_ceiling = 4 if writers_isolated else 3
        policy_ceiling = min(runtime_child_cap, MODE_CEILINGS[mode], write_ceiling)
        writer_limit = 2 if writers_isolated else 1
        writer_slots = min(ready_writers, writer_limit, policy_ceiling)
        if not writers_isolated:
            reasons.append("shared-checkout writing is serialized")
        else:
            reasons.append("isolated writers are capped at two")
    else:
        writer_slots = 0

    if resource_pressure:
        policy_ceiling = min(policy_ceiling, 2)
        writer_slots = min(writer_slots, policy_ceiling)
        reasons.append("resource pressure shrank the wave to two children")
    elif previous_failure_rate >= 0.20:
        policy_ceiling = min(policy_ceiling, 3)
        writer_slots = min(writer_slots, policy_ceiling)
        reasons.append("previous failure rate of at least 20% shrank the wave")

    read_slots = min(ready_reads, max(0, policy_ceiling - writer_slots))
    active_children = writer_slots + read_slots
    if active_children < ready_reads + ready_writers:
        reasons.append("ready work exceeds the current bounded wave")
    if active_children == 0:
        reasons.append("no ready work or no live child capacity")
    if mode == "broad" and not ready_writers and active_children == 6:
        reasons.append("six independent read lanes fill the Broad ceiling")
    if mode == "team" and active_children >= 7:
        reasons.append("qualified read-only lanes use the experimental Team ceiling")

    return FleetPlan(
        mode=mode,
        runtime_child_cap=runtime_child_cap,
        policy_ceiling=policy_ceiling,
        team_qualified=team_qualified,
        routes_attested=routes_attested,
        lanes_independent=lanes_independent,
        paired_comparison=paired_comparison,
        read_slots=read_slots,
        writer_slots=writer_slots,
        active_children=active_children,
        deferred_reads=ready_reads - read_slots,
        deferred_writers=ready_writers - writer_slots,
        reasons=tuple(reasons),
    )


def _resume_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-json", required=True)
    parser.add_argument("--gate-truth-json", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--gate-scopes-json")
    args = parser.parse_args(argv)
    try:
        stages = json.loads(Path(args.workflow_json).read_text())
        truth = json.loads(Path(args.gate_truth_json).read_text())
        scopes = (
            json.loads(Path(args.gate_scopes_json).read_text())
            if args.gate_scopes_json
            else {}
        )
        if (
            not isinstance(stages, list)
            or not isinstance(truth, dict)
            or not isinstance(scopes, dict)
        ):
            raise ValueError(
                "workflow must be a list and gate truth/scopes must be objects"
            )
        print(
            json.dumps(
                resume_plan(stages, truth, args.changed_path, scopes), sort_keys=True
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--workflow-json" in argv:
        return _resume_main(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=tuple(MODE_CEILINGS), required=True)
    parser.add_argument("--runtime-child-cap", type=int, required=True)
    parser.add_argument("--ready-reads", type=int, default=0)
    parser.add_argument("--ready-writers", type=int, default=0)
    parser.add_argument("--writers-isolated", action="store_true")
    parser.add_argument("--team-qualified", action="store_true")
    parser.add_argument("--routes-attested", action="store_true")
    parser.add_argument("--lanes-independent", action="store_true")
    parser.add_argument("--paired-comparison", action="store_true")
    parser.add_argument("--resource-pressure", action="store_true")
    parser.add_argument("--previous-failure-rate", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = plan_fleet(
            mode=args.mode,
            runtime_child_cap=args.runtime_child_cap,
            ready_reads=args.ready_reads,
            ready_writers=args.ready_writers,
            writers_isolated=args.writers_isolated,
            team_qualified=args.team_qualified,
            routes_attested=args.routes_attested,
            lanes_independent=args.lanes_independent,
            paired_comparison=args.paired_comparison,
            resource_pressure=args.resource_pressure,
            previous_failure_rate=args.previous_failure_rate,
        )
    except ValueError as exc:
        parser.error(str(exc))
    payload = asdict(plan)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{plan.active_children} children: {plan.read_slots} read, "
            f"{plan.writer_slots} write; {plan.deferred_reads + plan.deferred_writers} deferred"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
