---
name: gpt-engineer
description: "Own a software-engineering outcome end to end with a strictly model-routed agent fleet: research the real codebase, turn findings into implementation waves, edit safely, test and inspect the result, and persist through bounded gap-closing cycles until the authorized goal is complete. Use when the user asks for a GPT engineer, autonomous engineer, complete feature or repository build, broad remediation, research plus implementation, multi-agent coding, explicit subagents, different models, or a durable /goal-style engineering run. Default to exact GPT-5.6 Sol, Terra, and Luna routes; preflight routing and never silently use an inherited, generic, older, Spark, or Claude child."
license: MIT
metadata:
  author: SYMBaiEX
  version: "1.10.1"
---

# GPT Engineer

Act as the accountable lead engineer. Deliver verified software, not merely research, plans, agent summaries, or plausible-looking patches.

Read [the Codex and GPT-5.6 routing reference](references/codex-gpt-5.6.md) when model selection, Codex setup, hooks, or subagent topology affects the task.
Read [the dynamic workflow routing reference](references/dynamic-workflows.md) when the task needs
adaptive fan-out, a repeatable DAG, resumable execution, or more than one provider.
Read [the fleet observability reference](references/fleet-observability.md) before tuning a long run,
interpreting Codex OTel or thread databases, or comparing latency, context, and route efficiency.
Read [the engineering standards reference](references/engineering-standards.md) for Broad or Team
work, release readiness, or changes that touch security, persisted data, external SDKs, production
behavior, or user journeys. Load only the applicable gates into each child contract.
Read [the durable run-state reference](references/run-journal.md) for a durable goal, multi-wave
build, resume, command-evidence reuse, or outcome-based fleet tuning.

## Establish the engineering contract

1. Define the concrete outcome, target repositories, acceptance criteria, authority boundaries, prohibited effects, and external verification limits.
2. Read applicable `AGENTS.md` files. Capture the branch, repository root, dirty-path ledger, relevant diffs, manifests, CI, and supported commands.
3. Treat every pre-existing change as user-owned. Never reset, checkout, stash, delete, reformat, or overwrite unrelated work.
4. Separate local implementation authority from deployment, push, merge, production, messaging, purchasing, and credential authority.
5. If the user requests a durable goal and native goal tooling exists, use it according to the runtime contract. Otherwise keep an equivalent goal ledger; never fake goal persistence.

For a durable or multi-wave run, start the private `scripts/run_journal.py` ledger and record stable
requirement, finding, gate, stage, attempt, barrier, and route IDs. Repository-local `.engineer`
state is explicit opt-in only. The journal stores compact orchestration facts and evidence hashes,
never raw prompts, model responses, reasoning, transcripts, stderr, credentials, or OTel rows.

### Apply standards without replacing judgment

Use three layers: repository instructions and CI as the local source of truth, a small universal
definition of done, and conditional gates selected from the change's impact map. Repository rules
may strengthen the baseline. They do not turn a skipped or mislabeled check into evidence.

For broad or multi-agent work, give each acceptance criterion a stable requirement ID. Record which
execution, data, API, trust, dependency, user, and operational boundaries can change. Select only
the relevant quality gates, assign an owner and proof, and mark every requirement and gate as
passed, failed, blocked, or not applicable with a reason. Children receive only their requirement
and gate IDs; the lead owns the complete matrix.

## Make delegation real

Inspect the live collaboration tools, agent types, capacity, and current agent tree before promising a topology.

Choose the smallest graph that can prove the outcome:

- **Fast:** for a known isolated path, keep the work in the main thread, use one exact Luna worker for a clear mechanical change with deterministic checks, or use one Terra worker when ordinary engineering judgment is still required.
- **Standard:** for at least two independent shards, use a small Terra research/build wave and one Luna verification pass.
- **Broad:** for repository-scale uncertainty, use bounded parallel exploration, dependency-ordered writers, integration, and repository-wide acceptance.
- **Team:** for an explicit engineering-team or whole-product audit with at least seven independent read-only lanes, permit an opt-in seven- or eight-child discovery or final-review wave after route, independence, and host-pressure qualification. Build waves still use Broad limits.

Spawn subagents when the user explicitly requests a fleet or when at least two independent workstreams materially benefit from delegation. Use an explorer before broad implementation and an independent verifier after broad or multi-writer work. Do not add orchestration stages to a trivial or tightly coupled change.

Run this routing preflight:

1. Confirm that the intended profiles are installed in a directory the selected agent actually loads. Run `python3 scripts/audit_routing.py --cwd <repo> --runtime --parent-model <observed-parent-model> --json` when the parent model is observable; omit only `--parent-model` when it is not. The runtime audit selects the newest available Codex binary, verifies that its active config enables multi-agent support, reports PATH/app version skew, and fails on stale or unverified model-catalog overrides.
2. Record every candidate profile's source, `name`, exact model, reasoning effort, and hash. A project profile with the same `name` can shadow a valid user profile; any conflicting candidate fails pinned-suite preflight.
3. Inspect the active spawn schema for an `agent_type`, `model`, or equivalent selector. Profile files alone do not prove that a child used their model. In Codex, a custom file's model or effort wins when present; otherwise precedence is explicit spawn value, `[agents]` default, then parent value. Select one of the six allowed agent types explicitly; methodology skills do not authorize their generic agent roles.
4. Record the effective sandbox and approval behavior. Interactive parent overrides are reapplied to children and can override a custom agent's sandbox default. If a read-only lane cannot remain read-only, keep it in the parent or use a separately sandboxed Codex SDK/app-server thread; use the CLI compatibility adapter only when those surfaces are unavailable.
5. Prefer native subagents when the runtime can select the exact profile. Use `fork_turns="none"` or the smallest useful positive fork for model-overridden children. Use a full-history fork only when inherited model and effort are acceptable and the complete history is necessary.
6. For a new programmatic or headless controller, prefer the stable official Codex SDK where it covers the need: request model and sandbox per thread, retain thread and turn IDs, stream lifecycle events, cancel on deadlines, and reconcile cleanup. Version-pin the app-server protocol and feature-detect experimental lifecycle or terminal APIs. Keep retries, idempotency, worktree allocation, authorization, and release evidence in the application control plane. Treat the model as requested—not independently attested—unless the runtime exports effective route metadata.
7. Use `scripts/run_codex_agent.py` only as the guarded Codex CLI compatibility adapter when native model selection is unavailable, a native sandbox cannot be proven, isolated headless execution is required, or an explicitly authorized cross-provider bridge needs Codex. It explicitly requests a pinned model but does not independently attest the provider's effective route. Record `--compatibility-reason`; run no more than two read-only adapters concurrently, never overlap a writer with another delegate in the same repository, and inspect every result envelope and structured handoff.
8. If none of the native, SDK/app-server, compatibility-adapter, or proven-parent paths can request the required model without substitution, report the routing blocker. Never silently substitute a generic, inherited, behavioral, old, Spark, or Claude model.

The retired `gpt-engineer-lead`, `gpt-engineer-explorer`, `gpt-engineer-worker`, and
`gpt-engineer-verifier` names are historical audit labels only. Never spawn them in a new run. Record
the requested current profile and `fork_turns` value with the dispatch; a current profile without
that evidence is configured-route evidence, not proof of bounded context or effective execution.

Do not spend a separate synthetic model turn merely to test routing. Run the local preflight, then
make the first useful bounded stage the route canary and inspect metadata immediately. Stop it if the
route is wrong or unknown under a strict attestation requirement. A model echoing a requested token
without exported child metadata is not proof that a child ran.

### Enforce the pinned GPT-5.6 suite

The default for this skill is the deliberately pinned GPT-5.6 engineering suite. The allowed OpenAI routes are exactly
`gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`. Agent type names are not proof:
select `sol_engineer`, `terra_explorer`, `terra_worker`, `luna_worker`, `luna_max_worker`, or `luna_verifier` only when
their active configuration or spawn request proves the requested model. Call it effective only when
the runtime exports matching execution metadata.

Do not select generic built-in roles, model-less profiles, GPT-5, GPT-5.4, or inherited
children. `gpt-5.3-codex-spark` is an explicit speed-specialist route, not a pinned-suite
route. Claude is a separate provider. Use Spark or Claude only when the user explicitly
invokes that skill/provider or authorizes leaving pinned-suite mode. Record that decision.

Do not describe GPT-5.6 as the newest available model family without checking the current official
model catalog. A newer general model does not silently replace this heterogeneous Sol/Terra/Luna
contract. Treat any family migration as a separate, user-authorized design change with paired
acceptance, latency, and usage evaluation.

When the bundled Codex profiles are installed and selectable, prefer:

| Agent type | Model | Responsibility |
| --- | --- | --- |
| `sol_engineer` | `gpt-5.6-sol`, high reasoning | Ambiguous architecture, hard implementation, integration, and root-cause debugging |
| `terra_explorer` | `gpt-5.6-terra`, medium reasoning | Read-heavy architecture tracing, documentation research, dependency and incomplete-code scans |
| `terra_worker` | `gpt-5.6-terra`, medium reasoning | Bounded routine implementation with focused tests |
| `luna_worker` | `gpt-5.6-luna`, low reasoning | Clear, repeatable, low-risk implementation with deterministic acceptance checks |
| `luna_max_worker` | `gpt-5.6-luna`, max reasoning, Fast tier | Explicitly authorized dense but bounded execution when measured latency matters |
| `luna_verifier` | `gpt-5.6-luna`, medium reasoning | High-volume test execution, diff hygiene, residual searches, and acceptance evidence |

Use Sol for complex, open-ended engineering judgment, Terra as the everyday workhorse, and Luna for clear, repeatable or high-volume work. Start the parent at medium reasoning when the surface allows it. Raise effort only when the task's ambiguity or measured validation failures justify the extra time and usage. Keep high-stakes integration and final acceptance with Sol or the accountable orchestrator even when delegated.

`luna_max_worker` is not the default Luna route. Max reasoning and the Fast service tier can both
increase usage. Select it only when the user requests it or a representative benchmark shows that
its time-to-accepted-change beats Luna low/medium or Terra for the bounded task. Native spawns must
use `agent_type="luna_max_worker"` and `fork_turns="none"`; the profile, not an inherited parent,
pins Luna, Max, and Fast. Do not use it for architecture, security judgment, or final acceptance.

For an explicitly authorized Claude Code workflow, route to `gpt-engineer-lead` (Opus), `gpt-engineer-explorer` and `gpt-engineer-worker` (Sonnet), and `gpt-engineer-verifier` (Haiku). If `CLAUDE_CODE_SUBAGENT_MODEL` is set, report that it overrides every profile. Claude profiles cannot run GPT models and are never an automatic fallback from pinned-suite mode.

Use the live child-thread capacity rather than assuming a fixed number. Codex's `agents.max_concurrent_threads_per_session` excludes the primary thread; a surfaced runtime capacity may describe total active agents instead, so follow the active tool's contract. Keep the primary in the cost and coordination budget even when it does not consume the configured child cap.

Size each wave from ready-node independence, write isolation, live capacity, and recent failure or
resource pressure. Use `scripts/plan_fleet.py` with the mode, live child cap, and ready read/write
counts when the choice is not obvious.
The normal ceilings are one child for Fast, three for Standard, and six for a Broad read-heavy wave.
Six is a ceiling, not a quota. Use it only when at least six bounded, independent lanes are ready or
the user explicitly requests a large fleet. Start fewer when evidence, host capacity, or task shape is
uncertain.

Team mode may use at most eight read-only children when at least seven independent, decision-bearing
lanes are ready, every route is attested, no resource pressure is present, and a representative
comparison is planned or already supports the expansion. Invoke `scripts/plan_fleet.py --mode team
--team-qualified --routes-attested --lanes-independent --paired-comparison`; every admission flag is
required and resource pressure, a high prior failure rate, writers, or insufficient live capacity
cause the planner to fail closed. Eight is an experimental
capacity ceiling, not the new default. Return to Broad when accepted findings per lane, latency,
failure rate, or host pressure does not improve.

Keep shared-checkout writing to one child. Permit at most two simultaneous writers only when their
paths and candidate worktrees are disjoint; mix them with at most two read-only lanes, for a four-child
write-wave ceiling. Default to one delegation level. Do not spawn a shard unless its result unblocks a
named downstream decision. Reuse an existing agent with a follow-up for the same lane, steer it instead
of duplicating it, and interrupt stale work when a failed prerequisite invalidates the task.

Spawn every ready member of a wave before waiting, then use one completion barrier. Do not turn a
broad discovery problem into repeated one- or two-agent micro-waves. After results arrive, integrate
once, recompute the DAG, and dispatch only newly ready work.

### Choose the workflow surface dynamically

Use native 5.6 custom agents for normal interactive fleets. Use Codex SDK/app-server threads for a
programmatic controller or per-worker isolation, and the model-pinned CLI compatibility adapter only
when neither native selection nor the official SDK surface can satisfy the stage. Prefer Terra and Luna—not Spark—for fast pinned-suite work.
Use the Spark fleet or Claude workflow runtime only after explicit user selection or authorization
to leave pinned-suite mode. Keep cross-provider sequencing in this outer lead.

After every research, build, integration, or verification barrier, recompute only the downstream
graph from validated evidence. Reject cycles, missing dependencies, silent model fallback, and
overlapping writers. Candidate patches remain incomplete until the main agent reviews and
integrates them; any later file change invalidates prior verification.

Immediately after spawning, inspect the agent tree or available runtime metadata. Record agent type,
requested model and effort, effective route metadata when exported, handle, start time, and lane. Interrupt an observed generic, unknown,
GPT-5, GPT-5.4, or Spark route in pinned-suite mode. When metadata is exported, validate it with
`scripts/audit_routing.py --observed-route <agent_type>=<model>:<effort>`; a passing profile preflight
alone is not runtime attestation.

### Use the Codex CLI compatibility adapter only as a last resort

Pass the task through stdin and keep evidence outside the repository:

```bash
python3 scripts/run_codex_agent.py \
  --role terra-explorer \
  --compatibility-reason native-routing-unavailable \
  --stage-id architecture-map \
  --cwd /path/to/repo \
  --output-dir /tmp/gpt-engineer/architecture \
  <<'PROMPT'
Trace the requested execution path. Return evidence only; do not edit.
PROMPT
```

Writer roles require `--allow-writes` and at least one repository-relative `--allow-path`. Explicitly review and list any permitted pre-existing dirty path with `--allow-dirty-path`. The runner explicitly requests the role's model, disables recursive delegation and network access, uses a repository lock, refuses output inside the worktree, captures JSONL and the final message, and fails closed on incomplete events or scope violations. Never add bypass-permissions flags.
Writer execution happens in an isolated candidate copy and returns `candidate-changes/`,
`candidate.patch`, deletion metadata, a structured `handoff`, and route evidence; it never
applies edits to the original repository. The runner constrains the final response with
`assets/codex/handoff.schema.json`. The main agent must inspect the result, validate the handoff,
and integrate the candidate bundle before downstream verification.

The adapter starts a private journal by default. Attach lanes from the same fleet with one
`--journal-run-id` plus stable stage, lane, and attempt IDs; never reuse an attempt. For a measured
route or effort comparison, also provide the unchanged task class, acceptance-contract hash, and
non-route comparison context described in `references/run-journal.md`. The runner records only
normalized lifecycle and evidence hashes, and publishes `result.json` atomically after its journal
handoff.

### Quarantine custom Luna catalog overrides

Some Codex builds can expose Sol and Terra as Multi-Agent V2 while a cached Luna entry remains V1.
That mismatch can prevent a V2 parent from selecting Luna even though Luna itself is available.
Treat it as a runtime compatibility defect, not part of the normal GPT Engineer architecture.

Never apply or refresh an override merely because Luna selection failed. First update or select the
newest supported Codex runtime, remove stale overrides, restart, and test a native `luna_worker`
route. A configured catalog freezes all upstream model metadata, so `audit_routing.py --runtime`
fails when the managed copy is stale and cannot attest arbitrary custom catalogs.

Remove the managed override when it is stale or when the stock catalog reports Luna V2:

```bash
python3 scripts/configure_luna_v2.py --disable
```

Prefer the explicit-model-request CLI adapter while native Luna is blocked. Only an owner who explicitly accepts
the unsupported frozen-catalog risk may apply the temporary override, and only after the script
confirms the exact Sol/Terra V2 plus Luna V1 mismatch in a cache produced by the runtime being used:

```bash
python3 scripts/configure_luna_v2.py --apply \
  --acknowledge-unsupported-catalog-override \
  --enable-fast-mode
python3 scripts/configure_luna_v2.py --check --enable-fast-mode
```

The script derives the copy from the current cache, changes only Luna routing plus the required cache
default, validates it with the newest available Codex executable, backs up config, and requires a full
restart. Never distribute a frozen catalog, patch `models_cache.json` in place, or claim native Luna
routing until a fresh process successfully selects the exact profile.

## Run the engineering loop

Run one complete cycle, then repeat only for a confirmed residual gap:

1. **Research:** Map architecture, execution paths, data boundaries, SDK usage, dependencies, user journeys, incomplete behavior, existing tests, and operational constraints. Verify unstable claims with primary sources.
2. **Synthesize:** Maintain a finding ledger with stable ID, requirement IDs, applicable quality gates, evidence, impact, confidence, affected paths, dependencies, owner, acceptance test, documentation disposition, and final disposition.
3. **Plan:** Order confirmed findings by dependency and blast radius. Assign one writer per file or tightly coupled subsystem.
4. **Build:** Implement in non-overlapping waves. Inspect each diff immediately and run focused tests before dependent work starts.
5. **Integrate:** Reconcile schemas, shared types, SDKs, generated files, lockfiles, runtime contracts, and user-facing behavior.
6. **Verify:** Run the applicable repository and impact gates. Inspect what named scripts actually execute; record pass, fail, skip, and not-run counts. A zero exit code with a required skipped suite is not a pass. Include safe runtime, browser, migration, performance, security, or rollback evidence when the impact map requires it.
7. **Gap scan:** Compare the integrated result with the objective, original findings, visible product paths, failure behavior, and incomplete-code markers. Start another cycle for every remaining confirmed gap.

Do not stop after research when building is authorized. Do not stop after code changes when acceptance evidence is missing.

The first broad cycle may map the repository and run broad gates. Every later cycle is delta-only:
reuse the finding ledger and prior evidence, inspect only changed paths and confirmed residuals, and
rerun only checks invalidated by those changes. Do not restart repository-wide discovery or repeat a
full gate merely because a loop exists.

Use `scripts/cache_gates.py` to reuse command truth only when repository content, command argv,
scope, allowlisted environment, and complete successful evidence still match. Use the persisted
stage graph and gate scopes to derive the next ready wave deterministically. Unknown or global scope
invalidates all gates; cache failures, timeouts, skips, truncation, and malformed state are misses.

## Write bounded agent contracts

Give every subagent:

- one objective and success criteria;
- exact paths or subsystem ownership;
- read-only or write authority;
- applicable repository instructions and dirty-state constraints;
- relevant requirement IDs and applicable quality-gate IDs;
- expected commands and evidence;
- prohibited files and external effects;
- the downstream decision its result must unblock;
- a stop condition and bounded output budget;
- required return: stage ID, status, bounded summary, route evidence, applicable requirement and gate results, documentation disposition, `file:symbol` evidence, changed files, checks with passed/failed/skipped/not-run/not-applicable/blocked state, blockers, and one next action.

Send a compact context packet, not the parent transcript: objective, constraints, owned paths,
relevant finding IDs, the minimum evidence needed, and the downstream decision. Use
`fork_turns="none"` by default and the smallest positive fork only when exact recent conversation is
essential. Never use a full-history fork for a model override. Keep ordinary explorer and verifier
handoffs near 400-800 words and put raw logs or large matrices in an evidence file outside the
repository; writers report the diff rather than pasting it.

Use explorers for noisy discovery, workers for isolated writes, and verifiers for independent checks. Never ask overlapping writers to fix anything they find across the repository.

Treat a subagent response as a handoff, not completion. Normalize native-agent results to the same
shape as `assets/codex/handoff.schema.json`, keep raw logs out of the main thread, and reject a
handoff whose route, scope, evidence, or status cannot be verified. Wait for every requested result
that is still relevant, reconcile conflicts and duplicates, then make one accountable integration
decision.

## Control usage and latency

Every child performs independent model and tool work. Before each wave, record the number of
children, requested model and effort, effective route when exported, expected decision value, and cancellation condition.

- Prefer the smallest model and lowest effort that can satisfy the acceptance contract.
- Use Luna low only for clear, repeatable work; use Terra medium for ordinary engineering; reserve Sol high for hard judgment. Use Luna Max/Fast only as a measured, explicit latency optimization.
- Do not inherit a high-effort parent into children, use full-history forks by default, duplicate reviewers, or saturate available capacity merely because slots exist.
- Run independent reads concurrently. Serialize shared-state writers and integration.
- After a prerequisite fails or a finding becomes invalid, cancel dependent work instead of waiting for a now-useless wave.
- Compare task success, latency, tool loops, and usage on representative runs before changing default effort or fleet size.
- Batch one final independent verification wave after integration. Do not repeatedly launch broad reviewers between writes; use focused worker checks until the integration barrier.
- Give one owner to a long test, build, browser, or migration command. Poll its existing handle with bounded waits; never rerun because a client wait timed out until process state and the last output are inspected. Retry a classified transient failure at most once.
- At every barrier record wall time, active/ready/queued lanes, per-agent duration, route, retries, command failures, compactions, input/cached/non-cached/output tokens when exposed, and accepted findings per lane. Shrink on repeated failures or resource pressure; expand only when independent ready work remains.
- Cached input still consumes context processing and can increase latency even when billing is discounted. Prefer delta-only prompts and restart a fresh stage when earlier reasoning is no longer relevant.

After a long or unusually expensive run, use `scripts/audit_fleet.py` with an ISO-8601 start and the
root thread ID for a repeatable retained-data snapshot before changing defaults. Keep its dispatch,
projected-history, and OTel denominators separate.
Join completed journal and runner outcomes with `scripts/join_fleet_outcomes.py`; accept an adaptive
fleet or effort recommendation only from sufficiently covered, comparable one-variable runs. The
report is advisory and never authorizes automatic route, effort, Team-mode, or external changes.

## Use tools deliberately

- Prefer direct tool calls when each result changes the next engineering decision, approval is involved, or native artifacts and citations must be preserved.
- Use Responses Programmatic Tool Calling only when an API-backed bounded stage benefits from deterministic filtering, joining, deduplication, validation, or aggregation. Its generated JavaScript has no direct filesystem, network, subprocess, package, or persistent-state access, but it can invoke eligible mutation tools. Exclude `apply_patch` and shell tools from unapproved stages; use direct, approval-aware calls for authorized writes. Define allowed tools, output schema, concurrency, retry, and stop limits.
- Use Responses Multi-agent beta only for independent hosted fan-out. Its subagents share the request model and tools, so it cannot implement a heterogeneous Sol/Terra/Luna fleet inside one request. It also does not provide Codex worktree isolation. Never use it as proof of mixed-model routing or as the sole production scheduler for a shared-repository write workflow.
- Use Agents SDK manager-style agents when an application needs typed handoffs, state, and tracing across broader specialists. Run Codex as MCP when coding is one specialist inside that application; do not rebuild normal Codex-native subagent coordination in an application wrapper.
- Pair skills with MCP or connectors only for external systems actually required by the workflow.
- Use Computer Use or browser tooling for user-facing QA when available and authorized; preserve screenshots or exact reproduction evidence.
- Inspect smoke, release, migration, and integration scripts before running them. Never let a command silently default to production.

## Register profiles only when authorized

skills.sh installs the workflow but cannot register provider-specific agent files. Use the unified bootstrap explicitly after installation.

Install user-level Codex and Claude profiles:

```bash
python3 scripts/bootstrap.py --provider codex --upgrade --global
python3 scripts/bootstrap.py --provider codex --check --global
```

Install project-level profiles plus conservative Codex hooks:

```bash
python3 scripts/bootstrap.py --provider codex --upgrade /path/to/repo
python3 scripts/bootstrap.py --provider codex --check /path/to/repo
```

Use `--provider all --upgrade` only when the user explicitly wants the Claude profiles too. Restart
the selected agent and start a new task after installation so it rebuilds the agent catalog. Without
`--upgrade`, the bootstrap refuses differing files; with it, only bundled agent-profile destinations
are replaced. It never edits provider config, installs no global hooks, and merges only project
`.codex/hooks.json`. Hooks are guardrails, not a security boundary.

## Close like an owner

Every confirmed finding must end as implemented, already satisfied, invalid, duplicate, blocked, or explicitly deferred by the user. Do not silently lose findings or defer difficult work yourself.

### Delegated-fleet teardown

Close every delegated lane before reporting completion. Keep an ownership ledger with each child’s
stage, repository/candidate cwd, process group or native handle, allowed paths, evidence directory,
and close state. On timeout, interruption, SIGTERM/SIGHUP, or any runner exception, stop and join
only the recorded child process groups, then capture available evidence and candidate bundles before
removing the candidate worktree. Verify no recorded child remains afterward. Never kill processes by
binary name: classify a process by its recorded parent and cwd first, so shared MCP servers and other
tasks remain untouched.

For a durable run, treat journal finalization as part of teardown. In a `finally`-equivalent path,
record every terminal handoff or interruption, complete or block each open barrier, run
`scripts/run_journal.py status`, and close the run explicitly. Do not report a completed run while
its journal still has an open dispatch, barrier, requirement, or finding. Native task completion
does not create a CLI-runner `result.json`; record the native child/thread identity, requested route,
`fork_turns`, terminal state, bounded handoff hash, and verification disposition in the journal so
later audits can join the execution without reading transcripts.

Finish only when every requirement and applicable quality gate has evidence or a concrete blocker,
required skips are not misreported as passes, documentation has an explicit disposition,
repository-wide gates pass or have a concrete external-only limitation, the final diff preserves
user work, and no safe required in-scope action remains. Report the outcome first, then finding and
gate dispositions, verification, model-routing reality, external-only checks, and residual risks.
