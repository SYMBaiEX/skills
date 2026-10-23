# GPT Engineer 2.3.0

October 23, 2026. Source package: `SYMBaiEX/skills`.

## Current routes and upgrade

GPT-6.1 Sol replaces GPT-6 Sol for demanding children. Current profiles are
`gpt61-sol-{engineer,explorer,worker,verifier}` and `gpt6-luna-{explorer,worker,verifier}`.
Current suite selectors are `all`, `sol61`, and `luna` (the adapter uses the latter two).
The old `sol` suite and `gpt6-sol-*` child profiles are retired; migrate callers explicitly.
Astra remains parent-only by skill policy. The selected parent is never changed automatically.

The optional bootstrap backs up and removes exact managed old Sol presets on `--upgrade`, using
receipts or exact known bundled hashes. Customized or unknown retired profiles remain on disk for
review and fail the route audit; preservation does not authorize selecting them. Historical trace
classification retains old identities without keeping active old-model routes. The fleet audit uses
`--dispatch-suite gpt61` for this release; `gpt6` remains a historical 2.2 assertion, not an active route. Installation of the
portable skill and optional preset upgrade remain separate operations.

## Leaner engineering contract

The entrypoint is shorter and routes conditional setup, scheduling, and telemetry detail to focused
references. It keeps explicit delegation for useful independent work, acceptance and authority,
concurrent-work preservation, proportionate verification, and interruption recovery. Narrow searches,
filtered tool results, delta handoffs, existing process handles, and backoff on unchanged polling
reduce avoidable context and control-loop work. No fixed fleet size or maximum effort is imposed.

## Current OpenAI contracts

- Named custom-agent model/effort values override explicit spawn values. Native profiles inherit
  parent permissions and root tier preference; a role instruction is not a separate sandbox.
- 6.1 Sol API efforts are low/medium/high/xhigh/max. Codex Ultra is a client/model control,
  not an API effort to copy blindly. Tool calls use Responses; Luna retains its own none support.
- GPT-6-family reasoning updates, async tools, and Responses Multi-agent are controller capabilities
  with distinct compatibility constraints, not features enabled by installing a skill.
- Prompt caching now offers 12h retention alongside the default 30m; longer retention changes write
  pricing. Useful stable prefixes and cache diagnostics matter more than byte minimization alone.
- Fast/Ultrafast remain explicitly chosen paid tiers. No paid tier, global configuration, model
  catalog, trust setting, or hosted controller is enabled by this release.

Primary sources: [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[model migration](https://developers.openai.com/api/docs/guides/latest-model),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), and the
[API changelog](https://developers.openai.com/api/docs/changelog).

## Trace-driven maintenance

`audit_traces.py` streams retained local rollout files and reads local SQLite stores without
modifying them. Its explicit activity window includes resumed older threads, suppresses copied
events, separates projected history from retained files, and exports aggregate diagnostics.
It does not export transcript text or session identifiers. Static nested-tool references, repeated
calls, skill-read matches, and output markers are candidates rather than execution or waste proof.
Coverage gaps and partial runtime counters remain explicit; they are not billing or outcome proof.
Keep private trace reports outside the public repository.

## Validation boundary

Regression coverage includes new routes, retired-child rejection, parent preservation, profile
agreement, safe upgrades and customized-file preservation, CLI/native effort boundaries, hook
matching, and aggregate-audit privacy/window/deduplication. Repository validation also treats
`agents/openai.yaml` as optional, consistent with the skill format, while checking invocation when
that metadata exists.

These checks establish package behavior. They do not establish production routing, trusted hook
invocation, or a causal latency/cost/quality gain. Compare representative accepted tasks against the
previous release before claiming such gains.
