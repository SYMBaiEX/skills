# Fleet observability

Use this reference to tune a GPT Engineer run from evidence rather than perceived age, thread count,
or raw token totals.

## Establish the window

Record the requested start and snapshot end in UTC and local time. Codex's local stores can have
different retention windows:

- `~/.codex/logs_2.sqlite` contains OTel logs when local telemetry is enabled.
- `~/.codex/state_5.sqlite` contains thread identity, model, role, timestamps, and spawn edges.
- `~/.codex/thread_history_1.sqlite` contains projected turn status and duration for only the
  locally projected subset.
- rollout JSONL paths recorded in `state_5.sqlite` provide detailed evidence but can contain copied
  or inherited event streams; do not sum them without a thread/turn deduplication key.

Report each source's minimum and maximum timestamp before interpreting it. A retained window that
starts after a skill release cannot prove what happened in the missing interval. Label UTC dates
explicitly when local evening activity crosses midnight UTC.

For a repeatable route, latency, concurrency, and retention snapshot, run:

```bash
python3 scripts/audit_fleet.py \
  --since 2026-08-30T00:00:00-05:00 \
  --until 2026-09-04T15:25:24-05:00 \
  --root-thread <root-thread-id> \
  --json
```

Use an explicit exclusive `--until` for a reproducible snapshot. Omit `--root-thread` only when
intentionally auditing every spawned child in the time window. The
script does not sum token attributes because the same cumulative usage can appear on many nested
OTel rows; use a turn/request-deduplicated query for token analysis. It also cannot reconstruct
command retries, compactions, or finding acceptance from the three SQLite summaries alone. Combine
its output with runner `result.json` lifecycle envelopes and targeted rollout analysis when those
metrics matter.

Use `--dispatch-suite astra` or `--dispatch-suite economy` only when the selected audit window's
dispatch contract is known to use that v2 policy. Omission preserves historical interpretation and
reports post-cutover retired profiles as diagnostics rather than assuming every running task upgraded.

When the durable run journal is available, join normalized outcomes without copying raw logs:

```bash
python3 scripts/join_fleet_outcomes.py \
  --journal "${XDG_STATE_HOME:-$HOME/.local/state}/gpt-engineer" \
  --result-dir /path/to/external/runner-evidence \
  --since 2026-08-30T00:00:00-05:00 \
  --json
```

The joiner hashes identifiers by default, diagnoses ambiguous IDs and retention gaps, and keeps
dispatch, route, result-envelope, projected, OTel-covered, and accepted-outcome denominators
separate. It never treats a spawn edge or OTel row as an accepted engineering outcome. Read
[`run-journal.md`](run-journal.md) for the journal, cache, resume, privacy, and retention contract.

## Keep denominators separate

Use stable identities, not log-row counts:

- **dispatches:** distinct child thread IDs in `thread_spawn_edges`;
- **configured routes:** distinct children whose persisted role/profile identifies a GPT Engineer
  route;
- **projected executions:** distinct children with one or more `thread_turns` rows;
- **OTel-covered executions:** distinct thread or turn IDs with relevant retained OTel events;
- **root runs:** ultimate ancestors after recursively following spawn edges.

Never silently merge these denominators. Missing history or OTel rows usually mean retention or
projection gaps, not that a dispatch did no work. A spawn edge with status `open` is registry state,
not proof that an operating-system process is still alive.

Keep current GPT Engineer profiles, retired GPT Engineer profiles, and unattributed specialist
children separate. Distinguish the Astra cohort, retained economy routes, and historical 5.6 roles;
the public release date does not prove when a running task loaded the new skill. Validate the exact
model assigned to each role. Economy authorization requires dispatch/journal evidence and cannot be
inferred from the model name alone. A child outside the GPT Engineer profile catalog may come from another skill or
an explicit specialist workflow; it is not a GPT Engineer route violation without a journal or
dispatch identity linking it to this skill. Retired profile names remain useful for historical
baselines. Diagnose retired post-release profiles separately when the loaded routing policy is
unknown; use a confirmed dispatch policy before calling a valid older run an Astra route violation.

## Measure what changes decisions

Capture per run and per wave:

- requested and effective model, effort, service tier, agent type, and profile hash;
- ready, active, queued, completed, failed, interrupted, and cancelled lane counts;
- wall time, per-agent p50/p90/max duration, useful peak concurrency, and barrier wait time;
- parent sampling turns, child turns, command count and duration, failed commands, retries, and the
  longest command;
- input, cached input, cache-write input, non-cached input, output, reasoning output, and compaction
  count when the runtime emits them;
- accepted findings, implemented findings, rejected duplicates, and verification failures per lane.

Runtime-reported total tokens are not automatically account billing. Cache reads can be discounted
while still replaying a large context and adding latency. Deduplicate usage by thread ID, turn ID,
and the final cumulative usage event; usage attributes can appear on many nested OTel log lines.

## Diagnose slow runs

Classify wall time before changing fleet size:

1. **Parent control-loop bound:** many parent sampling turns, compactions, repeated instructions, or
  small sequential waves. Use compact delta prompts, dispatch useful ready work, and join only the
  prerequisites needed for the next decision.
2. **Child-compute bound:** long child turns with independent ready work. Increase read-only fan-out
   within the adaptive ceiling, lower effort where acceptance still passes, or split a genuinely
   oversized lane.
3. **Command bound:** tests, builds, browsers, migrations, or external RPCs dominate. Keep one owner
   and process handle, inspect before retry, and fix the harness instead of duplicating agents.
4. **Coordination bound:** repeated reviews before later writes, overlapping ownership, or large
   handoffs. Serialize integration, postpone broad review until the final write barrier, and return
   structured summaries instead of logs.
5. **Route leakage:** generic profiles select old or unintended models. Stop the lane, use an exact
   allowed agent type, and rerun `audit_routing.py` with observed route evidence.

## Tune with paired runs

Change one variable at a time on representative tasks: fleet ceiling, model, effort, prompt packet,
or test strategy. Compare accepted outcome, evidence completeness, wall time, non-cached input,
output, retries, and command failures. A larger fleet is an improvement only when independent ready
work exists and the final acceptance contract still passes.

Require a sufficiently covered sample and comparable one-variable pairs before accepting
`expand`, `lower-effort`, or `raise-effort`. Treat `insufficient-evidence` and `hold` literally. A
recommendation never edits Codex configuration, changes the pinned-suite allowlist, enables Fast or
Team mode, or authorizes a provider transition.

Compare single-agent Astra against Astra with selected delegation before increasing fleet size.
Use the same task and acceptance contract, record coordination/synthesis time, and count duplicated
findings and rework. Correctness tests for the migration do not establish a latency or cost win.
Keep prior Sol/Terra/Luna runs as historical baseline evidence rather than relabeling them Astra.

Use a Broad read ceiling of six as the default experiment, not a permanent conclusion. A qualified
Team read wave may compare seven or eight lanes against Broad, but it must measure accepted findings,
wall time, failures, context, and rework and return to Broad without a clear gain. Shrink immediately on
resource pressure, repeated transient failures, queueing, or low marginal findings. Keep shared
writers at one and isolated writers at two until measurements prove a safer higher value.
