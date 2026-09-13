# Runtime integrations and release checks

Capability review: September 13, 2026. Tested versions belong in release evidence, not a permanent
minimum-version promise. Read only rows relevant to the selected surface. A portable skill cannot
enable a runtime feature by describing it.

## Capability matrix

| Feature | Owner / version evidence | Current use | Expected benefit | Overhead | Limits | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| SKILL.md and progressive disclosure | Agent Skills current specification | Core and optional references | Cheap discovery; task-specific context | Description always discoverable; body on activation | Does not register agents/hooks or resolve dependencies | Adopt; compact core |
| Targeted install/update, temporary use | Vercel Skills CLI 1.5.26 validated | Portable distribution | Avoid blanket reinstalls; disposable canary | CLI/network and isolated setup | Installation telemetry is not usage/outcome telemetry | Adopt named skills and versioned evaluation |
| Native model/effort selection | Codex live schema; local CLI 0.153.4 inspected | Primary engineering route | No extra controller/process loop | Child context and synthesis | Profiles/defaults may override; account availability varies | Adopt explicit same/mixed route |
| Optional pinned agent profiles | Codex .toml; 0.153.4 inspection | Bundled/installed presets | Convenient roles | Catalog entries; maintenance | Installed is not necessarily loaded or effective | Retain optional; direct selectors suffice |
| SubagentStart context | Codex released hooks docs | Project opt-in handler | Compact role/ownership reminder | One short process per matching start | Parent session/model is not child attestation; trust required | Retain bounded, narrow, synchronous |
| Destructive command guard | Codex PreToolUse | Project opt-in handler | Extra accidental-command warning | Matching shell call latency | Not a complete security boundary; cannot grant authority | Retain synchronous; permissions remain authoritative |
| Model signal normalization | Codex hook extension | Optional pure helper, not a new global hook | Prevent parent/child misattribution | Small JSON parse | Caller must obtain authentic event; fields can be unavailable | Adopt whitelist, no persistence |
| Startup/compaction restoration | Codex SessionStart/PostCompact; runtime-specific | Manual journal resume/native context | Recover open requirements | Potential context injection and stale state | Needs explicit run binding and trust | Defer automatic hook; use bounded explicit resume |
| Tool outcomes/resource recorder | Codex PostToolUse/Interrupt | Native telemetry plus explicit owned handles | Better causal timing/cleanup | Per-tool hook load and sensitive outputs | Hosted tools differ; async completion may arrive later | Defer generic hook until missing evidence justifies it |
| Stop/reconciliation hooks | Codex/Claude distinct payloads | Explicit journal close | Honest completion | Continuation can consume usage | Hook cannot determine all acceptance/authority | Reject generic auto-continue; keep explicit gates |
| Native context notes/history | Eligible Astra Codex session; experiment off by default | Feature-detected only | Search prior context rather than replay | State/tool calls | Account/client/sign-in restrictions; not arbitrary cross-project memory | Prefer when available; never auto-enable |
| Claude skills and agent profiles | Claude Code 2.1.247 inspected; current docs may describe newer releases | Shared skill folder, separate native profiles | Portable engineering in Claude | Provider-specific maintenance | GPT model IDs do not select Claude models; precedence differs | Retain, test separately |
| Claude forced subagent model | Docs require 2.1.257+ for FORCE | Not enabled by this skill | Uniform routing when explicitly required | Removes role flexibility | Local 2.1.247 below documented FORCE version | Defer; do not claim env default is a force guarantee |
| Companion plugin | Codex/Claude packaging extensions | Not added | Could ship hooks/agents as a versioned bundle | Another catalog, activation and trust boundary | Skills CLI does not install plugin components; duplicate hooks can all run | Defer: optional bootstrap covers current need |
| Codex SDK / app-server | Current official TS Node18+, Python3.10+ stable SDK | Recommended for application controllers | Managed local thread lifecycle/streaming | App runtime and ownership | Does not automatically replace candidate isolation, locks or acceptance | Prefer for new controllers; no unnecessary rewrite |
| Agents API / Responses Multi-agent / Agents SDK | Distinct current API surfaces, beta where documented | Documented application options, not enabled integrations | Managed or app-owned orchestration | Billable app sessions, tool execution, operations | Different tool inheritance, model selection, residency and concurrency | Defer adoption until an actual app requires it |

Potential benefit is a hypothesis until comparable outcomes are measured. Structural tests or
successful installation prove neither runtime invocation nor a performance improvement.

## Install just what is needed

Portable core for both clients:

```bash
bunx skills@1.5.26 add SYMBaiEX/skills --skill gpt-engineer --agent codex claude-code --global --yes
bunx skills@1.5.26 update gpt-engineer --global --yes
```

Use `npx --yes skills@1.5.26` instead of `bunx` if Bun is unavailable. Named updates follow the
installation lock/source; verify the resulting version/hash. Add optional wrappers by exact name
only when wanted. A pack is a convenience selection, not a dependency resolver. For a disposable
canary, inspect `skills use --help` and use its temporary skill path in an isolated evaluation;
running an agent through it consumes real usage.

Codex native direct model selection needs no profile installation. Optional presets:

```bash
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --global --upgrade
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --global --check
```

Claude native profiles are separate: select `--provider claude` explicitly. Project setup targets a
Git root instead of `--global`. Inspect `bootstrap.py --help` for optional hook setup and lifecycle
operations. Setup never changes the parent model, custom catalog, or trust state. Preserve modified
files and symlinks; warnings are not proof that a customized profile matches the bundled route.

Project Codex hooks require explicit opt-in; ordinary profile upgrades do not re-enable them:

```bash
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py /path/to/repo --provider codex --with-hooks --upgrade
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py /path/to/repo --provider codex --with-hooks --diagnose
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py /path/to/repo --provider codex --disable
python3.11 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py /path/to/repo --provider codex --uninstall
```

Bootstrap lifecycle locking targets macOS/Linux. Diagnostics are read-only. Global installs contain
profiles only; hook disable applies to project registrations, not a global off switch. Re-running
`--with-hooks` explicitly requests registration again. Malformed hook configuration blocks uninstall
before deleting assets; repair/review it first. No hook files or trust state are installed in Claude
by this core bootstrap; the separate Claude Multi-Agent package has its own lifecycle.
Remove core Claude profiles with `bootstrap.py --provider claude --global --uninstall` (or
replace `--global` with the project path). Customized profiles and Claude settings/hooks remain.

After profile changes restart the relevant client or start a fresh task as its catalog requires.
For Codex hooks, inspect `/hooks`, review the exact definitions and grant trust through the normal
UI. Updated definitions may need renewed trust. Never bypass trust to make a test pass.

## Hook acceptance contract

Inventory user/project/inline/plugin sources before enabling a handler: all matching Codex hooks can
run, not just the highest precedence file. An installer can deduplicate its own scope, not every
unknown plugin. Prefer project scope; do not register both a plugin and manual copy.

Handlers must bound input/output and runtime, validate payload shape, avoid reflecting untrusted
text, preserve missing fields, and be idempotent. Record latency and emitted bytes on fixtures.
Concurrent state writers need locking and atomic updates; stateless context hooks avoid that cost.
Blocking guards remain synchronous. Async hooks cannot replace safety/completion gates and require
their own lifecycle, deduplication and cancellation. No full transcripts or tests-after-every-edit.

Report separately: packaged, installed, registered, enabled, trusted, invoked by runtime, and measured
beneficial. Directly executing a hook with a fixture proves handler behavior only. A pending trust
review means runtime execution is not verified. Do not fabricate observed events or modify trust hashes.

Disable/remove only managed registrations. Uninstall only unchanged managed files; retain customized
or unrecognized content with a warning. Do not broadly disable other hooks or uninstall shared tools.
The portable skill can be removed separately with `skills remove gpt-engineer --global --yes`;
that does not remove separately bootstrapped profiles/hooks.

## Release evidence and evaluation

In isolated homes/repositories verify clean install, upgrade, duplicate handling, custom/symlink
preservation, discovery, route selection, failure behavior and disable/uninstall. Test core decisions
in fresh contexts: small fix, substantive build/design, parallel research, unavailable models,
session switch, resume after drift, dirty/shared work, hook failure and resource cleanup. Include
activation and non-activation. Compare previous/revised/no-skill on identical task contracts when
useful. Give evaluators raw artifacts, not the desired answer.

Predeclare cases, model/effort, concurrency and usage/time budget. Separate scripted invariants,
model decision exercises, actual implementation, trusted runtime-hook execution and production proof.
Record outcomes, regressions, rework, elapsed time, tokens, coordination, hook overhead, interventions
and missing metrics. One sample is not a causal performance claim. Keep raw traces local; export
sanitized findings only. Track recommendation IDs to changed files, tests and release commits.

## Primary references

- [Skills CLI](https://github.com/vercel-labs/skills#readme) and [skills.sh](https://skills.sh)
- [Agent Skills specification](https://agentskills.io/specification)
- [Codex skills](https://learn.chatgpt.com/docs/skills), [hooks](https://learn.chatgpt.com/docs/hooks), [models](https://learn.chatgpt.com/docs/models), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins) and [SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [Claude skills](https://code.claude.com/docs/en/skills), [hooks](https://code.claude.com/docs/en/hooks), [subagents](https://code.claude.com/docs/en/sub-agents), [plugins](https://code.claude.com/docs/en/plugins-reference), [plugin evals](https://code.claude.com/docs/en/plugin-evals)
