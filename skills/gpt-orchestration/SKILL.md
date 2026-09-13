---
name: gpt-orchestration
description: "Coordinate a requested coding-agent fleet with bounded ownership, dependency-aware handoffs, and integrated verification. Use for explicit orchestration or parallel-specialist requests; ordinary engineering can use GPT Engineer directly."
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.1.0"
---

# GPT Orchestration

Use the installed GPT Engineer core when available; load its dynamic-workflow reference only for
nontrivial scheduling. This is an orchestration entry point, not another routing policy or a reason
to load every engineer wrapper. A Skills CLI installation does not resolve dependencies or register
agents and hooks.

Preserve the selected parent (`gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, or
`gpt-5.6-luna`). Same-model delegation is explicit by default; mixed-model lanes require a deliberate
policy and exact child selection. Never infer execution from profiles or model self-description.
If the core or native delegation is absent, explain the limitation and perform suitable work directly;
do not switch models or install a framework automatically. Claude native routing stays provider-specific.

For the requested fleet, inspect live capacity and active descendants. State lane and resource
budgets. Partition independent decisions or subsystems; assign one accountable integrator.
Give each lane objective, owned paths, prerequisites, authority, checks, compact output and stop
condition. Preserve dirty work; keep shared files under one writer and isolate parallel candidates.
Workers are not alone and must not revert others' edits.

Dispatch ready work while the lead works. Integrate results as they arrive, then unlock dependencies;
do not wait on unrelated readers. Retain integration and final acceptance barriers. Reuse a related
child for a delta, cancel invalidated work, and prevent recursive fan-out beyond the root budget.
A fleet request warrants useful delegation or an explicit runtime limitation, not empty busywork.

When implementation is authorized, carry findings through evidence-backed disposition, build,
integration, and proportionate verification. Reviews alone do not authorize edits. Every handoff
includes status, evidence, changed paths, checks, blockers, and owned resource handles. Inspect
artifacts rather than trusting summaries. Keep full logs outside prompts.

Teardown only this task's agents, processes, listeners, and temporary candidates after preserving
evidence. Idle handles or open database edges do not establish OS liveness. Preserve shared MCP
services, other tasks, user work, and unclassified processes. Report integrated outcomes, remaining
gaps, verification, and requested versus effective routing honestly.
