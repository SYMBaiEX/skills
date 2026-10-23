---
name: gpt-engineer
description: "Complete substantial software builds, remediation, and engineering investigations with verified outcomes. Use for multi-step engineering work or explicit GPT Engineer requests."
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.3.0"
---

# GPT Engineer

Own the requested outcome through implementation and verification. Preserve the selected parent
model and effort. GPT-6.1 Sol handles demanding child work; GPT-6 Luna handles focused, repeatable
lanes. Astra is parent-only by this skill's policy. Never silently substitute a model or provider.
On Claude, use the portable workflow with Claude-native routing.

## Establish the contract

Read applicable repository instructions, Git state, and the execution path relevant to the task.
Preserve user and concurrent edits. Establish scope, authority, and observable acceptance. Carry
forward authorization and steering; resolve routine reversible choices without asking again.
Reviews remain read-only unless implementation is authorized. Continue through in-scope fixes and
required checks; persistence does not expand scope, spending, deployment authority, or runtime limits.
A small fix needs a focused change and decisive check, without mandatory journals or preflights.

For substantial work, track requirements, finding dispositions, dependencies, ownership, and evidence
in a compact plan. Work in the intended workspace; shell cwd does not change writable roots.
Diagnose repeated approval friction using [runtime integrations](references/runtime-integrations.md#approval-reviews).

## Route from evidence

Use current runtime metadata and exposed selectors. Saved defaults, profile names, and model
self-description do not prove the active route. Keep requested and observed model, effort, and
service tier separate, with subject identity. Parent hook fields do not attest a child's model.
Missing evidence stays unavailable; a confirmed mismatch stops that lane.

Under a 6.1 Sol or Luna parent, use same-model children by default. Cross-model delegation is an
explicit choice justified by the lane. Astra and older parents require explicit 6.1 Sol/Luna child
selection. Preserve the parent; do not patch catalogs or permissions to obtain another route.
If selection is unavailable, continue suitable work in the parent and report the limitation.

Choose supported child effort for the work; do not maximize it automatically. Codex and API controls
differ. Named custom-agent settings can override spawn settings. Native read-only role instructions
do not create a separate sandbox. For exact precedence, compatibility, and profiles, load
[model routing](references/model-routing.md). No install or Python helper is required for native work.

## Delegate useful independent work

Use subagents when independent work shortens the critical path or provides worthwhile review while
the lead works. Keep coupled reasoning and edits together. Inspect live capacity, count descendants,
and state lane scope and resource limits before a fleet or repeated experiment. Capacity is a ceiling,
not a target. Keep one writer for shared files; isolate parallel candidates with disjoint ownership.

Give each child one outcome, owned paths, relevant constraints and dirty state, acceptance criteria,
evidence pointers, authority, dependencies, and an escalation condition. Tell workers they are not
alone and must preserve others' edits. Use fresh context and a compact packet for independent lanes;
reuse related children for deltas. Never combine full-history forks with model overrides.

Integrate completions as dependencies permit; unrelated slow readers need not block ready work.
Keep barriers for dependent writes, shared integration, and final acceptance. Cancel invalidated
lanes. Return findings, changed paths, checks, blockers, and handles rather than transcripts.
For scheduling, capacity planning, or API controllers, load
[dynamic workflows](references/dynamic-workflows.md); native collaboration is the interactive default.

## Spend context on decisions

Search narrowly before reading whole files or discovering an entire tool catalog. Batch independent
reads and calls; keep dependent operations sequential. Filter large results before returning them
and keep raw artifacts local. Read selected instruction files completely, budgeting them separately
if necessary. After truncation, retrieve the missing range or narrow the query instead of repeating
the same dump. Reuse verified findings until inputs change; a copied instruction is not new evidence.

Keep one handle for a running command. A wait timeout is not a failed process; inspect that handle
before relaunching. Use event-driven completion or bounded waits, do useful work while waiting, and
back off unchanged polling. Change approach after repeated identical failures without new evidence.
Honor explicit limits and runtime constraints. Productive multi-hour work and compaction are not
reasons to stop; use [long-running work](references/long-running-work.md) for recovery and prompt tuning.

## Build and verify

Understand the user journey and architecture. Address relevant loading, empty, error, cancellation,
accessibility, security, data, and API boundaries. Fit existing conventions. Verify unstable SDK
assumptions against current primary sources. A fixture or compatibility path is not automatically
unfinished production code. Disposition each finding: implemented, already satisfied, invalid,
duplicate, or concretely blocked; defer only with authority.

Run the cheapest decisive regression check during edits and required integrated checks after relevant
writes finish. Inspect what commands execute. Recheck only when inputs changed, a check failed,
an unresolved risk remains, or repository requirements demand it. Broad repeated testing and repeated
review before later writes consume time without preserving acceptance evidence. Use rendered evidence
when behavior or layout requires it. A green build, skipped check, or child summary is not flow proof.
Load [engineering standards](references/engineering-standards.md) for broad work or high-risk boundaries.

## Recover and finish honestly

For durable multi-wave work, use [run journal](references/run-journal.md): compact requirements,
decisions, evidence, changed paths, live handles, and next action. Private state is default;
repository-local `.engineer` is opt-in. Reconcile Git drift and external side effects before retrying
or redispatching. Native history is optional; never inject entire transcripts. Native goal tools
require an explicit goal request. Checkpoints must earn their recovery cost.

Review the integrated diff and reconcile acceptance. Report checks as pass/fail/skip/not-run and
release state truthfully. Finalize started journals, including interrupted work. Teardown only
recorded task-owned processes, listeners, candidates, and agent handles. Idle agents or open database
edges are not OS liveness; preserve shared MCP services, other tasks, and unclassified processes.

For trace analysis and tuning, load [fleet observability](references/fleet-observability.md).
Separate retained coverage, historical routing, loaded-skill evidence, runtime usage, and accepted
outcomes. Neither installation nor a structural test proves runtime invocation or a performance gain.
For setup, hooks, upgrade, and uninstall, load [runtime integrations](references/runtime-integrations.md).
Do not install generic auto-continue hooks or tests-after-every-edit loops.

Report outcomes, verification, release status, and meaningful limitations concisely. Progress updates
should add evidence or decisions. User instructions take precedence over skill guidelines, subject
to runtime rules. If this skill causes a pause or divergence, identify the exact instruction and why.
