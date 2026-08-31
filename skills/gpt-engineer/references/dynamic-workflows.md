# Dynamic workflow routing

Read this reference when an engineering goal needs adaptive fan-out, repeatable phases, resumable
state, or more than one provider.

## Select the execution surface

| Surface | Use it for | Limit |
| --- | --- | --- |
| Native Codex subagents | A few evidence-driven shards with direct lead supervision | Runtime may not expose a model selector |
| Model-pinned Codex runner | Exact Sol/Terra/Luna routing with external evidence | At most two readers; candidate writers are serialized |
| Responses API Multi-agent beta | One-model hosted fan-out in an API application | Subagents share the request model; not a mixed Sol/Terra/Luna router |
| GPT Engineer Spark fleet | Explicitly requested fast, bounded exploration, candidate edits, and verification | Opt-in older model; Spark never owns architecture or final acceptance |
| Claude dynamic workflow | Explicitly authorized repeatable high-fanout audits, migrations, cross-checking, and bounded loops | Opt-in separate provider; same-session resume |

Do not force every task through the largest surface. Start with the smallest primitive that can
hold the dependency graph and completion evidence.

Latest-only is the default. Use exact Sol, Terra, and Luna routes unless the user explicitly selects
Spark, Claude, or another provider. Never treat provider fallback as a speed optimization.

## Keep one outer contract

The GPT Engineer lead owns provider transitions. Claude workflow JavaScript cannot select GPT
models, and a Codex child cannot prove a Claude phase completed. Record every stage with:

- stable ID, objective, dependencies, provider, role, and exact requested model;
- read, candidate-write, integration-gate, or verify mode;
- path ownership, dirty-path exceptions, prohibited effects, retry and stop bounds;
- decision unblocked, maximum output, cancellation condition, and handoff schema;
- evidence directory, result status, changed paths, violations, and final disposition.

Never silently reroute a failed stage to another provider or model. A fallback must be explicitly
authorized in the stage contract and recorded as a new attempt.

## Build the graph from evidence

Treat the first plan as provisional. After each barrier:

1. validate returned evidence and reject unsupported findings;
2. add, remove, split, or reorder downstream nodes based on the new facts;
3. reject missing dependencies, cycles, and overlapping writer scopes;
4. dispatch every independent ready read-only node in one wave within the adaptive limit;
5. serialize candidate writers and stop at a main-agent integration gate;
6. invalidate verification whenever the integrated files change;
7. start another bounded gap-closing cycle only for confirmed residual work.

Dynamic does not mean unbounded. Persist the resolved graph, attempts, and completion barriers so a
restart cannot reinterpret a partial run as complete.

## Size waves adaptively

Treat configured and runtime capacity as ceilings. Compute a wave from independent ready work,
write isolation, recent failures, and local resource pressure:

| Mode | Normal child ceiling | Shape |
| --- | ---: | --- |
| Fast | 1 | Known isolated task or one deterministic check |
| Standard | 3 | Two or three independent reads, or one writer plus focused support |
| Broad read | 6 | Four to six bounded exploration, triage, test, or summarization lanes |
| Team read | 8, opt-in | Seven or eight qualified logical-specialist lanes for whole-product discovery or final review |
| Write wave | 3 shared / 4 isolated | One shared-checkout writer, or two disjoint candidate writers, plus at most two readers |

Current official Codex examples show a six-point parallel review, one project with a six-thread cap,
and another with an eight-thread cap. They are examples, not an OpenAI claim that either number is
optimal. Broad remains the default. Team is a read-only experiment that requires at least seven
independent decision-bearing lanes, exact route attestation, no host pressure, and a paired outcome
comparison. Never manufacture shards to fill capacity.

Use the deterministic planner when topology is not obvious:

```bash
python3 scripts/plan_fleet.py \
  --mode team \
  --team-qualified \
  --routes-attested \
  --lanes-independent \
  --paired-comparison \
  --runtime-child-cap 8 \
  --ready-reads 8 \
  --ready-writers 0 \
  --json
```

Team mode rejects writers and fails closed unless every admission flag is present; it also rejects
resource pressure, high prior failure, and live capacity below seven. Plan every build wave in Broad
mode. Qualification means the lead has applied the criteria in
[`engineering-standards.md`](engineering-standards.md), not merely that eight slots are configured.
Use `--writers-isolated` only when writers have disjoint path ownership and candidate worktrees.
Use `--resource-pressure` or the previous wave's failure rate to shrink Fast, Standard, or Broad;
either condition disqualifies Team. A configured
Codex child cap excludes the primary thread, but the primary still belongs in the usage and
coordination budget.

Dispatch the complete wave before waiting. Join at one barrier, validate the compact handoffs,
integrate once, then recompute the ready set. Repeated micro-waves add parent turns and replay context
without increasing useful concurrency. Reuse a completed agent for a related follow-up instead of
spawning a duplicate lane, and do not use a full-history fork when a compact delta packet is enough.

## Control long-running gates

Give each long test, build, migration, or browser suite one owner and one live process handle. A
client wait timeout is not a test failure. Inspect the existing process and last output before any
retry; retry a classified transient transport or runner failure at most once. CPU- or I/O-bound
commands do not become faster merely because more agents wait on duplicates.

Run focused checks with the owning writer. Save broad independent review and repository-wide gates
for the post-integration verification wave. A later source change invalidates only affected focused
checks plus the final broad gate, not the entire discovery phase.

## Provider-specific completion

- **Codex/Spark:** inspect each `result.json` and structured handoff. Candidate patches are
  artifacts, not integrated code. Apply them only after main-agent review, then run verification
  in the real checkout.
- **Claude:** prefer the saved JavaScript workflow or Agent SDK `Workflow` tool over keyword-based
  triggering. Preserve `runId`, `scriptPath`, and `transcriptDir`. Resume only in the same session.
- **All providers:** natural-language confidence is never a completion barrier. Required nodes,
  integration, and post-change checks need machine-readable success and direct evidence.

At every barrier persist the stage attempts, route, start/end time, retries, active and ready counts,
command failures, compactions, and token fields the runtime exposes. See
[`fleet-observability.md`](fleet-observability.md) before comparing runs or changing a default.

For Claude-specific script and permission semantics, read the installed
`claude-multi-agent/references/WORKFLOWS.md` and the official
[dynamic workflow documentation](https://code.claude.com/docs/en/workflows).
