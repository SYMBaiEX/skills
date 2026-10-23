# Model-aware routing

Reviewed October 23, 2026 against current official OpenAI documentation. Current child models are
`gpt-6.1-sol` and `gpt-6-luna`. GPT-6 Sol child routes and presets are retired. Historical identifiers
remain only for interpreting old records and safely retiring known installations. Astra is allowed
only as the selected parent/orchestrator; this is GPT Engineer policy, not a platform restriction.

## Selection and effort

| Selected parent | Default child policy | Current child models |
| --- | --- | --- |
| GPT-6.1 Sol | Same-model when useful | 6.1 Sol; Luna with an explicit mixed-model decision |
| GPT-6 Luna | Same-model when useful | Luna; 6.1 Sol with an explicit mixed-model decision |
| Astra or an already-selected older parent | Preserve parent; explicit mixed-model selection | 6.1 Sol or Luna |
| Unknown parent | Parent-only until route is known | Do not guess same-model equality |

Use 6.1 Sol for ambiguous, multi-step reasoning and implementation; Luna for focused, repeatable
work. This is task shaping, not a capability ceiling. Profiles start at medium effort for Sol
(high for verification), and high for Luna. Preserve selected parent effort; tune child effort
from acceptance evidence rather than assigning maximum effort to every lane.

The **6.1 Sol API** accepts `low`, `medium` (default), `high`, `xhigh`, and `max`; it rejects
`none` and `minimal`. Tool calling requires Responses; Chat Completions is supported without tools.
With reasoning enabled remove unsupported sampling/logprob parameters as documented. Codex clients
can expose additional controls, including `ultra`; use only efforts the live client and model support.
Do not translate Codex Ultra into an undocumented API effort. The CLI adapter intentionally accepts
its documented effort subset; direct native tools follow their live schema.

Fast and Ultrafast are separate, billable service choices. The skill never enables them or changes
account-wide defaults. 6.1 Sol Ultrafast is documented at 6x Standard API rates; speed claims require
comparable accepted tasks, and account/client availability must be checked.

## Native Codex precedence

Resolve a setting from explicit spawn values, then `[agents]` defaults, then the parent. An explicit
or default model selection without an effort selects that model's default effort. A named custom
agent file then takes precedence for fields it sets: **its model and effort can override spawn values**.
A file setting only `model` preserves the previously resolved effort. Bundle profiles therefore set
both model and effort. Project profiles and custom agents shadowing built-in names need inspection.

For an exact route, choose a matching profile or use an unconfigured native role with explicit
selectors. Do not assume a direct selector overrides a named preset. Full-history forks do not
accept model overrides; use a fresh packet for explicit mixed-model lanes.

Custom agents inherit parent permissions, provider, MCP servers, and root service-tier preference.
A read-only role's instructions do not create a read-only sandbox; enforce isolation through the
owning runtime when needed. Profile `sandbox_mode`, `approval_policy`, provider, or MCP settings
cannot replace the parent's settings. The separate CLI adapter does select its own execution sandbox.

## Runtime evidence

Use current session/turn metadata with subject identity. Saved configuration, model availability
catalogs, self-description, and a profile name are not active-route evidence. Record requested and
observed model/effort/tier separately; missing observed fields remain unavailable. `SubagentStart`
and `SubagentStop` common model fields can describe the parent and cannot independently attest a
child. An actual mismatch stops the affected lane.

Runtime-owned approval reviewers such as `codex-auto-review` are not GPT Engineer delegates.
Specialist agent names alone also do not establish skill attribution. Identify loaded instructions,
dispatch identity, and source before assigning a run or its usage to this skill.

Never edit model catalogs, trust, or permissions to obtain a route. If a current child is unavailable,
continue suitable work in the selected parent and report the limitation. Never silently fall back
to retired GPT-6 Sol or older children. Claude native routing remains provider-specific.

## Primary sources

- [GPT-6.1 Sol model and API efforts](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [GPT-6 guidance and migration](https://developers.openai.com/api/docs/guides/latest-model)
- [Codex models](https://learn.chatgpt.com/docs/models)
- [Codex subagents and exact precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex hooks and event fields](https://learn.chatgpt.com/docs/hooks)
- [Ultrafast mode](https://developers.openai.com/api/docs/guides/ultrafast-mode)
