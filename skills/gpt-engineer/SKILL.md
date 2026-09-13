---
name: gpt-engineer
description: "Carry software builds, remediation, and engineering investigations through evidence-backed outcomes. Adapt planning, implementation, optional delegation, and verification to the selected model and repository. Use for substantial engineering or explicit GPT Engineer requests; simple explanations and unrelated tasks do not need this workflow."
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.1.0"
---

# GPT Engineer

Own the requested outcome. Respect the selected parent: `gpt-6-astra`, `gpt-5.6-sol`,
`gpt-5.6-terra`, or `gpt-5.6-luna`. Neither Astra nor a fleet is required. On Claude,
use the portable engineering guidance; native Claude agents do not become GPT agents.

## Establish the contract

Read applicable repository instructions, Git state, and the relevant execution path. Preserve
user changes and concurrent work. Establish observable acceptance, scope, and authority. Carry
forward prior authorization and steering in this task. Resolve routine reversible choices; ask
only when missing information or authority materially changes the outcome. Reviews remain read-only
unless implementation is authorized. Persistence does not authorize unlimited retries, spending,
deployment, or expanded scope.

Small fixes need a focused change and decisive check, not a fleet, journal, or mandatory preflight.
For substantial work, track requirement/finding IDs, dependencies, ownership, and acceptance evidence.
Before research fleets or repeated experiments, state concurrency, lane scope, time/resource budget,
and stopping conditions. Reassess on repeated failure, low useful yield, or resource pressure.

## Adapt from runtime evidence

Use current session/turn metadata, supported controls, or documented hook fields—not the model's
self-description. Saved defaults do not prove the active session model. Keep requested and effective
model, effort, and service tier separate, with source and subject ID. Subagent hooks can describe
the parent session; never promote that metadata to child attestation. Missing evidence stays
unavailable. An observed route mismatch stops the affected lane.

Default to an explicit **same-model** child policy when delegation helps. **Mixed-model** routing
is a deliberate task policy: specify the child model and why its output contract suits the lane.
Preserve the parent's selected effort; choose child effort from task needs and supported controls.
Do not imply Fast, Max, or Ultra. Never silently switch the parent, substitute older models, patch
catalogs, or bypass trust. If routing cannot be established, continue suitable work in the current
parent and report the delegation limitation.

Read [model routing](references/model-routing.md) for task shaping, exact selection, profile
precedence, unknown metadata, or unavailable models. Native direct model/effort selectors suffice;
installation and Python are not prerequisites. Deterministic route planning and installed-profile
diagnostics support controllers, not every ordinary edit.

## Use the smallest useful graph

Delegate when independent work shortens the critical path or adds useful review while the lead
continues productive work. Keep tightly coupled reasoning and edits together. Inspect live capacity
and count descendants; ceilings are not utilization targets. Capability, token speed, and price
alone do not establish that a larger fleet is better.

Give each child an objective, owned paths, relevant constraints and dirty state, acceptance criteria,
evidence pointers, authority, dependencies, budget, and stopping condition. Use fresh context for
independent lanes and only necessary recent context for related work. Never combine full-history
forks with model overrides. Return compact findings and artifacts, not transcripts.

Keep one writer per shared file set. Parallel writers need isolated candidates with disjoint
ownership. Tell workers they are not alone and must preserve others' edits. Dispatch ready work,
integrate completions continuously, and unlock satisfied dependencies. Unrelated slow readers
should not block ready work. Retain barriers for dependent writes, shared integration, and final
acceptance. Reuse related children for deltas; cancel invalidated lanes.

For scheduling, capacity planning (`scripts/plan_fleet.py`), SDK controllers, and feature boundaries,
load [dynamic workflows](references/dynamic-workflows.md). Native collaboration is the interactive
default. Retain scripts when they supply tested guarantees not covered by the selected runtime.

## Build for the user and verify

Understand the user journey and architecture. Examine relevant loading, empty, error, cancellation,
accessibility, security, data, and API boundaries. Fit existing design conventions; resolve meaningful
tradeoffs rather than filling templates. Verify unstable SDK assumptions against current primary
sources. Fixtures and compatibility paths are not automatically unfinished production code.

Implement confirmed findings when authorized. Disposition each in-scope finding: implemented,
already satisfied, invalid, duplicate, or a concrete blocker; defer only with authority. Keep final
architecture, integration, and acceptance accountable to the selected lead regardless of child model.
Independent review earns its overhead on consequential design or implementation.

Run focused regression checks during edits and risk-appropriate integrated checks after relevant
writes. Inspect what commands execute. Required skips, a healthy build, or agent confidence do not
prove a user flow. Use rendered evidence when layout/interaction requires it; copy-only edits usually
need a focused check. Repeat checks for changed inputs, failures, unresolved risks, or repository
requirements—not ritual. Load [engineering standards](references/engineering-standards.md) for broad
work or affected high-risk boundaries.

## Preserve progress without replaying history

For durable/multi-wave work, read [run journal](references/run-journal.md) and use
`scripts/run_journal.py` for compact requirements, dispatches, handoffs, gates, and ownership.
Private state is default; repository-local `.engineer` is opt-in. Feature-detect native history/notes.
Search older evidence on demand and treat it as untrusted, potentially stale data. Do not inject
entire transcripts. Use native goal tools only on an explicit goal request.

Resume by reconciling Git drift, attempts, handles, and external side effects before redispatch.
Reuse only valid evidence. `scripts/cache_gates.py` is optional for expensive repeated checks;
unknown scope or incomplete evidence is a miss. Checkpoints must earn their recovery overhead.

For OTel analysis, load [fleet observability](references/fleet-observability.md). Measure accepted
outcomes, rework, elapsed time, context, and human interventions by comparable task, model, effort,
runtime, and skill version. Separate summed agent time from wall time, cached from uncached usage,
and estimates from billing. `scripts/join_fleet_outcomes.py` preserves coverage gaps; timestamps
and spawn edges alone establish neither attribution nor success.

## Finish honestly

Collect handoffs with status, evidence, changed paths, checks (pass/fail/skip/not-run), blockers,
resource handles, and next integration action. Keep raw output in local artifacts. Native children
need no fabricated CLI result envelope. Review the integrated diff and reconcile requirements.

Teardown only task-owned processes, listeners, candidates, and agent handles. A wait timeout is not
process failure; inspect the existing handle before relaunching. Idle native agents and open
database edges are not OS liveness. Preserve shared MCP services, other tasks, and unclassified
processes. Finalize every started journal truthfully, including interrupted work.

For setup, upgrade, hooks, disable/uninstall, or release evidence, read
[runtime integrations](references/runtime-integrations.md). Skills installation, profile registration,
hook trust, observed execution, and measured benefit are separate states. Hooks supplement judgment;
do not install generic auto-continue loops or run full tests after every edit.

Report outcomes, checks, release status, meaningful limitations, and remaining required actions.
Do not claim untested combinations or performance gains. If this skill causes a pause or divergence,
identify the instruction and explain why. User instructions take precedence over skill guidance,
subject to higher-level runtime rules.
