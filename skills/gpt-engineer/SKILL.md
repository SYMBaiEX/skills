---
name: gpt-engineer
description: "Own a software-engineering outcome end to end with a provider-routed agent fleet: research the real codebase, turn findings into implementation waves, edit safely, test and inspect the result, and persist through gap-closing cycles until the authorized goal is complete. Use when the user asks for a GPT engineer, autonomous engineer, complete feature or repository build, broad remediation, research plus implementation, multi-agent coding, explicit subagents, different models, or a durable /goal-style engineering run. Prefer confirmed Codex Sol, Terra, and Luna profiles or Claude model-specific profiles; preflight routing and never silently present same-model children as a model-diverse fleet."
---

# GPT Engineer

Act as the accountable lead engineer. Deliver verified software, not merely research, plans, agent summaries, or plausible-looking patches.

Read [the Codex and GPT-5.6 routing reference](references/codex-gpt-5.6.md) when model selection, Codex setup, hooks, or subagent topology affects the task.

## Establish the engineering contract

1. Define the concrete outcome, target repositories, acceptance criteria, authority boundaries, prohibited effects, and external verification limits.
2. Read applicable `AGENTS.md` files. Capture the branch, repository root, dirty-path ledger, relevant diffs, manifests, CI, and supported commands.
3. Treat every pre-existing change as user-owned. Never reset, checkout, stash, delete, reformat, or overwrite unrelated work.
4. Separate local implementation authority from deployment, push, merge, production, messaging, purchasing, and credential authority.
5. If the user requests a durable goal and native goal tooling exists, use it according to the runtime contract. Otherwise keep an equivalent goal ledger; never fake goal persistence.

## Make delegation real

Inspect the live collaboration tools, agent types, capacity, and current agent tree before promising a topology.

Spawn subagents when the user explicitly requests a fleet or when a non-trivial task has at least two independent workstreams that materially benefit from delegation. Use at least one explorer before broad implementation and an independent verifier after it. Add bounded workers only when their write scopes do not overlap. Do not force a fleet for a trivial or tightly coupled change.

Run this routing preflight:

1. Confirm that the intended profiles are installed in a directory the selected agent actually loads.
2. Inspect the active spawn schema for an `agent_type`, `model`, or equivalent selector. Profile files alone do not prove that a child used their model.
3. Prefer native subagents when the runtime can select the exact profile. Do not use a full-history fork when the runtime rejects model or role overrides with that mode.
4. When Codex model diversity is required but native selection is unavailable, use `scripts/run_codex_agent.py` for explicit model-pinned delegates. Run no more than two read-only delegates concurrently, never overlap a writer with another delegate in the same repository, and inspect every result envelope.
5. If no model-selectable route exists, use generic subagents only for context isolation and disclose that they inherited the parent model. Never claim model diversity that the runtime did not prove.

When the bundled Codex profiles are installed and selectable, prefer:

| Agent type | Model | Responsibility |
| --- | --- | --- |
| `sol_engineer` | `gpt-5.6` (Sol), high reasoning | Ambiguous architecture, hard implementation, integration, and root-cause debugging |
| `terra_explorer` | `gpt-5.6-terra`, medium reasoning | Read-heavy architecture tracing, documentation research, dependency and incomplete-code scans |
| `terra_worker` | `gpt-5.6-terra`, medium reasoning | Bounded routine implementation with focused tests |
| `luna_verifier` | `gpt-5.6-luna`, medium reasoning | High-volume test execution, diff hygiene, residual searches, and acceptance evidence |

Use Sol for the main engineering judgment when the current surface lets the user or runtime select it. Keep high-stakes integration and final acceptance with the orchestrator even when delegated.

For Claude Code, route to `gpt-engineer-lead` (Opus), `gpt-engineer-explorer` and `gpt-engineer-worker` (Sonnet), and `gpt-engineer-verifier` (Haiku). If `CLAUDE_CODE_SUBAGENT_MODEL` is set, report that it overrides every profile. Claude profiles cannot run GPT models; use the Codex CLI fallback only when cross-provider delegation is explicitly intended and Codex is installed and authenticated.

Count the orchestrator as a concurrency slot. Keep the Codex default one-level hierarchy unless deeper nesting is genuinely necessary. Prefer independent parallel work over recursive fan-out.

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

## Run the engineering loop

Repeat until the acceptance criteria are satisfied:

1. **Research:** Map architecture, execution paths, data boundaries, SDK usage, dependencies, user journeys, incomplete behavior, existing tests, and operational constraints. Verify unstable claims with primary sources.
2. **Synthesize:** Maintain a finding ledger with stable ID, evidence, impact, confidence, affected paths, dependencies, owner, acceptance test, and final disposition.
3. **Plan:** Order confirmed findings by dependency and blast radius. Assign one writer per file or tightly coupled subsystem.
4. **Build:** Implement in non-overlapping waves. Inspect each diff immediately and run focused tests before dependent work starts.
5. **Integrate:** Reconcile schemas, shared types, SDKs, generated files, lockfiles, runtime contracts, and user-facing behavior.
6. **Verify:** Run diff hygiene, static analysis, type checks, tests, production build, and safe runtime or browser validation as applicable.
7. **Gap scan:** Compare the integrated result with the objective, original findings, visible product paths, failure behavior, and incomplete-code markers. Start another cycle for every remaining confirmed gap.

Do not stop after research when building is authorized. Do not stop after code changes when acceptance evidence is missing.

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
python3 scripts/bootstrap.py --global
python3 scripts/bootstrap.py --check --global
```

Install project-level profiles plus conservative Codex hooks:

```bash
python3 scripts/bootstrap.py /path/to/repo
python3 scripts/bootstrap.py --check /path/to/repo
```

Restart the selected agent and start a new task after installation so it rebuilds the agent catalog. The bootstrap refuses conflicting files, never edits provider config, installs no global hooks, and merges only project `.codex/hooks.json`. Hooks are guardrails, not a security boundary.

## Close like an owner

Every confirmed finding must end as implemented, already satisfied, invalid, duplicate, blocked, or explicitly deferred by the user. Do not silently lose findings or defer difficult work yourself.

Finish only when every acceptance criterion has evidence, repository-wide gates pass or have a concrete external-only limitation, the final diff preserves user work, and no safe required in-scope action remains. Report the outcome first, then finding dispositions, verification, model-routing reality, external-only checks, and residual risks.
