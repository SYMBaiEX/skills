# Codex-Spark routing reference

Use this reference when deciding whether and how to route a Spark fleet.

## Current official contract

- Exact model identifier: `gpt-5.3-codex-spark`.
- Availability: research preview for ChatGPT Pro subscribers in supported Codex clients.
- Interface: Codex with ChatGPT sign-in; do not present Spark as a generally available API model.
- Shape: text-only, 128k context, smaller and less capable than broader Codex models.
- Performance: OpenAI reports more than 1,000 tokens per second, but do not promise a measured rate for a particular run.
- Limits: Spark has separate, demand-sensitive usage limits. No fixed public fleet quota exists.
- Custom agents: set `model = "gpt-5.3-codex-spark"` in a user-level or project-level Codex agent TOML.
- Codex defaults: `agents.max_threads` defaults to 6 and `agents.max_depth` to 1. Respect the actual runtime capacity.

Official sources:

- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/agent-configuration/speed#codex-spark
- https://learn.chatgpt.com/docs/changelog#codex-2026-02-12
- https://learn.chatgpt.com/docs/pricing#what-are-the-usage-limits-for-my-plan

## Routing language

Distinguish these facts:

- `requestedModel`: the exact profile or CLI argument requested Spark.
- `serverAcceptedRequest`: an explicitly pinned turn completed successfully.
- `modelAttestedByRuntime`: populate only when returned runtime metadata identifies the executing model.

Do not call a profile file, role name, nickname, or prompt wording execution proof.

## Work selection

Prefer Spark for bounded searches, routine transformations, focused fixes, narrow tests, and independent diff inspection. Keep ambiguous planning, system-wide changes, sensitive security work, conflicting findings, integration, and final acceptance with the capable parent.

Ask for tests explicitly. A fast child should not infer that testing is optional.

The guarded CLI writer edits an isolated candidate copy and emits a change bundle. It does not mutate
or automatically restore the original checkout. Review and integrate that bundle in the main agent,
then verify the real integrated repository.
