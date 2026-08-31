# Codex and GPT-5.6 routing

Use this reference when selecting models, defining Codex custom agents, or deciding whether hooks or deeper orchestration are appropriate. Recheck the linked official documentation when current availability or configuration syntax matters.

## Model roles

- **Sol:** use the explicit `gpt-5.6-sol` identifier for strict routing. The `gpt-5.6` family alias currently routes to Sol, but an alias is weaker evidence than an explicit target.
- **Terra:** `gpt-5.6-terra` balances intelligence and cost. Codex specifically recommends it for exploration, read-heavy scans, large-file review, and supporting-document work. It is also suitable for bounded routine implementation.
- **Luna:** `gpt-5.6-luna` is the fastest, lowest-cost family member for clear, repeatable, or high-volume work. Use it for deterministic transformations, narrow mechanical changes, test matrices, residual searches, and structured evidence collection. Keep ambiguous architecture, semantic acceptance, and high-risk decisions with Terra, Sol, or the orchestrator.

GPT-5.6 supports `none`, `low`, `medium`, `high`, `xhigh`, and `max` in the API. Current Codex surfaces also expose higher efforts when the selected model supports them. Use the lowest effort that passes representative checks: low for clear latency-sensitive work, medium as the normal baseline, and high or above only for measured hard cases. The bundled Luna worker uses low; the everyday Terra lanes and Luna verifier use medium; the Sol specialist uses high. The separate `luna_max_worker` pins Max plus the Fast service tier and is deliberately opt-in because both choices can increase usage.

## Codex custom agents

Current Codex releases load user agents from `~/.codex/agents/*.toml` and project agents from `.codex/agents/*.toml`. Required fields are `name`, `description`, and `developer_instructions`; model, reasoning effort, sandbox, MCP servers, and skill config are optional overrides.

`agents.max_concurrent_threads_per_session` caps spawned threads and excludes the primary thread. The live collaboration tool may instead report total active-agent capacity, so inspect the active contract rather than assuming a fixed number. Current official Codex examples include six- and eight-thread project caps plus a six-lane PR review, but they do not prescribe a universal optimum. GPT Engineer therefore uses one/three/six Fast, Standard, and Broad read ceilings plus an explicitly qualified, read-only Team ceiling of eight. Shared writers remain serialized and isolated write waves remain capped at two writers plus at most two readers. More agents and nesting increase tokens, latency, local resource use, and repeated fan-out risk.

Subagents are enabled in current Codex releases and can be requested directly or by applicable `AGENTS.md` or skill instructions. Each child performs independent model and tool work, so a fleet consumes more usage than a comparable single-agent run. ChatGPT Work can also run parallel hosted subagent workflows where available.

Agent files are configuration, not proof of selection. Record the effective profile source, `name`, exact model, effort, and file hash. A project-scoped profile with the same `name` can shadow a user profile. When a custom file specifies model or effort, that value wins; otherwise Codex resolves explicit spawn value, the corresponding `[agents]` default, then the parent value. If a spawn changes only the model, that model's default effort applies. Immediately inspect the spawned agent metadata when the client exposes it; interrupt a generic, unknown, or disallowed route rather than discovering leakage after a long run.

Inspect the current spawn tool for an agent-type or model selector. Native custom agents are the
normal interactive path. For a new programmatic controller, prefer the stable official Codex SDK
where it covers the need, requesting model and sandbox per thread; version-pin app-server and
feature-detect experimental APIs. The bundled `run_codex_agent.py` is only a guarded CLI
compatibility adapter when native/SDK routing or isolation is unavailable; it requires a recorded
compatibility reason and does not independently attest the provider's effective model. In latest-only mode, never use a generic or inherited child as a fallback. Use
`scripts/audit_routing.py --runtime` to fail closed on missing/conflicting profiles, an invalid active
runtime, and stale or unattested custom catalogs.

Avoid synthetic model-call smoke tests. They can load the entire global skill/tool surface and spend
substantial context without proving that a child ran. Use the local preflight first, then treat the
first useful bounded stage as the canary and require runtime-exported child metadata when effective
route attestation is necessary. An echoed marker alone is not attestation.

## Strict and fast routing

The default GPT Engineer route allows only `gpt-5.6-sol`, `gpt-5.6-terra`, and
`gpt-5.6-luna`. Spark and Claude remain explicit opt-in surfaces because they are not members of
the GPT-5.6 family. If the required model cannot be requested without substitution, keep the work
with a parent whose effective route is exported and allowed, or report the blocker. Configuration
and request fields prove the requested route only; claim an effective route only from matching
runtime-exported execution metadata.

Use medium reasoning as the normal baseline, low for clear latency-sensitive work
when validation still passes, and high only for hard judgment. Do not raise reasoning automatically.
Codex Fast mode can speed supported GPT-5.6 models at higher credit use; it is a user/runtime choice,
not a model substitution.

## Custom Luna catalog quarantine

Some Codex runtime/cache combinations can mark Sol and Terra as Multi-Agent V2 while marking Luna as
V1. The V2 spawn path can then reject Luna before execution. This is a compatibility defect, not a
stable public contract or a normal part of GPT Engineer setup.

Prefer updating/selecting the newest supported runtime, removing any stale override, restarting, and
testing a fresh native Luna route. While Luna is blocked, use the explicit-model-request CLI compatibility
adapter rather than freezing the full model catalog. `scripts/audit_routing.py --runtime` reports
runtime version skew and rejects a stale managed catalog or an arbitrary custom catalog it cannot
attest.

Use `scripts/configure_luna_v2.py --apply --acknowledge-unsupported-catalog-override` only after the
owner accepts the frozen-metadata risk and the script validates the exact mismatch. The script derives a
managed catalog from the current `~/.codex/models_cache.json`, changes only Luna's
`multi_agent_version` to `v2`, materializes the required `supports_reasoning_summaries` cache default,
validates the generated schema in a fresh Codex CLI process, and points the supported top-level
`model_catalog_json` setting at the copy. It can also enable `features.fast_mode`; the `luna_max_worker` profile independently pins
`service_tier = "fast"`. Native spawns should select `agent_type="luna_max_worker"` with
`fork_turns="none"` so neither model nor history is inherited from the Sol orchestrator.

This workaround has operational costs:

- Codex snapshots custom catalog content at process startup, so every apply, refresh, or disable
  requires a full restart.
- A custom catalog freezes upstream metadata. If the source cache changes, disable the override;
  never refresh it from an older client cache merely to make the audit pass.
- Desktop and app-server catalog behavior has had active bugs. The CLI compatibility adapter can
  fail closed on the requested model and local guardrails, but only runtime-exported metadata can
  attest the effective route. Verify any native route in a fresh process.
- Fast mode is documented as faster with increased usage. Do not infer that Luna Max/Fast is cheaper
  than Terra standard without current account-level measurements.

When the stock Luna entry becomes V2, run `python3 scripts/configure_luna_v2.py --disable`, restart,
and return to the upstream catalog.

Primary references: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[Luna V1/V2 mismatch report](https://github.com/openai/codex/issues/34301),
[custom catalog startup caching](https://github.com/openai/codex/issues/35129), and
[Multi-Agent V2 routing limitations](https://github.com/openai/codex/issues/32705).

An optional default guard for model-less children is:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 8
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "medium"
```

This is not a latest-only enforcement boundary: an explicitly selected custom profile can still
override those defaults. A user may set the capacity ceiling to `8` while GPT Engineer keeps Broad
at six and unlocks the last two slots only for a qualified Team read wave. Lower it on constrained
hosts. The bootstrap intentionally does not rewrite user or project config.

## Claude Code agents

Claude Code loads user agents from `~/.claude/agents/*.md` and project agents from `.claude/agents/*.md`. The bundled lead, explorer, worker, and verifier profiles use the stable `opus`, `sonnet`, and `haiku` aliases. `CLAUDE_CODE_SUBAGENT_MODEL` overrides every per-agent model; surface that condition rather than claiming diversity.

Claude Code cannot natively run GPT-5.6 profiles. Cross-provider GPT delegation requires an installed,
authenticated Codex SDK/app-server or the explicit Codex CLI compatibility adapter. Do not relabel
Claude agents as Sol, Terra, or Luna.

## Hooks

Codex loads hooks from `hooks.json` or inline config. Useful engineering events include `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, and `Stop`.

The bundled setup uses:

- `SubagentStart` to inject repository-safety and evidence requirements into the six bundled agent types.
- `PreToolUse` to deny a small set of destructive Git commands and force pushes.

Do not install a default `Stop` continuation hook. A generic auto-continue hook can create expensive loops and cannot decide whether new authority is required. Native goal state or the skill's explicit goal ledger is the safer persistence mechanism.

`SubagentStart` can add developer context, but official Codex documentation states that
`continue: false` does not stop the child from starting. It cannot enforce latest-only routing.
`SubagentStop` can request a focused continuation and exposes the child transcript path, but the
transcript format is not stable; do not install a generic auto-continue loop. `PreCompact` and
`PostCompact` can observe compaction, but should not dump prior history back into the prompt.

Command hooks can deny supported intercepted calls, but `PreToolUse` coverage is incomplete and is
not a complete enforcement boundary. Hooks supplement sandboxing, permissions, repository
instructions, runtime route attestation, review, and human authority; they do not replace them.

Live parent sandbox and approval overrides, including interactive permission changes and `--yolo`,
are reapplied when Codex spawns a child. They can override a custom agent's sandbox default. Record
effective permissions before delegation. Keep an unprovable read-only lane in the parent or use a
separately sandboxed SDK/app-server thread; use the CLI compatibility adapter only when that surface
is unavailable.

## Prompt and context efficiency

GPT-5.6 guidance recommends lean prompts: state each rule once, expose only relevant tools, and
measure context as a session grows. Keep stable outcome, authority, and acceptance criteria with the
lead; send children only a compact delta packet. Put raw logs and matrices in evidence artifacts,
not handoff prose. Use persisted reasoning across turns only while goals and assumptions remain
stable; start a fresh stage or use current-turn context when earlier reasoning is irrelevant.

Programmatic Tool Calling belongs to the Responses API, not the local Codex subagent contract. Use
it only in an API-backed bounded stage for deterministic filtering, joining, deduplication,
aggregation, or validation. Its generated JavaScript has no direct Node, filesystem, network,
subprocess, package, or persistent-state access, but it can invoke eligible tools such as patch or
shell surfaces. Exclude mutation tools from unapproved stages. Define eligible tools, output schema,
concurrency, retry, and stop limits. Keep
direct calls when each result changes engineering judgment, approval is involved, or citations and
native artifacts must survive.

Responses Multi-agent beta lets one GPT-5.6 request coordinate independent hosted subagents. Its
current documentation does not establish heterogeneous child model/tool control or filesystem
isolation, so it cannot prove mixed Sol/Terra/Luna Codex routing.
Use the Codex SDK for coding-focused threads. When Codex is one specialist in a broader application,
expose Codex CLI as MCP and use an Agents SDK manager that retains final ownership. Native traces,
rollouts, and SDK state aid resume and observability; retain application-owned authorization,
idempotency, worktree, test, and release receipts.

## Official sources

- GPT-5.6 model and prompt guidance: https://developers.openai.com/api/docs/guides/latest-model
- Sol model: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- Terra model: https://developers.openai.com/api/docs/models/gpt-5.6-terra
- Luna model: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- Codex subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex SDK: https://learn.chatgpt.com/docs/codex-sdk
- Codex app-server: https://learn.chatgpt.com/docs/app-server
- Codex hooks: https://learn.chatgpt.com/docs/hooks
- Codex configuration reference: https://learn.chatgpt.com/docs/config-file/config-reference
- Codex customization: https://learn.chatgpt.com/docs/customization/overview
- Responses Multi-agent: https://developers.openai.com/api/docs/guides/responses-multi-agent
- Agents SDK orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- Programmatic Tool Calling: https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code model configuration: https://code.claude.com/docs/en/model-config
