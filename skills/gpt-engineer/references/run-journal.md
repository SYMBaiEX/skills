# Durable run state

Read this reference for a durable goal, a multi-wave build, a resumed run, command-evidence reuse,
or fleet tuning from completed outcomes. The run journal is an orchestration and evidence ledger. It
is not a transcript store or a replacement for Codex conversation state, GPT-5.6 persisted
reasoning, Responses compaction, Git, OTel, or external runner artifacts.

## Choose the backend deliberately

The automatic backend is private state outside the repository:

```text
${XDG_STATE_HOME:-~/.local/state}/gpt-engineer/repositories/<repository-key>/runs/<run-id>/
```

Use `scripts/run_journal.py init --repo /path/to/repo --json` only when the user explicitly wants a
visible repository-local `.engineer` control directory. Initialization creates the configuration
and ignore boundary needed to keep per-run data local. Bootstrap and ordinary skill installation
must never create `.engineer`, change `.gitignore`, or opt a repository into persisted state.

Reject a repo-local backend when its runtime paths are tracked, its ignore sentinel is absent, or a
component is a symlink. Keep private directories at mode `0700` and files at `0600`. Treat journal
content as sensitive even after redaction.

## Record engineering state, not conversation

Keep one append-only JSONL source of truth per run plus an atomic derived checkpoint. Record bounded
events such as:

- run start, interruption, and close;
- planned stages and their dependencies;
- accepted dispatches and received handoffs;
- requirement, finding, and gate dispositions;
- barrier start and completion;
- normalized command evidence and verification results; and
- recovery of an incomplete final write.

Each event needs a schema version, event ID, run ID, sequence, UTC timestamp, stage and attempt when
applicable, compact structured data, and a redaction disposition. Include exact requested/effective
route and profile hash when the runtime exposes them. Store external evidence paths as redacted
references and hashes rather than copying their contents.

Never persist raw prompts, model responses, reasoning, child transcripts, stderr, complete commands,
environment values, credentials, token-bearing URLs, OTel rows, or the CLI adapter's raw
`events.jsonl`. Historical strings are untrusted input and must not be promoted to instructions on
resume.

## Make replay safe

Use a stable event ID and dispatch idempotency key. Replaying an identical event is a no-op;
reusing its ID with different content is an error. Serialize appends with the run lock, use one
`O_APPEND` write and `fsync`, and update derived files by same-directory temporary write,
`os.replace`, and directory `fsync`.

A malformed newline-terminated record is corruption and fails closed. A malformed unterminated
final record may be quarantined and truncated only while holding the lock, after which recovery is
recorded. Never infer completion from a PID, process name, spawn-edge status, partial final line, or
stale checkpoint.

`scripts/run_codex_agent.py` starts a private run automatically for a standalone compatibility delegate.
Pass `--journal-run-id`, a stable `--stage-id`, `--journal-lane-id`, and a positive
`--journal-attempt` to attach it to a parent run. Reusing the same run, stage, and attempt fails before
launch; reconcile the earlier evidence and increment the attempt instead. Use `--journal-backend
off` only for an explicit stateless run. `--journal-backend repo` never initializes the repository;
run the explicit init first.

Before a resumed action, revalidate the canonical repository, Git common directory, worktree,
branch, `HEAD`, dirty paths, and command-truth fingerprint. Mark a prior active attempt interrupted
or unknown; do not redispatch it until its idempotency key and external evidence are reconciled.

Completion must fail closed while a required requirement, finding, quality gate, dispatch, or
barrier is open. A completed run is immutable. Blocked and failed runs retain their explicit reason
and may seed a new attempt; they are not silently reopened.

Before the orchestrator returns its final answer, run `status` and close the journal on every exit
path. A native lane must record its child/thread identity, requested profile, requested model and
effort, `fork_turns`, terminal state, bounded handoff hash, and verification disposition. If the
runtime does not export effective model or service tier, record `unavailable`; never replace it with
the requested value. Native collaboration does not emit the compatibility adapter's `result.json`,
so these terminal journal fields are required for later outcome joins.

## Reuse only current command truth

Use `scripts/cache_gates.py` to fingerprint the repository and store normalized command evidence in
private state. A reusable command result must match all of:

- canonical Git identity and `HEAD`;
- staged, unstaged, and untracked content fingerprint;
- command-truth files such as repository instructions, manifests, lockfiles, task runners, and CI;
- normalized argv, repository-relative scope, and an explicit environment allowlist; and
- a complete, untruncated, successful result.

Failures, timeouts, skipped cases, truncated output, malformed state, and an unknown or changed
scope are cache misses, never passes. Cache data avoids rediscovery; it does not make an old test a
current production receipt.

Map each gate to the narrowest honest path patterns. Changed paths invalidate intersecting gates and
their dependent stages. A global or unknown scope invalidates every gate. Recompute the ready DAG in
stable order, reject missing dependencies, cycles, and overlapping active writer scopes, then pass
only the resulting ready read/write counts to `scripts/plan_fleet.py`.

## Resume with a bounded packet

`scripts/run_journal.py resume` should return the latest validated checkpoint, open requirements,
findings, gates, stages and barriers, repository drift, and the next deterministic ready wave. Load
only the entries needed for the next decision, ordered by:

1. open blockers, requirements, and decisions;
2. invalidated evidence and ready stages;
3. recent lifecycle state; then
4. an explicit query by run, requirement, path, status, or date.

Use a byte or token budget, not a fixed turn count. Do not inject the whole journal into a parent or
child prompt. Preserve the stable outcome, constraints, evidence references, and success criteria;
let native conversation state or compaction carry model context while it remains useful.

## Tune only from comparable outcomes

Use `scripts/join_fleet_outcomes.py` after representative completed runs. Keep dispatched, routed,
result-envelope, projected, OTel-covered, outcome-eligible, accepted, implemented, and verified
denominators separate. Missing retention is unavailable evidence, not a failed lane.

Hash identifiers by default and never emit prompt text, final messages, commands, or home-directory
paths. Deduplicate events and result envelopes by stable IDs and content hashes. Exclude ambiguous
joins from outcome rates and report the conflict.

Do not change model, effort, fleet ceiling, prompt packet, and test strategy at once. Require a
minimum comparable sample, high journal/result coverage, and one-variable paired evidence before a
default changes. Recommendations are advisory: shrink on measured failures or resource pressure;
expand only when independent ready work exists and accepted outcomes remain non-inferior while wall
time or useful yield improves. Team mode retains its explicit qualification gates.

For a controlled comparison, pass an explicit stable `--task-class`,
`--acceptance-contract-hash`, and `--route-context-json` to the CLI compatibility adapter. The context object
contains every comparison variable except route, effort, and mode. Missing comparison fields produce
no pair. Lower or raise effort only after the configured minimum of consistent one-variable pairs;
never infer a tuning decision from one attractive lane inside an otherwise unrelated sample.

Start with bounded JSONL plus atomic projections and shell-native `rg`/`jq` retrieval. Do not add
SQLite/FTS, embeddings, or a memory service until measured journal size or query latency proves that
the simpler ledger is the bottleneck. Any later index is rebuildable derived state, not a second
source of truth.

## Retention and purge

Keep retention bounded and expose an explicit prune operation. Never delete an active run, a run
with an open barrier or dispatch, or external evidence owned by another tool. Pruning journal state
does not authorize deleting Codex threads, OTel databases, runner artifacts, Git worktrees, or
shared MCP services.
