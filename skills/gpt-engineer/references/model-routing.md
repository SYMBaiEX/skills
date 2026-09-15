# Model-aware routing

Reviewed against official documentation September 13, 2026. The supported GPT contract is exactly
`gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`. Preserve the selected parent;
neither a model upgrade nor a fleet is implicit. Claude and explicitly requested Spark are separate
runtime/model workflows, not fallback members of this contract.

## Select from evidence

The current runtime schema and current session/turn metadata govern what can be requested. A saved
`model` setting, model catalog entry, profile, prior turn, or self-description does not prove current
execution. After a session switch or resumption, refresh relevant metadata rather than carrying an
old route forward. Record unavailable fields without guessing.

Codex hooks document a `model` extension. At parent-scoped events it is a useful runtime signal for
the current parent. `SubagentStart`/`SubagentStop` use the parent `session_id`; their common `model`
field is not independent child-model attestation. Keep `agent_id` separate. Child evidence needs
that child's runtime metadata, correctly attributed turn, or an attested execution response.
Claude's payloads differ; do not assume Codex extensions exist there.

For each route retain requested/effective model, effort and tier; subject/parent/child identity;
evidence source; policy; and profile hash if used. Missing effective evidence does not invalidate
an otherwise supported requested route unless the task requires attestation. Observed mismatch does.
Never use a model-echo prompt as a routing test.

The engineering-model contract does not apply to runtime-owned approval reviewers. For example,
`codex-auto-review` with a native Guardian source is an approval service, not a worker routed to an
unexpected coding model. Classify it separately from parent and delegated engineering work. A name
alone is not provenance: keep unknown sources unknown. Do not disable the reviewer, modify its model,
or loosen permissions to satisfy a routing audit. See [approval reviews](runtime-integrations.md#approval-reviews).

## Same-model and mixed-model policies

- **Same-model (default):** request the observed supported parent model explicitly for useful
  children. Include an appropriate supported child effort rather than inheriting an unintended
  global default. If parent identity is unknown, continue direct work; do not silently guess a child.
- **Mixed-model:** select an exact child model for a bounded contract, with the reason and budget.
  The user can select this policy, or approve an explicit proposed policy where it changes cost or
  capability materially. It is not automatic failure recovery. The selected parent remains the lead.
- **Unavailable:** do not edit catalogs, bypass review, retry a denied route under another model,
  or switch the parent. Continue independent suitable work, then report the missing capability.
  Escalation changes only the affected lane and needs authority for any material scope/cost change.

Use native direct `model` and `reasoning_effort` selectors when exposed. Give bounded role
instructions in the task packet. A custom profile can override spawn/default/parent settings;
inspect it and project shadows before relying on its name. A model-less profile is deliberate
inheritance only if the resolved runtime policy supports the intended route, not proof by itself.
The optional `scripts/select_route.py` validates a machine-readable route request without launching
a model. Profile audits are diagnostics for users of bundled profiles, not a gate for direct work.

## Adapt the task, not a stereotype

| Selected model | Official guidance informs this starting hypothesis | Calibrate from outcomes |
| --- | --- | --- |
| Astra | Strong end-to-end reasoning; sensitive to skill instructions; may over-test or under-delegate | Give outcome/constraints; remove conflicting process rules; use proportional checks and useful independent review |
| Sol | Complex, open-ended work and polish | Define done and research boundaries; keep coupled decisions coherent; delegate clear supporting evidence |
| Terra | Everyday reasoning/tool work | Use a bounded feature or investigation with clear interfaces; expand scope only after accepted results |
| Luna | Clear, repeatable/high-volume work | Give specific scope, output schema/examples when helpful, deterministic checks, and a stop condition; split ambiguity by decision boundary |

These are prompting starting points, not claims that a model cannot do architecture or must delegate.
Any supported parent can own design, implementation and final acceptance. Review consequential work
independently when warranted. Do not prescribe fleet size from price or marketing descriptions.

Preserve the selected parent's effort. For child tasks, use the lowest supported effort that meets
acceptance; medium is a starting experiment, not a universal floor. Raise effort or split an
oversized lane only for demonstrated reasoning difficulty; tool waits are not solved by more effort.
Keep supported effort values runtime-specific. Astra does not support none/minimal. Max and Ultra
are distinct controls: official Codex guidance describes Ultra as subagent-enabled, so budget its
actual topology rather than treating it as merely more single-agent reasoning. Service tier is
independent; never silently enable Fast.

## Bundled and legacy adapters

Bundled Astra/Terra/Luna profiles remain optional presets with exact model/effort pins. They do not
dictate the parent. Existing Sol profiles are supported when their resolved route is verified; the
v2.0 Astra-only restriction was a skill policy, not OpenAI model retirement. Historical audit cohorts
must retain their original policy/version, not be rewritten to the current policy.

The guarded CLI adapter is for documented headless/isolation gaps. Its candidate filesystem, allow
paths, locks, process groups, handoff validation and cleanup are real guarantees; a new SDK alone
does not replace them. See [Codex adapter details](codex-astra.md). New controllers should prefer
official SDK/app-server surfaces after checking those guarantees and [runtime boundaries](dynamic-workflows.md).

## Primary sources

- [Codex models and reasoning](https://learn.chatgpt.com/docs/models)
- [Subagent model resolution and custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Hook fields and event semantics](https://learn.chatgpt.com/docs/hooks)
- [Astra prompting and API restrictions](https://developers.openai.com/api/docs/guides/latest-model)
