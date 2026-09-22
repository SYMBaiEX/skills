# Model-aware routing

Reviewed against the official Codex model and subagent documentation on September 22, 2026.
This skill's routing rule is intentionally stricter than the platform: GPT-6 Astra is allowed only
as the active parent/orchestrator (the current chat model), never as a GPT Engineer child. GPT-6
Sol and GPT-6 Luna are the only current child routes. This is a GPT Engineer policy, not an OpenAI
runtime restriction.

## Preserve the active parent

Use current session or turn metadata and the runtime's exposed model selectors. A saved default,
profile, prior turn, model catalog, or model self-description does not prove the current route.
Keep requested and effective model, effort, and service tier separate, with subject identity and
evidence source. If runtime evidence is unavailable, say so; never guess or silently change the
parent.

| Active parent | Default child policy | Allowed GPT Engineer child models |
| --- | --- | --- |
| GPT-6 Astra | Explicit mixed-model only | GPT-6 Sol or GPT-6 Luna; never Astra |
| GPT-6 Sol | Same-model when delegation helps | GPT-6 Sol; GPT-6 Luna only as a deliberate mixed route |
| GPT-6 Luna | Same-model when delegation helps | GPT-6 Luna; GPT-6 Sol only as a deliberate mixed route |
| GPT-5.6 Sol/Terra/Luna during rollout | Preserve parent; same-model is unavailable under this child contract | GPT-6 Sol or GPT-6 Luna only with an explicit mixed-model decision |
| Unknown or unsupported parent | Parent-only until the active route is known | Do not guess a child route |

When Astra is the parent, select Sol for ambiguous, demanding, multi-step engineering lanes and
Luna for focused, repeatable lanes. Under a Sol or Luna parent, same-model is the default unless
the lane has a clear reason for cross-routing. Do not dispatch either model merely to fill fleet
capacity. The parent remains responsible for architecture, integration, user communication, and
final acceptance.

OpenAI's Codex guidance recommends Sol for complex coding and agentic workflows and Luna for
focused, repeatable tasks. These are starting points, not capability ceilings: shape lanes from the
actual acceptance contract and runtime evidence. Start with medium effort for Sol and high for Luna
when the runtime supports those controls; tune effort from observed outcomes. Higher effort can
increase time and token use. Fast/service tiers are independent controls and are never enabled by
this skill.

The official Codex subagent behavior inherits the parent model and effort unless a child route is
specified. Therefore, when Astra leads, always specify a Sol or Luna model explicitly. Likewise,
use exact child model and effort selectors when relying on named profiles, and inspect project-level
shadow profiles before trusting a profile name. Never install or request an Astra worker profile.

GPT-5.6 parents may remain available during the GPT-6 rollout. Preserve a user's already-selected
GPT-5.6 parent, but do not create new GPT-5.6 child routes. Since GPT-5.6 is not in this skill's
child allowlist, delegation from such a parent is explicitly mixed-model and must select GPT-6 Sol
or Luna. Do not edit `models_cache.json`, `model_catalog_json`, permissions, or account-wide model
settings to make a route appear available. If Sol/Luna selection is unavailable, continue suitable
work directly under the active parent and report the limitation.

## Evidence boundaries

Codex parent-scoped hook events can identify the parent model. `SubagentStart` and `SubagentStop`
common model fields may still describe the parent and are not independent child attestation. Keep
`agent_id`/subject identity separate; attest a child only from correctly attributed child runtime
metadata, a child turn, or an execution response. Claude event payloads and model resolution are
provider-specific; this GPT routing rule does not configure Claude Code.

Runtime-owned approval reviewers (including `codex-auto-review`) are not GPT Engineer worker lanes.
Identify their runtime provenance before attributing usage or review behavior to this skill. Do not
disable them, change their model, or weaken permissions to satisfy a GPT Engineer route audit.

## Primary sources

- [Codex models](https://learn.chatgpt.com/docs/models)
- [Codex subagents and model resolution](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex hooks and event fields](https://learn.chatgpt.com/docs/hooks)
- [GPT-6 Sol model](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [GPT-6 Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [Introducing GPT-6 Sol and Luna](https://openai.com/index/introducing-gpt-6-sol-and-luna/)
