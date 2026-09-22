# Fleet observability

For the current contract, `audit_fleet.py --dispatch-suite gpt6` asserts that active GPT Engineer
children use GPT-6 Sol or GPT-6 Luna and never Astra. It does not attest parent-child equality.
Preserve `astra`/`economy` only for explicitly identified historical cohorts. A timestamp or
currently installed skill version cannot establish which policy an old run loaded; an old Astra
child route without dispatch evidence is historical, not automatically a confirmed violation.

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
intentionally auditing the created-child cohort across parents. Its date filter selects child
creation, not all activity: older resumed children, root work, and runtime approval services need
separate activity-window queries. A fixed cutoff is not an immutable snapshot of rotating stores;
record capture time and retention changes. The
script does not sum token attributes because the same cumulative usage can appear on many nested
OTel rows; use a turn/request-deduplicated query for token analysis. It also cannot reconstruct
command retries, compactions, or finding acceptance from the three SQLite summaries alone. Combine
its output with runner `result.json` lifecycle envelopes and targeted rollout analysis when those
metrics matter.

Use `--dispatch-suite gpt6` only when the selected audit window is known to have loaded the current
policy. Use `astra` or `economy` solely for known v2.1 historical routing, not as current choices.
Omission preserves historical interpretation; pre-existing Sol/Astra records are not reclassified
by release date alone.

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
- **approval service:** source-attested native Guardian sessions, distinct request turns, and
  per-response usage; not engineering delegates or model-routing violations.

Never silently merge these denominators. Missing history or OTel rows usually mean retention or
projection gaps, not that a dispatch did no work. A spawn edge with status `open` is registry state,
not proof that an operating-system process is still alive.

Keep current GPT Engineer profiles, retired GPT Engineer profiles, and unattributed specialist
children separate. Current cohorts are GPT-6 Sol and GPT-6 Luna; Astra is an allowed parent but
never a child. Keep historic Astra-child and GPT-5.6 cohorts for longitudinal comparison; the
public release date does not prove when a running task loaded the new skill. Validate the exact
model assigned to each known role. A child outside the GPT Engineer profile catalog may come from
another skill or an explicit specialist workflow; it is not a GPT Engineer route violation without
a journal or dispatch identity linking it to this skill. Retired profile names remain useful for
historical baselines. Diagnose old routes separately when the loaded policy is unknown; use a
confirmed current dispatch policy before calling an older run a violation.

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
while still replaying a large context and adding latency. Identify the emitting source and counter
semantics before aggregating: deduplicate cumulative usage by thread/turn, or incremental response
usage by thread/response. Do not sum both representations. Numeric strings copied inside tool
output, fixture text, or prompts are not telemetry events. Missing evidence is unavailable, not zero.

Context-scope token estimates and `token_limit_reached` signals do not establish completed
compactions; require actual compaction events. Stored rollout/projection bytes also differ from
text delivered to the model and billable tokens. Examine complete turn samples and report sampling
bias. Attribute behavior to the version actually loaded, not today's installed version or release date.

For suspected repeated reads, compare call arguments, emitted content, and intervening compaction or
file changes. Pagination, different references, and necessary reloads are not redundant full reads.
Budget large mandatory instruction reads so each can be read completely without truncation; filter
ordinary search/diagnostic results before returning them. Do not cap useful engineering duration
or remove required instruction reads merely to lower a byte count.

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
6. **Approval-bound:** source-attested runtime reviews gate repeated outside-root or escalated
   actions. Check workspace scope and exact requests using
   [runtime integrations](runtime-integrations.md#approval-reviews); do not weaken safety controls.

## Tune with paired runs

Change one variable at a time on representative tasks: fleet ceiling, model, effort, prompt packet,
or test strategy. Compare accepted outcome, evidence completeness, wall time, non-cached input,
output, retries, and command failures. A larger fleet is an improvement only when independent ready
work exists and the final acceptance contract still passes.

Require a sufficiently covered sample and comparable one-variable pairs before accepting
`expand`, `lower-effort`, or `raise-effort`. Treat `insufficient-evidence` and `hold` literally. A
recommendation never edits Codex configuration, changes the supported-model contract, enables Fast or
Team mode, or authorizes a provider transition.

Compare the selected parent alone against that same parent with useful delegation before increasing
fleet size. Use the same task and acceptance contract, record coordination/synthesis time, and count
duplicated findings and rework. Correctness tests for the migration do not establish a latency or cost
win. Keep original model, effort, runtime, and loaded skill policy/version evidence. Existing
GPT-5.6 Sol/Terra/Luna parent sessions may continue during rollout, but those models are not current
GPT Engineer child routes; the child allowlist is GPT-6 Sol/Luna only.

Use a Broad read ceiling of six as the default experiment, not a permanent conclusion. A qualified
Team read wave may compare seven or eight lanes against Broad, but it must measure accepted findings,
wall time, failures, context, and rework and return to Broad without a clear gain. Shrink immediately on
resource pressure, repeated transient failures, queueing, or low marginal findings. Keep shared
writers at one and isolated writers at two until measurements prove a safer higher value.
