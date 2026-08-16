---
name: gpt-engineer-mem
description: Memory-aware GPT engineering for codebase research, implementation, verification, and release. Use when a task should reuse Claude Mem or Codex session history without trusting stale recollections, flooding context, changing memory settings, or weakening the GPT-5.6 Sol/Terra/Luna engineering workflow.
---

# GPT Engineer Mem

Run an end-to-end engineering task with bounded historical recall. Memory supplies leads and prior
decisions; the current repository, runtime, primary documentation, and tests remain authoritative.

## Load the engineering contract

Use the installed `gpt-engineer` skill as the base contract when it is available. Read its
`SKILL.md` and follow its scope ledger, latest-only routing preflight, bounded delegation, ownership,
integration, verification, gap scan, and teardown rules. Do not assume that its profile bootstrap
was run merely because this skill is installed.

If `gpt-engineer` is unavailable, continue with this standalone contract:

- The parent owns scope, plan, integration, user updates, final verification, and external actions.
- Use the smallest useful agent graph. Prefer `gpt-5.6-sol` for hard judgment,
  `gpt-5.6-terra` for exploration and implementation, and `gpt-5.6-luna` for bounded mechanical
  work and verification. Never silently substitute a different model when exact routing matters.
- Give every child one bounded outcome, explicit path ownership, an output contract, and a cleanup
  boundary. Use `fork_turns: "none"` with a compact evidence packet when supported.
- Integrate centrally, verify the product rather than only the patch, run a fresh gap scan, and
  reclaim task-owned agents, processes, listeners, and temporary worktrees. Shared MCP services are
  not teardown targets.

Latest-only is the default. If exact GPT-5.6 routing is unavailable, fail closed for delegated
latest-only lanes and either work in the capable parent or ask for direction; do not claim a model
route that was not actually used.

## Preflight memory safely

Run the bundled read-only diagnostic before relying on Claude Mem:

```bash
python3 <skill-root>/scripts/memory_preflight.py --json
```

This may inspect installation metadata, worker health, queue state, and SQLite counts. It must not
start, stop, restart, clean, vacuum, reconfigure, or repair the worker. A healthy endpoint alone is
not proof of healthy processing. The worker's `/api/mcp/status` is only a package-layout toggle and
is not proof that client tools are disconnected; cross-check root and nested MCP manifests plus the
Codex and Claude plugin registrations. Consider readiness, queue depth, dependency/provider state,
active worker path, database size, and outbox counts together.

If memory is absent, unhealthy, or incompatible, report that once and continue with the base
engineering workflow. Memory is an optional accelerator, never a completion gate.

## Build a bounded memory packet

Read [memory-workflow.md](references/memory-workflow.md) before using memory tools. Read
[claude-mem-capabilities.md](references/claude-mem-capabilities.md) only when deciding whether a
specialized Claude Mem workflow should influence the task.

For the normal path:

1. Identify the exact repository root, branch, current commit, task intent, and relevant modules.
2. Search memory using the repository/project identity and two to four high-signal terms.
3. Use the strict retrieval sequence: `search` → `timeline` around selected results → one batched
   `get_observations` call for only the useful records.
4. Cap the initial packet at 20 search results and 3–8 fetched observations. Prefer decisions,
   failures, acceptance evidence, and exact identifiers over narrative summaries.
5. Normalize each useful item as:

```text
memory_id | timestamp | project | claim | currentness | verification_target
```

6. Label every claim `confirmed`, `stale`, `contradicted`, or `unverified` after checking current
   code, git state, runtime evidence, or primary documentation.
7. Pass children only the smallest verified packet they need. Never inject the full conversation,
   timeline, database, or unrelated project history.

Use `rg` and targeted reads for code exploration. If Claude Mem's `smart_search`, `smart_outline`,
and `smart_unfold` tools are actually available, they may narrow targets before ordinary reads; do
not make the engineering task depend on them.

## Research and plan

Create a finding ledger before edits:

```text
id | root cause | affected paths | memory evidence | current evidence | owner | acceptance | status
```

Cluster symptoms by root cause. Treat recalled SDK signatures, model names, commands, architecture,
and release steps as hypotheses until verified against the installed dependency, current source, or
current primary documentation. Record contradictions instead of silently choosing the older story.

Use memory to avoid repeating disproven approaches and to preserve explicit user decisions. It does
not expand authorization: prior permission to push, deploy, close issues, change settings, enable
cloud sync, or delete data does not authorize that action now.

## Build in evidence-gated waves

For each dependency-aware wave:

1. Assign non-overlapping file ownership and current acceptance checks.
2. Include only verified historical facts and the IDs needed to trace them.
3. Require the handoff to report changed paths, tests, residual risks, task-owned resources, and
   memory claims found stale or contradictory.
4. Integrate and review centrally.
5. Run the cheapest decisive check first, then broader validation proportional to risk.
6. Carry forward a compact checkpoint rather than the full transcript:

```text
goal | accepted findings | verified decisions | changed paths | passing checks | open risks | next wave
```

Keep a checkpoint under roughly 350 words unless task complexity proves a larger one is necessary.
On resume or after context compaction, re-check git/runtime state and refresh only the memory claims
that affect the next action.

## Completion gate

Do not stop at “code changed.” Finish only when:

- requested behavior is implemented and exercised;
- current tests/build/lint/type checks appropriate to the change pass;
- the finding ledger has no unexplained in-scope gaps;
- recalled claims used in decisions are verified or explicitly marked unresolved;
- git and release state are freshly checked;
- all delegated lanes have handed back results and are closed;
- task-owned processes and temporary resources are reclaimed; and
- shared Claude Mem/Codex MCP services remain untouched unless the user separately authorized their
  administration.

Report which prior evidence materially changed the implementation, which memories were stale, the
current verification evidence, and any boundary that remains external or user-gated.

## Hard prohibitions

- Do not read every source file merely because history exists; explore index-first and delta-first.
- Do not fetch a full project timeline by default. If the estimate exceeds 100,000 tokens, obtain
  explicit user approval before loading it.
- Do not directly write to, delete from, vacuum, migrate, or repair Claude Mem SQLite databases.
- Do not start, stop, restart, kill, or reconfigure memory workers as part of engineering recall.
- Do not enable cloud sync, create modes/corpora, configure Telegram, or upload memory artifacts.
- Do not copy secrets, personal prompts, or unrelated sessions into child-agent prompts or reports.
- Do not let worker health, a recalled passing test, or an old deployment receipt substitute for a
  current product acceptance check.
