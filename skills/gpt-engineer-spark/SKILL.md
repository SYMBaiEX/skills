---
name: gpt-engineer-spark
description: Lead end-to-end engineering work with a capable main agent and a parallel fleet of model-pinned GPT-5.3-Codex-Spark subagents. Use when the user asks for a Spark fleet, ultra-fast parallel coding agents, rapid repository exploration, many bounded implementation shards, or low-latency independent verification while retaining architecture, integration, and final acceptance with the main agent.
---

# GPT Engineer Spark

Own the outcome as the main agent. Keep planning, architecture, conflict resolution, integration, security-sensitive judgment, and final acceptance in the main thread. Delegate small, explicit shards to `gpt-5.3-codex-spark` for speed.

Read [references/codex-spark.md](references/codex-spark.md) before claiming availability, performance, or route proof.

## Establish the route

1. Confirm that the client can select a named custom agent or exact child model.
2. Check for `spark-explorer`, `spark-worker`, and `spark-verifier` in `~/.codex/agents` or `.codex/agents`.
3. If missing, tell the user this skill is installing profiles, then run:

```bash
python3 /path/to/gpt-engineer-spark/scripts/bootstrap.py --global
python3 /path/to/gpt-engineer-spark/scripts/bootstrap.py --check --global
```

Use a project path instead of `--global` for repository-scoped profiles. Restart Codex and start a new task after installation.

A profile file is configuration, not proof that a child used Spark. Prefer native custom-agent routing when the spawn surface exposes the selected agent. When it does not, use the guarded CLI fallback with an explicit `--model gpt-5.3-codex-spark` request. Never relabel an inherited or generic child as Spark.

If Spark is unavailable, rejected, throttled beyond the task budget, or the user lacks the required entitlement, report that plainly. Do not silently substitute Terra, Luna, Sol, another model, or the parent.

## Shape the fleet

Create a fleet only when at least two independent shards exist. Default to two to four Spark children and stay within the live client capacity. The normal Codex thread default is finite; never assume unlimited fan-out.

Use these roles:

- `spark-explorer`: read-only repository mapping, searches, call-flow tracing, focused audits, and evidence collection.
- `spark-worker`: one routine implementation objective within exact non-overlapping files and explicit acceptance checks.
- `spark-verifier`: read-only diff review, focused test-result inspection, regression analysis, and evidence reconciliation.

Do not let Spark children delegate. Keep the hierarchy one level deep.

Give every child:

- one objective;
- exact paths or subsystem boundaries;
- relevant constraints and initial dirty-state facts;
- commands or tests it must run or inspect;
- prohibited effects such as commit, push, deploy, dependency churn, or shared-file edits;
- a compact return contract: findings or changes, evidence, commands run, failures, and residual risks.

Spark is optimized for bounded iteration, not broad ambiguity. Keep product decisions, cross-cutting architecture, migrations, auth/crypto/security judgment, shared contracts, lockfiles, generated roots, and final acceptance with the main agent.

## Execute in waves

### 1. Map

Inspect the repository instructions and dirty state yourself. Partition the task into independent read shards. Run `spark-explorer` children concurrently and ask for evidence-rich summaries rather than raw logs.

### 2. Decide

Reconcile the returned evidence in the main thread. Inspect contradictions directly. Do not decide by majority vote. Produce a path-ownership ledger before authorizing edits.

### 3. Build

Delegate routine, well-specified changes to `spark-worker`.

- Serialize writers that share one checkout.
- Parallelize writers only in isolated worktrees or branches with disjoint ownership.
- Reserve shared files, schemas, dependency manifests, lockfiles, and generated artifacts for the main agent unless one worker owns them exclusively.
- Review every worker diff before the next write wave.

### 4. Verify

Run independent `spark-verifier` children over separate risk areas. Treat their claims as leads until backed by command output or direct inspection. The main agent must run the integrated repository gates and inspect the final diff.

### 5. Close

Account for every requirement and finding as implemented, already satisfied, invalid, duplicate, blocked, or explicitly deferred. Completion requires integrated evidence, not child confidence.

## Use the guarded fallback

When native spawn routing cannot select or expose the Spark profile, run one bounded child with:

```bash
python3 /path/to/gpt-engineer-spark/scripts/run_spark_agent.py \
  --role spark-explorer \
  --cwd /path/to/repository \
  --output-dir /private/tmp/spark-auth-scan <<'PROMPT'
Trace the authentication call flow. Do not edit. Return paths, symbols, findings, and commands run.
PROMPT
```

For a writer, also pass `--allow-writes` and one or more repository-relative `--allow-path` values.
Explicitly reviewed dirty overlaps require `--allow-dirty-path`. The runner pins the exact model,
disables recursive delegation and network access, copies the current repository into an isolated
sandboxed candidate worktree, and returns `candidate-changes/`, `candidate.patch`, and deletion
metadata. It never applies candidate edits to the original repository. The main agent must inspect
and integrate the bundle with normal editing tools, then run verification from the integrated state.

For multiple fallback children, use `run_spark_fleet.py` with a JSON manifest. Start from
`assets/read-only-fleet.example.json`. Put explorers in the same read-only wave. Candidate writers
may appear only in the terminal wave and run serially. Integrate their bundles before starting a new
verifier fleet. A required shard failure makes the fleet incomplete and stops later waves.

## Report route evidence honestly

For every child record:

- role and shard;
- route method (`native-profile` or `cli-explicit-model`);
- requested model;
- completed, failed, blocked, or unavailable status;
- changed paths and violations;
- evidence or output location.

A successful explicitly pinned CLI turn proves that the server accepted that model request. Claim stronger model attestation only when runtime metadata actually reports it.

Never report the work complete when a required shard failed, the model route was silently changed, scope was violated, verification is missing, or the integrated repository is not accepted by the main agent.
