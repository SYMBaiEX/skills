# Dynamic workflow routing

Read this reference when an engineering goal needs adaptive fan-out, repeatable phases, resumable
state, or more than one provider.

## Select the execution surface

| Surface | Use it for | Limit |
| --- | --- | --- |
| Native Codex subagents | A few evidence-driven shards with direct lead supervision | Runtime may not expose a model selector |
| Model-pinned Codex runner | Exact Sol/Terra/Luna routing with external evidence | At most two readers; candidate writers are serialized |
| GPT Engineer Spark fleet | Fast, bounded exploration, candidate edits, and verification | Spark never owns architecture or final acceptance |
| Claude dynamic workflow | Repeatable high-fanout audits, migrations, cross-checking, and bounded loops | Claude models only; same-session resume |

Do not force every task through the largest surface. Start with the smallest primitive that can
hold the dependency graph and completion evidence.

## Keep one outer contract

The GPT Engineer lead owns provider transitions. Claude workflow JavaScript cannot select GPT
models, and a Codex child cannot prove a Claude phase completed. Record every stage with:

- stable ID, objective, dependencies, provider, role, and exact requested model;
- read, candidate-write, integration-gate, or verify mode;
- path ownership, dirty-path exceptions, prohibited effects, retry and stop bounds;
- evidence directory, result status, changed paths, violations, and final disposition.

Never silently reroute a failed stage to another provider or model. A fallback must be explicitly
authorized in the stage contract and recorded as a new attempt.

## Build the graph from evidence

Treat the first plan as provisional. After each barrier:

1. validate returned evidence and reject unsupported findings;
2. add, remove, split, or reorder downstream nodes based on the new facts;
3. reject missing dependencies, cycles, and overlapping writer scopes;
4. run ready read-only nodes concurrently within the live capacity;
5. serialize candidate writers and stop at a main-agent integration gate;
6. invalidate verification whenever the integrated files change;
7. start another bounded gap-closing cycle only for confirmed residual work.

Dynamic does not mean unbounded. Persist the resolved graph, attempts, and completion barriers so a
restart cannot reinterpret a partial run as complete.

## Provider-specific completion

- **Codex/Spark:** inspect each `result.json`. Candidate patches are artifacts, not integrated code.
  Apply them only after main-agent review, then run verification in the real checkout.
- **Claude:** prefer the saved JavaScript workflow or Agent SDK `Workflow` tool over keyword-based
  triggering. Preserve `runId`, `scriptPath`, and `transcriptDir`. Resume only in the same session.
- **All providers:** natural-language confidence is never a completion barrier. Required nodes,
  integration, and post-change checks need machine-readable success and direct evidence.

For Claude-specific script and permission semantics, read the installed
`claude-multi-agent/references/WORKFLOWS.md` and the official
[dynamic workflow documentation](https://code.claude.com/docs/en/workflows).
