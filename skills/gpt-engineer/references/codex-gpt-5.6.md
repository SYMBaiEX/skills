# Codex and GPT-5.6 routing

Use this reference when selecting models, defining Codex custom agents, or deciding whether hooks or deeper orchestration are appropriate. Recheck the linked official documentation when current availability or configuration syntax matters.

## Model roles

- **Sol:** use the explicit `gpt-5.6-sol` identifier for strict routing. The `gpt-5.6` family alias currently routes to Sol, but an alias is weaker evidence than an explicit target.
- **Terra:** `gpt-5.6-terra` balances intelligence and cost. Codex specifically recommends it for exploration, read-heavy scans, large-file review, and supporting-document work. It is also suitable for bounded routine implementation.
- **Luna:** `gpt-5.6-luna` is the fastest, lowest-cost family member for clear, repeatable, or high-volume work. Use it for deterministic transformations, narrow mechanical changes, test matrices, residual searches, and structured evidence collection. Keep ambiguous architecture, semantic acceptance, and high-risk decisions with Terra, Sol, or the orchestrator.

GPT-5.6 supports `none`, `low`, `medium`, `high`, `xhigh`, and `max` in the API. Current Codex surfaces also expose higher efforts when the selected model supports them. Use the lowest effort that passes representative checks: low for clear latency-sensitive work, medium as the normal baseline, and high or above only for measured hard cases. The bundled Luna worker uses low; the everyday Terra lanes and Luna verifier use medium; the Sol specialist uses high. The separate `luna_max_worker` pins Max plus the Fast service tier and is deliberately opt-in because both choices can increase usage.

## Codex custom agents

Current Codex releases load user agents from `~/.codex/agents/*.toml` and project agents from `.codex/agents/*.toml`. Required fields are `name`, `description`, and `developer_instructions`; model, reasoning effort, sandbox, MCP servers, and skill config are optional overrides.

`agents.max_concurrent_threads_per_session` caps spawned threads and excludes the primary thread. The live collaboration tool may instead report total active-agent capacity, so inspect the active contract rather than assuming a fixed number. Default GPT Engineer waves to at most three active children and depth one. More agents and nesting increase tokens, latency, local resource use, and repeated fan-out risk.

Subagents are enabled in current Codex releases and can be requested directly or by applicable `AGENTS.md` or skill instructions. Each child performs independent model and tool work, so a fleet consumes more usage than a comparable single-agent run. ChatGPT Work can also run parallel hosted subagent workflows where available.

Agent files are configuration, not proof of selection. Record the effective profile source, `name`, exact model, effort, and file hash. A project-scoped profile with the same `name` can shadow a user profile. When a custom file specifies model or effort, that value wins; otherwise Codex resolves explicit spawn value, the corresponding `[agents]` default, then the parent value. If a spawn changes only the model, that model's default effort applies.

Inspect the current spawn tool for an agent-type or model selector. When that selector is unavailable, use the bundled `run_codex_agent.py` wrapper to pin `codex exec --model`. In latest-only mode, never use a generic or inherited child as a fallback. Use `scripts/audit_routing.py` to fail closed on missing or conflicting Sol, Terra, or Luna profiles.

## Strict and fast routing

The default GPT Engineer route allows only `gpt-5.6-sol`, `gpt-5.6-terra`, and
`gpt-5.6-luna`. Spark and Claude remain explicit opt-in surfaces because they are not members of
the GPT-5.6 family. If exact routing cannot be proven, keep the work with an exact-model parent or
report the blocker.

Use medium reasoning as the normal baseline, low for clear latency-sensitive work
when validation still passes, and high only for hard judgment. Do not raise reasoning automatically.
Codex Fast mode can speed supported GPT-5.6 models at higher credit use; it is a user/runtime choice,
not a model substitution.

## Temporary Luna Multi-Agent V2 compatibility

As of Codex CLI 0.144.6, the shipped catalog can mark Sol and Terra as Multi-Agent V2 while marking
Luna as V1. The V2 spawn path filters requested models by that version, so a Sol/Terra parent can
reject Luna before execution. This is a real catalog compatibility defect, but it is not a stable
public configuration contract and should not be hidden inside normal bootstrap.

Use `scripts/configure_luna_v2.py` only after it validates that exact mismatch. The script derives a
managed catalog from the current `~/.codex/models_cache.json`, changes only Luna's
`multi_agent_version` to `v2`, and points the supported top-level `model_catalog_json` setting at the
copy. It can also enable `features.fast_mode`; the `luna_max_worker` profile independently pins
`service_tier = "fast"`. Native spawns should select `agent_type="luna_max_worker"` with
`fork_turns="none"` so neither model nor history is inherited from the Sol orchestrator.

This workaround has operational costs:

- Codex snapshots custom catalog content at process startup, so every apply, refresh, or disable
  requires a full restart.
- A custom catalog freezes upstream metadata until the managed copy is refreshed. Re-run `--apply`
  after Codex updates, then restart again.
- Desktop and app-server catalog behavior has had active bugs. Keep the CLI runner as the fail-closed
  fallback and verify the exact route in a fresh process.
- Fast mode is documented as faster with increased usage. Do not infer that Luna Max/Fast is cheaper
  than Terra standard without current account-level measurements.

When the stock Luna entry becomes V2, run `python3 scripts/configure_luna_v2.py --disable`, restart,
and return to the upstream catalog.

Primary references: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Codex configuration](https://developers.openai.com/codex/config-reference),
[Luna V1/V2 mismatch report](https://github.com/openai/codex/issues/34301),
[custom catalog startup caching](https://github.com/openai/codex/issues/35129), and
[Multi-Agent V2 routing limitations](https://github.com/openai/codex/issues/32705).

An optional default guard for model-less children is:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "medium"
```

This is not a latest-only enforcement boundary: an explicitly selected custom profile can still
override those defaults. The bootstrap intentionally does not rewrite user or project config.

## Claude Code agents

Claude Code loads user agents from `~/.claude/agents/*.md` and project agents from `.claude/agents/*.md`. The bundled lead, explorer, worker, and verifier profiles use the stable `opus`, `sonnet`, and `haiku` aliases. `CLAUDE_CODE_SUBAGENT_MODEL` overrides every per-agent model; surface that condition rather than claiming diversity.

Claude Code cannot natively run GPT-5.6 profiles. Cross-provider GPT delegation requires an installed, authenticated Codex CLI and the explicit Codex fallback. Do not relabel Claude agents as Sol, Terra, or Luna.

## Hooks

Codex loads hooks from `hooks.json` or inline config. Useful engineering events include `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, and `Stop`.

The bundled setup uses:

- `SubagentStart` to inject repository-safety and evidence requirements into the five bundled agent types.
- `PreToolUse` to deny a small set of destructive Git commands and force pushes.

Do not install a default `Stop` continuation hook. A generic auto-continue hook can create expensive loops and cannot decide whether new authority is required. Native goal state or the skill's explicit goal ledger is the safer persistence mechanism.

Current Codex command hooks are the enforceable hook path; prompt and agent hook handlers may be parsed but skipped. `PreToolUse` interception is incomplete and is not a complete enforcement boundary. Hooks supplement sandboxing, permissions, repository instructions, review, and human authority; they do not replace them.

Live parent sandbox and approval overrides, including interactive permission changes and `--yolo`,
are reapplied when Codex spawns a child. They can override a custom agent's sandbox default. Record
effective permissions before delegation; use the explicit runner or the parent when a native
read-only lane cannot remain read-only.

## Official sources

- GPT-5.6 model guidance: https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6
- GPT-5.6 prompt guidance: https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
- Sol model: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- Terra model: https://developers.openai.com/api/docs/models/gpt-5.6-terra
- Luna model: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- Codex subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex hooks: https://learn.chatgpt.com/docs/hooks
- Codex customization: https://learn.chatgpt.com/docs/customization/overview
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code model configuration: https://code.claude.com/docs/en/model-config
