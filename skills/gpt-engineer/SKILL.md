---
name: gpt-engineer
description: "Deliver software-engineering outcomes with GPT-6 Astra: investigate the codebase, implement findings, coordinate useful parallel agents, and verify the integrated result. Use for autonomous engineering, substantial builds or remediation, explicit coding fleets, and durable goal-driven work. Astra is the default; mixed-model economy routing is an explicit option."
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.0.1"
---

# GPT Engineer

Own the requested engineering outcome through implementation and verification. Start with one Astra
agent. Add delegation only when independent work shortens the critical path or adds valuable review;
complexity alone does not require a fleet.

## Carry the user's intent through completion

Treat an action request as authorization to do the work within its stated and implied scope. Carry
forward earlier authorization, constraints, and corrections. Resolve routine reversible choices
from repository evidence; continue independent work while material questions are pending. Prepare
the concrete result before asking for any genuinely missing consequential decision. A side question
or steering message updates the ongoing task unless the user replaces it.

User instructions take precedence over this skill's guidance, subject to the runtime's higher-level
rules. If a skill causes a pause, identify the exact file and instruction and explain why it applies.
Do not invent an approval requirement from a guideline or ask again for already authorized work.

Read the applicable repository instructions, current Git state, relevant code and commands. Preserve
user-owned changes and concurrent work. Establish observable acceptance criteria and actual external
boundaries. For broad work, assign stable requirement and finding IDs; for a small fix, a compact plan
and direct evidence suffice. Use native `/goal` tooling only when the user requests a durable goal.

Load supporting guidance only when it changes the next decision:

- [Astra and Codex routing](references/codex-astra.md): profile selection, setup, migration, hooks,
  compatibility adapter, or model-specific behavior.
- [Dynamic workflows](references/dynamic-workflows.md): dependent stages, async work, SDK/API
  controllers, steering, or multiple providers.
- [Engineering standards](references/engineering-standards.md): broad work or relevant API, data,
  security, user-experience, performance, and release boundaries.
- [Run journal](references/run-journal.md): durable or multi-wave work, resumption, and gate reuse.
- [Fleet observability](references/fleet-observability.md): OTel, usage, latency, or outcome comparisons.

## Route to Astra deliberately

Default the lead and engineering children to exact `gpt-6-astra`. This skill cannot switch an
already running parent; report its observed model and use the active runtime's selection mechanism.
Do not silently substitute an older model when Astra is unavailable.

| Native profile | Model and effort | Responsibility |
| --- | --- | --- |
| `astra_engineer` | `gpt-6-astra`, high | Difficult architecture, cross-system implementation, root cause, and consequential review |
| `astra_explorer` | `gpt-6-astra`, medium | Bounded code, SDK, dependency, and user-journey investigation |
| `astra_worker` | `gpt-6-astra`, medium | Scoped implementation with focused verification |
| `astra_verifier` | `gpt-6-astra`, medium | Independent review, regression checks, and acceptance evidence |

Preserve the selected parent's effective effort during migration. The bundled profiles pin both
model and effort; low is useful for routine direct work, medium for general engineering, and high
for difficult judgment. Evaluate higher effort before making it a default. Astra does not support
`none` or `minimal`; Max, Ultra, Pro, and Fast are distinct runtime choices, not assumed upgrades.

**Economy is an explicit option:** retain `terra_explorer`, `terra_worker`, `luna_worker`, and
`luna_verifier` for suitable bounded work when the user selects a mixed-model cost/latency policy.
The lead remains Astra. Preserve those profiles' model/effort roles; choose them from accepted
results per cost and time, rather than token price alone. `luna_max_worker` remains a separate
explicit or measured Fast/Max choice. Sol profiles are historical; Spark and Claude remain separate
user-selected workflows. Never silently fall back between suites or providers.

Inspect the active spawn schema and capacity. Prefer native profiles when installed and selectable;
otherwise an explicit `model="gpt-6-astra"` plus supported effort and bounded role instructions is
valid when the runtime exposes these selectors. Do not require installation or a Python launch just
to give an available native child a role. A model-less role is insufficient route evidence.

Use `scripts/audit_routing.py --cwd <repo> --runtime --parent-model <observed-model> --json` when
validating installed profiles; add `--suite economy` for that explicit policy. Recheck after a
profile, project, runtime, or catalog change, rather than repeating a full preflight at every stage.
Inspect conflicting project overrides before delegation. Record requested route, effort, profile
source/hash when applicable, and `fork_turns`; record effective values only when the runtime exports
them. Missing effective metadata is `unavailable`, not proof of a wrong route or a reason to abandon
an otherwise valid requested route unless the task explicitly requires attestation. Stop an observed
mismatch. Make the first useful stage the canary; avoid synthetic model-echo tests.

## Delegate when it advances the outcome

Astra can under-delegate without clear guidance, but unnecessary delegation duplicates context and
adds synthesis cost. Use collaboration tools when a bounded independent lane can save time or add
review value, while the lead continues useful work. Give every child a concrete decision or artifact
to deliver. Keep tightly coupled changes together. Inspect live capacity; configured limits are
ceilings and do not create useful work. A fleet is never required merely because this skill is active.

- **Fast:** direct execution, or one child whose work can overlap useful lead work.
- **Standard:** up to three independent children for ordinary multi-part work.
- **Broad:** up to six read-heavy children for repository-scale investigation or final review.
- **Team:** an explicitly qualified seven/eight-reader experiment; use the criteria and
  `--team-qualified --routes-attested --lanes-independent --paired-comparison` controls in
  [dynamic workflows](references/dynamic-workflows.md).

Use `scripts/plan_fleet.py` when capacity or write isolation makes the choice non-obvious. Keep one
writer in a shared checkout; two simultaneous writers require disjoint owned paths in isolated
candidate worktrees, with at most two supporting readers. Tell workers they share the repository
with others and must preserve others' edits. Avoid reads of files whose changing state would make
the result unreliable. Delegate at one level by default; another level needs a concrete independent
shard, capacity, and inclusion in the root ownership ledger.

Dispatch ready independent work before waiting. As results arrive, validate them and start newly
unblocked stages; wait only for prerequisites required by the next decision. Keep explicit barriers
for shared-file integration, dependent writes, and final acceptance. Reuse a child for a related
delta; cancel invalidated work. Avoid repeated broad discovery and review between writes.

Send compact context: objective, owned paths, relevant repository rules and dirty state, acceptance
criteria, evidence pointers, authority, dependency, and stop condition. Use `fork_turns="none"` for
independent lanes; a small positive fork is appropriate when exact recent context is necessary.
Full-history forks require necessary shared context and acceptable inherited model/effort. Never
use a full-history fork with a model override.

Require a concise handoff: stage/status, result, file or artifact evidence, changed paths, checks
(pass/fail/skip/not-run), blockers, and the next integration action. Include applicable requirement,
gate, and documentation dispositions. Most handoffs fit 150–350 words; include additional evidence
when the decision needs it. Keep raw logs and full diffs in artifacts. Use
`assets/codex/handoff.schema.json` for programmatic handoffs; normalize native results when recording
them, without demanding a fabricated CLI `result.json`.

## Build and verify with proportionate effort

Trace relevant execution and data paths before changing them. Check current primary documentation
for unstable SDK/API assumptions. Distinguish intended fixtures, placeholders, and compatibility
paths from incomplete production behavior. Rank confirmed findings by impact and dependencies,
then implement, integrate, and verify them. Every finding receives an explicit disposition.

Match verification to the change's risk and repository requirements. Add regression tests for
meaningful behavior; low-impact reversible edits do not need tests that merely mirror the edit.
Run focused checks during implementation and appropriate integrated checks at completion. Inspect
what commands execute and report required skips separately. Once checks pass, broaden or repeat
them only for changed code, failures, unresolved concerns, or an applicable repository gate.

Use browser/computer tools when the changed interaction, layout, runtime behavior, or acceptance
criterion needs rendered evidence, including relevant error, loading, accessibility, and responsive
states. A copy-only edit normally needs a focused source check unless rendered behavior is uncertain.
Preserve direct evidence. A successful build alone
does not prove a flow; neither does a model's confidence. Keep one owner and live handle per long
build/test/browser process, inspect its state after a wait timeout, and avoid duplicate launches.

Subsequent cycles are delta-only: reuse validated findings, resolve confirmed gaps, and invalidate
only affected evidence. `scripts/cache_gates.py` can verify command-evidence reuse for large repeated
runs. Do not impose its fingerprinting overhead on a simple one-off edit.

## Keep long work observable and resumable

For durable or multi-wave work, use the private `scripts/run_journal.py` ledger for requirements,
stages, dispatches, handoffs, barriers, and evidence hashes. The lead is the logical journal writer.
Repository-local `.engineer` state is opt-in. Read [run-journal.md](references/run-journal.md) before
initialization or resume. Use native context/history retrieval when available, storing only compact
operational facts in the journal. Search older evidence as needed; do not replay full transcripts.

Measure accepted verified outcomes, elapsed time, rework, and usage by route and effort. Preserve
requested/effective distinctions, missing-data states, and separate dispatch/history/OTel coverage.
Use `scripts/audit_fleet.py` and `scripts/join_fleet_outcomes.py` with explicit snapshot bounds for
comparisons. The pre-Astra logs remain a historical baseline; migration correctness tests do not
prove an Astra speed or cost gain. Compare representative tasks before tuning fleet size and effort.

## Select the execution surface and finish ownership

Native Codex collaboration is the interactive default. For an application, choose the official
Codex SDK, managed Agents API, Responses, or Agents SDK from the capabilities and constraints in
[dynamic workflows](references/dynamic-workflows.md). Astra's async tools, steering, and context
features require actual runtime/API support; a skill cannot activate them by assertion.

`scripts/run_codex_agent.py` remains a guarded CLI compatibility adapter with a required reason,
isolated candidate writes, bounded processes, and structured evidence. Read
[codex-astra.md](references/codex-astra.md) before using it. Skills installation and profile
registration are separate: `scripts/bootstrap.py --provider codex --upgrade --global`, then
`--check --global`, registers bundled profiles when setup is authorized. Restart Codex to refresh
its catalog. Do not patch model caches or add generic auto-continue hooks as routine setup.

Before finishing, review the integrated diff and reconcile every required lane, finding, and check.
For delegated-fleet teardown, stop and join only task-owned processes using recorded native handles,
process groups, and working directories. Close native lanes where supported; an idle retained agent
handle or open database edge does not prove a running OS process. Preserve shared MCP services and
other tasks. Retain candidate artifacts until integrated or explicitly disposed of.

Finalize every started journal even on interruption: record terminal handoffs, reconcile open
dispatches/barriers, inspect `status`, and close with the truthful outcome. Report completion only
when acceptance is supported or the remaining external blocker is explicit. Lead with what changed,
why, verification, and material limitations. Use concise prose and useful evidence links.
