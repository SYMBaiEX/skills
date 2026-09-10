# Astra engineering and Codex routing

Official guidance reviewed September 10, 2026. Read for routing, setup, model migration, or the CLI
adapter. The runtime's actual schema governs available controls; documentation examples can lag it.

## Model and effort policy

Use exact `gpt-6-astra` for the lead and default engineering roles. Preserve the selected parent's
effort; do not raise it simply because the model changed. The bundled `astra_engineer` uses high for
hard judgment; `astra_explorer`, `astra_worker`, and `astra_verifier` use medium. An explicit native
model/effort request can provide the same bounded task role without installed custom profiles.

API Astra supports low, medium, high, xhigh, and max. Codex may expose additional efforts such as
ultra; inspect its live schema. Astra rejects none/minimal. Pro mode and Fast processing are separate
choices, neither enabled by the bundled Astra profiles. Do not infer task cost from per-token price:
measure accepted output, input/cache-write/cache-read/output usage, retries, and elapsed time.

The optional economy suite retains these exact task roles:

| Profile | Model | Effort | Use |
| --- | --- | --- | --- |
| `terra_explorer` | `gpt-5.6-terra` | medium | Bounded read-heavy investigation |
| `terra_worker` | `gpt-5.6-terra` | medium | Routine scoped implementation |
| `luna_worker` | `gpt-5.6-luna` | low | Clear mechanical changes |
| `luna_verifier` | `gpt-5.6-luna` | medium | Deterministic checks and evidence collection |
| `luna_max_worker` | `gpt-5.6-luna` | max, Fast | Separately selected or measured latency option |

Economy requires explicit selection; it is not automatic recovery from an unavailable Astra route.
Astra retains integration and acceptance judgment. Sol and the old `gpt-engineer-*` Codex profiles
remain historical audit identities. Claude's similarly named provider profiles are a separate
explicit workflow, and Spark retains its separate skill.

## Profile and route evidence

Codex loads user `~/.codex/agents/*.toml` and project `.codex/agents/*.toml` profiles. Required fields
are name, description, and developer_instructions. Pin model and reasoning effort together. An
agent file's configured values override the resolved spawn/default/parent values; setting only a
model does not reliably reset an inherited effort. Check project shadowing and the live tool schema.

Use native children with compact role instructions. Inspect the actual sandbox and approvals:
parent permission overrides may supersede a profile's read-only default. If a lane requires enforced
isolation, use a separately sandboxed thread or candidate runner when native isolation is inadequate.

Profile preflight proves configured/requested routing. Runtime metadata can additionally establish
observed execution. Record unavailable effective fields as unavailable. Do not substitute an echoed
model name or reject useful native execution merely because the host omits attestation. Explicit
attestation requirements and observed route mismatches still stop the affected lane.

For installed profiles, use Python 3.11+ (or a Python environment with `tomli`) for complete TOML
parsing in the routing audit. Native engineering itself does not require Python:

```bash
python3 scripts/audit_routing.py --cwd /path/to/repo --runtime --parent-model gpt-6-astra --json
```

Use `--suite economy` only for that selected policy. Check local configuration before the first
useful stage, then recheck when relevant inputs change. Do not repeatedly pay for synthetic routing
tests. Model catalogs describe availability; they do not prove account access or actual execution.

## Install and migrate

Skills.sh installs the skill; profile registration is a separate operation:

```bash
bunx skills add SYMBaiEX/skills --skill gpt-engineer --agent codex --global --yes
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --upgrade --global
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --check --global
```

Restart Codex and start a fresh task so its catalog sees installed profiles. A skill cannot switch
an active parent's model or change its live collaboration schema. Project-scoped installations can
shadow global ones; apply the same authorized migration to the relevant project path.

Bootstrap preserves unrelated files and provider settings, backs up known retired managed profiles,
and warns about customized retired profiles while preserving them. These unused legacy files do
not prevent Astra installation; review them separately if their removal is desired.
Project hook upgrades update the managed matcher and scripts while preserving unrelated hooks.
Global installation adds no hooks. Claude profiles are installed only when explicitly selected.

## Context, hooks, and instruction design

Astra responds strongly to skills and AGENTS.md. Remove repeated process rules, automatic approval
pauses, unconditional audits, and tests that merely restate implementation. Use actionable acceptance
criteria and the user's continuing authority. Delegate only useful independent work and keep output
concise. Preserve source and check evidence without pasting full transcripts into every lane.

Codex's experimental `features.context_management.experimental_mode` supports notes and searchable
earlier context in eligible sessions. Feature-detect its runtime/tools and account support. It is
not universally available, especially in API-key/custom-provider or temporary structured sessions.
Use native history retrieval when present and retain the journal for operational facts; do not
install a competing full-transcript memory loop or change global configuration during ordinary work.

Hooks supplement permissions and evidence. `SubagentStart` context does not attest routing and
`continue: false` there does not prevent a spawn. Keep the managed destructive-command guard scoped.
Do not add a generic Stop/SubagentStop auto-continue loop. Native completion, journal finalization,
and cleanup of task-owned handles are the completion path. Shared MCP processes are not child tasks.

## CLI compatibility adapter

Use only when native routing/isolation and the relevant official SDK path cannot satisfy the stage,
or when an explicitly selected headless/cross-provider workflow needs it:

```bash
python3 scripts/run_codex_agent.py \
  --role astra-explorer \
  --compatibility-reason native-routing-unavailable \
  --stage-id architecture-map --cwd /path/to/repo \
  --output-dir /tmp/gpt-engineer/architecture < /path/to/task-packet.txt
```

Writer roles need `--allow-writes` and owned repository-relative `--allow-path` entries. Explicit
dirty-path exceptions use `--allow-dirty-path`. The adapter uses a repository lock, bounded process
groups, a candidate copy, structured handoffs, and private journal state. It disables recursive
delegation and network access. It never integrates candidates automatically. Inspect result.json,
candidate.patch/changes, deletions, checks, and route evidence before integration. At most two
read-only adapters may run together; serialize candidate writers for the same repository.

The legacy [Luna compatibility note](codex-gpt-5.6.md) is relevant only to explicitly selected
economy work with an old runtime. It is never Astra setup.

## Sources

- [Astra introduction](https://openai.com/index/gpt-6-astra/)
- [Astra in professional work](https://openai.com/index/gpt-6-astra-next-generation-work/)
- [Astra prompting and migration](https://developers.openai.com/api/docs/guides/latest-model)
- [Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Codex changelog](https://learn.chatgpt.com/docs/changelog)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
