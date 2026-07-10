# Codex and GPT-5.6 routing

Use this reference when selecting models, defining Codex custom agents, or deciding whether hooks or deeper orchestration are appropriate. Recheck the linked official documentation when current availability or configuration syntax matters.

## Model roles

- **Sol:** `gpt-5.6` routes to `gpt-5.6-sol`. Use it for frontier capability, ambiguous multi-step engineering, architecture, difficult debugging, integration, and final judgment.
- **Terra:** `gpt-5.6-terra` balances intelligence and cost. Codex specifically recommends it for exploration, read-heavy scans, large-file review, and supporting-document work. It is also suitable for bounded routine implementation.
- **Luna:** `gpt-5.6-luna` targets cost-sensitive, high-volume workloads. Using it for mechanical verification, test matrices, residual searches, and structured evidence collection is an orchestration inference from that documented positioning; keep semantic acceptance and high-risk decisions with Sol or the orchestrator.

GPT-5.6 supports `none`, `low`, `medium`, `high`, `xhigh`, and `max` in the API. Codex custom-agent configuration support can lag API capabilities, so the bundled profiles use `medium` or `high`. Do not write `max` into a Codex agent file unless the installed Codex schema confirms it.

## Codex custom agents

Current Codex releases load project agents from `.codex/agents/*.toml`. Required fields are `name`, `description`, and `developer_instructions`; model, reasoning effort, sandbox, MCP servers, and skill config are optional overrides.

Codex defaults to six concurrent agent threads and a maximum spawn depth of one. Keep depth one by default. More nesting increases tokens, latency, local resource use, and the chance of repeated fan-out.

Subagents are enabled in current Codex releases and can be requested directly or by applicable `AGENTS.md` or skill instructions. ChatGPT Work can also run parallel hosted subagent workflows where available.

## Hooks

Codex loads hooks from `hooks.json` or inline config. Useful engineering events include `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, and `Stop`.

The bundled setup uses:

- `SubagentStart` to inject repository-safety and evidence requirements into the four bundled agent types.
- `PreToolUse` to deny a small set of destructive Git commands and force pushes.

Do not install a default `Stop` continuation hook. A generic auto-continue hook can create expensive loops and cannot decide whether new authority is required. Native goal state or the skill's explicit goal ledger is the safer persistence mechanism.

`PreToolUse` interception is incomplete and is not a complete enforcement boundary. Hooks supplement sandboxing, permissions, repository instructions, review, and human authority; they do not replace them.

## Official sources

- GPT-5.6 model guidance: https://developers.openai.com/api/docs/guides/latest-model
- Sol model: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- Terra model: https://developers.openai.com/api/docs/models/gpt-5.6-terra
- Luna model: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- Codex subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex hooks: https://learn.chatgpt.com/docs/hooks
- Codex customization: https://learn.chatgpt.com/docs/customization/overview
