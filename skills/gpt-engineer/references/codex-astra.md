# Codex presets and compatibility adapter

The filename is retained for links from v2.0. Current model policy lives in
[model-routing.md](model-routing.md). GPT Engineer supports Astra, Sol, Terra and Luna parents;
the following optional presets do not override that choice.

Bundled profiles pin exact model/effort: Astra engineer high and explorer/worker/verifier medium;
Terra explorer/worker medium; Luna worker low and verifier medium. Luna Max/Fast is a separate
explicit preset, not an automatic economy choice. Native direct model/effort selection can provide
any suitable role without installing a preset.

Use [runtime integrations](runtime-integrations.md) for installation, trust, upgrade and removal.
A profile's model/effort can override a spawn request. Avoid conflicting profiles by using a direct
generic role request when the runtime permits it; record actual requested/effective evidence.

## Guarded CLI adapter

Prefer native collaboration for interactive work and the official Codex SDK/app-server for new
application controllers. The adapter remains for an explicit headless/isolation or cross-provider
gap: candidate copies, path scope, repository locks, process groups, output bounds, structured
handoffs and private lifecycle evidence. It disables recursive delegation and network access.
It does not automatically integrate candidates.

For a generic role, select exact model and effort, preserving the observed parent in same-model mode:

```bash
python3 scripts/run_codex_agent.py \
  --role explorer --model gpt-5.6-sol --reasoning-effort medium \
  --parent-model gpt-5.6-sol --policy same-model \
  --compatibility-reason headless-isolation-required \
  --stage-id architecture-map --cwd /path/to/repo \
  --output-dir /tmp/gpt-engineer/architecture < /path/to/task-packet.txt
```

Use `--policy mixed-model` only for a deliberate different-model child. The caller supplies the
observed parent identity; the CLI cannot attest the parent's session. Generic roles do not inherit
a Fast tier. Named presets remain explicit compatibility options: `--role astra-explorer` or
`--role terra-explorer --suite economy`; the legacy suite name selects presets, not a parent.

Writer roles need `--allow-writes` and owned repository-relative `--allow-path` values. Dirty-path
exceptions use `--allow-dirty-path`. Inspect result.json, candidate changes/deletions, checks and
route evidence before integration. At most two read-only adapters may run together; serialize
candidate writers for the same repository. A successful dry run establishes command construction,
not effective provider/model execution. Retain separate requested and effective fields.
