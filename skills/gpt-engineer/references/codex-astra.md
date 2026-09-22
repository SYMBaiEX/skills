# Codex routes and compatibility adapter

This historical filename is retained for existing links. GPT-6 Astra is parent-only: it may be
the active orchestrator/chat model, but it is never a GPT Engineer worker, verifier, fallback, or
spawned profile. GPT-6 Sol and GPT-6 Luna are the only bundled child models. See
[model routing](model-routing.md) for the complete policy and official source links.

The optional Codex profile bundle includes Sol engineer/explorer/worker/verifier and Luna
explorer/worker/verifier profiles. Sol profiles begin at medium effort (high for independent
verification); Luna profiles begin at high effort. These are starting defaults, not hard limits on
the native model. The runtime's available efforts and profile precedence remain authoritative.

Use [runtime integrations](runtime-integrations.md) for installation, trust, upgrade, and removal.
The upgrade backs up and retires only exact skill-managed Astra child profiles. Customized or
unknown old Astra profiles are preserved and should be reviewed; the route audit flags them as
unsafe GPT Engineer targets. Profile registration is not evidence that a run used the profile.

## Guarded CLI adapter

Prefer native collaboration for interactive work and the official Codex SDK/app-server for new
application controllers. The adapter remains only for an explicit headless/isolation or
cross-provider gap: candidate copies, path scope, repository locks, process groups, bounded output,
structured handoffs, and private lifecycle evidence. It disables recursive delegation and network
access. It does not automatically integrate candidates.

For a generic role, select an exact GPT-6 Sol or Luna model and effort. An Astra parent must use an
explicit mixed-model policy; same-model is available only when the selected Sol/Luna parent matches
the child. The CLI caller supplies the observed parent identity; the adapter cannot attest the
parent's session.

```bash
python3 scripts/run_codex_agent.py \
  --role explorer --model gpt-6-sol --reasoning-effort medium \
  --parent-model gpt-6-astra --policy mixed-model \
  --compatibility-reason headless-isolation-required \
  --stage-id architecture-map --cwd /path/to/repo \
  --output-dir /tmp/gpt-engineer/architecture < /path/to/task-packet.txt
```

Writer roles need `--allow-writes` and owned repository-relative `--allow-path` values. Dirty-path
exceptions use `--allow-dirty-path`. Inspect result.json, candidate changes/deletions, checks, and
route evidence before integration. Serialize candidate writers for the same repository. A
successful dry run establishes command construction, not effective provider/model execution.
Retain separate requested and effective fields.

There is no default child runtime deadline. For an explicit operator deadline, pass `--timeout`
with a positive number of seconds. A timeout triggers owned-group shutdown and reports failure;
it never proves that a task was completed. Keep a supervising owner and process handle for an
unlimited-duration invocation; inspect progress and use cancellation when required. Lock
acquisition, metadata probes, and shutdown grace periods keep their short operational timeouts.
Output limits still bound retained evidence; truncated evidence cannot pass acceptance.

Shutdown escalates graceful signals to forced termination for the registered process group even
after its leader exits. `cleanupVerified` requires a reaped direct child and an absent group;
lingering, zombie, or inaccessible groups are unverified and cannot pass acceptance. Descendants
that create a different session are outside this group guarantee and require separately recorded
ownership/cleanup handles. Do not discover or kill unrelated processes to manufacture clean status.
