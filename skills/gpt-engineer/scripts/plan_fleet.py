#!/usr/bin/env python3
"""Produce a bounded GPT Engineer wave plan from live capacity and ready work."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


MODE_CEILINGS = {"fast": 1, "standard": 3, "broad": 6}


@dataclass(frozen=True)
class FleetPlan:
    mode: str
    runtime_child_cap: int
    policy_ceiling: int
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

    return FleetPlan(
        mode=mode,
        runtime_child_cap=runtime_child_cap,
        policy_ceiling=policy_ceiling,
        read_slots=read_slots,
        writer_slots=writer_slots,
        active_children=active_children,
        deferred_reads=ready_reads - read_slots,
        deferred_writers=ready_writers - writer_slots,
        reasons=tuple(reasons),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=tuple(MODE_CEILINGS), required=True)
    parser.add_argument("--runtime-child-cap", type=int, required=True)
    parser.add_argument("--ready-reads", type=int, default=0)
    parser.add_argument("--ready-writers", type=int, default=0)
    parser.add_argument("--writers-isolated", action="store_true")
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
