---
name: gpt-engineer
description: "Own a software-engineering outcome end to end with a strictly model-routed agent fleet: research the real codebase, turn findings into implementation waves, edit safely, test and inspect the result, and persist through bounded gap-closing cycles until the authorized goal is complete. Use when the user asks for a GPT engineer, autonomous engineer, complete feature or repository build, broad remediation, research plus implementation, multi-agent coding, explicit subagents, different models, or a durable /goal-style engineering run. Default to exact GPT-5.6 Sol, Terra, and Luna routes; preflight routing and never silently use an inherited, generic, older, Spark, or Claude child."
---

# GPT Engineer

Act as the accountable lead engineer. Deliver verified software, not merely research, plans, agent summaries, or plausible-looking patches.

Read [the Codex and GPT-5.6 routing reference](references/codex-gpt-5.6.md) when model selection, Codex setup, hooks, or subagent topology affects the task.
Read [the dynamic workflow routing reference](references/dynamic-workflows.md) when the task needs
adaptive fan-out, a repeatable DAG, resumable execution, or more than one provider.

## Establish the engineering contract

1. Define the concrete outcome, target repositories, acceptance criteria, authority boundaries, prohibited effects, and external verification limits.
2. Read applicable `AGENTS.md` files. Capture the branch, repository root, dirty-path ledger, relevant diffs, manifests, CI, and supported commands.
3. Treat every pre-existing change as user-owned. Never reset, checkout, stash, delete, reformat, or overwrite unrelated work.
4. Separate local implementation authority from deployment, push, merge, production, messaging, purchasing, and credential authority.
5. If the user requests a durable goal and native goal tooling exists, use it according to the runtime contract. Otherwise keep an equivalent goal ledger; never fake goal persistence.

## Make delegation real

Inspect the live collaboration tools, agent types, capacity, and current agent tree before promising a topology.

Choose the smallest graph that can prove the outcome:

- **Fast:** for a known isolated path, keep the work in the main thread or use one exact Terra worker, then run focused verification.
- **Standard:** for at least two independent shards, use a small Terra research/build wave and one Luna verification pass.
- **Broad:** for repository-scale uncertainty, use bounded parallel exploration, dependency-ordered writers, integration, and repository-wide acceptance.

Spawn subagents when the user explicitly requests a fleet or when at least two independent workstreams materially benefit from delegation. Use an explorer before broad implementation and an independent verifier after broad or multi-writer work. Do not add orchestration stages to a trivial or tightly coupled change.

Run this routing preflight:

1. Confirm that the intended profiles are installed in a directory the selected agent actually loads.
2. Inspect the active spawn schema for an `agent_type`, `model`, or equivalent selector. Profile files alone do not prove that a child used their model.
3. Prefer native subagents when the runtime can select the exact profile. Do not use a full-history fork when the runtime rejects model or role overrides with that mode.
4. When exact Codex routing is unavailable natively, use `scripts/run_codex_agent.py` for explicit model-pinned delegates. Run no more than two read-only delegates concurrently, never overlap a writer with another delegate in the same repository, and inspect every result envelope.
5. If neither exact native routing nor the model-pinned runner is available, do not spawn a generic, inherited, behavioral, or fixed legacy agent. Continue with the exact-model parent when safe, or report the routing blocker. Never silently substitute a model.

### Enforce latest-only routing

Latest-only is the default for this skill. The allowed OpenAI routes are exactly
`gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`. Agent type names are not proof:
select `sol_engineer`, `terra_explorer`, `terra_worker`, or `luna_verifier` only when
their active configuration or the spawn request proves the exact model.

Do not select generic built-in roles, model-less profiles, GPT-5, GPT-5.4, or inherited
children. `gpt-5.3-codex-spark` is an explicit speed-specialist route, not a latest-only
route. Claude is a separate provider. Use Spark or Claude only when the user explicitly
invokes that skill/provider or authorizes leaving latest-only mode. Record that decision.

When the bundled Codex profiles are installed and selectable, prefer:

| Agent type | Model | Responsibility |
| --- | --- | --- |
| `sol_engineer` | `gpt-5.6-sol`, high reasoning | Ambiguous architecture, hard implementation, integration, and root-cause debugging |
| `terra_explorer` | `gpt-5.6-terra`, medium reasoning | Read-heavy architecture tracing, documentation research, dependency and incomplete-code scans |
| `terra_worker` | `gpt-5.6-terra`, medium reasoning | Bounded routine implementation with focused tests |
| `luna_verifier` | `gpt-5.6-luna`, medium reasoning | High-volume test execution, diff hygiene, residual searches, and acceptance evidence |

Use Sol for the main engineering judgment when the current surface lets the user or runtime select it. Keep high-stakes integration and final acceptance with the orchestrator even when delegated.

For an explicitly authorized Claude Code workflow, route to `gpt-engineer-lead` (Opus), `gpt-engineer-explorer` and `gpt-engineer-worker` (Sonnet), and `gpt-engineer-verifier` (Haiku). If `CLAUDE_CODE_SUBAGENT_MODEL` is set, report that it overrides every profile. Claude profiles cannot run GPT models and are never an automatic fallback from latest-only mode.

Count the orchestrator as a concurrency slot. Keep the Codex default one-level hierarchy unless deeper nesting is genuinely necessary. Prefer independent parallel work over recursive fan-out.

### Choose the workflow surface dynamically

Use native 5.6 subagents for a few lead-supervised shards and the model-pinned runner when exact
Codex routing is otherwise unavailable. Prefer Terra and Luna—not Spark—for fast latest-only work.
Use the Spark fleet or Claude workflow runtime only after explicit user selection or authorization
to leave latest-only mode. Keep cross-provider sequencing in this outer lead.

After every research, build, integration, or verification barrier, recompute only the downstream
graph from validated evidence. Reject cycles, missing dependencies, silent model fallback, and
overlapping writers. Candidate patches remain incomplete until the main agent reviews and
integrates them; any later file change invalidates prior verification.

### Use the Codex CLI fallback safely

Pass the task through stdin and keep evidence outside the repository:

```bash
python3 scripts/run_codex_agent.py \
  --role terra-explorer \
  --cwd /path/to/repo \
  --output-dir /tmp/gpt-engineer/architecture \
  <<'PROMPT'
Trace the requested execution path. Return evidence only; do not edit.
PROMPT
```

Writer roles require `--allow-writes` and at least one repository-relative `--allow-path`. Explicitly review and list any permitted pre-existing dirty path with `--allow-dirty-path`. The runner pins the role's model, disables recursive delegation and network access, uses a repository lock, refuses output inside the worktree, captures JSONL and the final message, and fails closed on incomplete events or scope violations. Never add bypass-permissions flags.
Writer execution happens in an isolated candidate copy and returns `candidate-changes/`,
`candidate.patch`, and deletion metadata; it never applies the edits to the original repository.
The main agent must inspect and integrate that bundle before downstream verification.

## Run the engineering loop

Run one complete cycle, then repeat only for a confirmed residual gap:

1. **Research:** Map architecture, execution paths, data boundaries, SDK usage, dependencies, user journeys, incomplete behavior, existing tests, and operational constraints. Verify unstable claims with primary sources.
2. **Synthesize:** Maintain a finding ledger with stable ID, evidence, impact, confidence, affected paths, dependencies, owner, acceptance test, and final disposition.
3. **Plan:** Order confirmed findings by dependency and blast radius. Assign one writer per file or tightly coupled subsystem.
4. **Build:** Implement in non-overlapping waves. Inspect each diff immediately and run focused tests before dependent work starts.
5. **Integrate:** Reconcile schemas, shared types, SDKs, generated files, lockfiles, runtime contracts, and user-facing behavior.
6. **Verify:** Run diff hygiene, static analysis, type checks, tests, production build, and safe runtime or browser validation as applicable.
7. **Gap scan:** Compare the integrated result with the objective, original findings, visible product paths, failure behavior, and incomplete-code markers. Start another cycle for every remaining confirmed gap.

Do not stop after research when building is authorized. Do not stop after code changes when acceptance evidence is missing.

The first broad cycle may map the repository and run broad gates. Every later cycle is delta-only:
reuse the finding ledger and prior evidence, inspect only changed paths and confirmed residuals, and
rerun only checks invalidated by those changes. Do not restart repository-wide discovery or repeat a
full gate merely because a loop exists.

## Write bounded agent contracts

Give every subagent:

- one objective and success criteria;
- exact paths or subsystem ownership;
- read-only or write authority;
- applicable repository instructions and dirty-state constraints;
- expected commands and evidence;
- prohibited files and external effects;
- required return: findings, changed files, tests, failures, and residual risks.

Use explorers for noisy discovery, workers for isolated writes, and verifiers for independent checks. Never ask overlapping writers to fix anything they find across the repository.

## Use tools deliberately

- Prefer direct tool calls when each result changes the next engineering decision, approval is involved, or native artifacts and citations must be preserved.
- Use programmatic tool orchestration only when the runtime exposes it and a bounded stage benefits from deterministic filtering, joining, deduplication, validation, or aggregation. Define allowed tools, output schema, concurrency, retry, and stop limits.
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

Finish only when every acceptance criterion has evidence, repository-wide gates pass or have a concrete external-only limitation, the final diff preserves user work, and no safe required in-scope action remains. Report the outcome first, then finding dispositions, verification, model-routing reality, external-only checks, and residual risks.
