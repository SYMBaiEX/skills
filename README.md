# skills

Public [Agent Skills](https://agentskills.io/home) — portable `SKILL.md` capability packages that
work across Claude Code, Codex, Cursor, and other Skills-compatible agents.

This repository is also a conformant [Agent Plugins 1.0](https://agent-plugins.org/specification)
package. Root [`plugin.json`](plugin.json) describes the package and [`mcp.json`](mcp.json) points
compatible clients at the public documentation and authenticated evidence Streamable HTTP MCP
servers. Read [`AGENTS.md`](AGENTS.md) for the repository-wide credential and approval boundaries.

## Skills

- [`skills/gpt-engineer/`](skills/gpt-engineer/) — GPT-6 Astra engineering from research through
  verified delivery. Start with one Astra agent; delegate when independent work saves time or adds
  useful review. Includes proportionate tests, optional economy routes, native context retrieval,
  private durable run journals, outcome measurement, and task-owned cleanup. Native Codex is the
  interactive path; current SDK and managed Agents API guidance supports programmatic work. The
  Python CLI runner remains a guarded compatibility adapter.
- [`skills/gpt-engineer-mem/`](skills/gpt-engineer-mem/) — the memory-aware GPT engineer: bounded
  Claude Mem/Codex recall, live freshness checks, Astra delivery, and read-only
  memory-service diagnostics.
- [`skills/gpt-engineer-spark/`](skills/gpt-engineer-spark/) — keep a capable lead in control while
  a model-pinned GPT-5.3-Codex-Spark fleet handles dependency-aware exploration, isolated candidate
  edits, and checks.
- [`skills/claude-multi-agent/`](skills/claude-multi-agent/) — delegate real engineering work to
  Claude Code as an autonomous team or a saved native dynamic workflow with explicit research,
  planning, build, verification, bounded gap-closing, and child-process cleanup phases.
- [`skills/gpt-orchestration/`](skills/gpt-orchestration/) — coordinate native agent fleets for
  repository-wide audits and implementation work with explicit ownership, safe concurrency,
  runtime-honest model handling, and independent verification.
- [`skills/gpt-orchestration-build/`](skills/gpt-orchestration-build/) — take an existing audit,
  finding list, or implementation plan and build every confirmed item through verified waves.
- [`skills/gpt-orchestration-auto/`](skills/gpt-orchestration-auto/) — run a persistent `/goal`-style
  research, implementation, verification, and gap-closing loop until the outcome is complete.
- [`skills/symbaiex-agent-enrollment/`](skills/symbaiex-agent-enrollment/) — enroll and operate a
  user-directed SYMBaiEX agent with locally held Ed25519 credentials.
- [`skills/symbaiex-evidence-search/`](skills/symbaiex-evidence-search/) — search bounded public
  evidence and editorial records through the published REST or MCP contracts.
- [`skills/symbaiex-claim-verification/`](skills/symbaiex-claim-verification/) — verify stored claims
  against version-bound citations and inspect revision history.
- [`skills/symbaiex-research-jobs/`](skills/symbaiex-research-jobs/) — create and monitor bounded
  cited research and JSONL export jobs.
- [`skills/symbaiex-webhooks/`](skills/symbaiex-webhooks/) — configure owner-scoped, HMAC-signed
  evidence and usage event delivery.

## Install a skill

Skills in this repo follow the open [Agent Skills spec](https://agentskills.io/specification):
a folder with a `SKILL.md` (metadata + instructions) plus optional `scripts/`, `references/`, and
`assets/`, kept under `skills/<name>/` so the [`skills` CLI](https://github.com/vercel-labs/skills)
(the tool behind [skills.sh](https://www.skills.sh/)) auto-discovers them:

```bash
npx skills add SYMBaiEX/skills                         # interactive: pick agent + skill
npx skills add SYMBaiEX/skills --skill gpt-engineer -y
npx skills add SYMBaiEX/skills --skill gpt-engineer-mem -y
npx skills add SYMBaiEX/skills --skill gpt-engineer-spark -y
npx skills add SYMBaiEX/skills --skill claude-multi-agent -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration-build -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration-auto -y
```

Install the SYMBaiEX platform skills with Bun:

```bash
bunx skills add SYMBaiEX/skills --skill symbaiex-agent-enrollment -y
bunx skills add SYMBaiEX/skills --skill symbaiex-evidence-search -y
bunx skills add SYMBaiEX/skills --skill symbaiex-claim-verification -y
bunx skills add SYMBaiEX/skills --skill symbaiex-research-jobs -y
bunx skills add SYMBaiEX/skills --skill symbaiex-webhooks -y
```

For the complete GPT Engineer workflow in Codex and Claude Code, install it globally, register the
bundled provider-native model profiles, then restart both clients:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill gpt-engineer --agent codex claude-code --global --yes
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --upgrade --global
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --provider codex --check --global
python3 ~/.agents/skills/gpt-engineer/scripts/audit_routing.py --cwd /path/to/repo --runtime --json
```

Install the memory-aware variant alongside the base engineer. It reuses the base profile setup when
available, remains usable as a standalone orchestration contract, and never configures or restarts
Claude Mem automatically:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill gpt-engineer gpt-engineer-mem \
  --agent codex claude-code --global --yes
python3 ~/.agents/skills/gpt-engineer-mem/scripts/memory_preflight.py --json
```

The profile bootstrap is deliberately separate from skills.sh. It never edits provider configuration;
`--upgrade` updates bundled profiles and managed project hooks, and backs up/removes the known
unmodified retired Sol profile. Customized retired profiles require review and are preserved.
Use `--provider all --upgrade` only
when Claude profiles are explicitly wanted. For project-local profiles and conservative Codex hooks,
replace `--global` with `/path/to/repository`.

The optional routing audit and repository validation require Python 3.11+ or an environment with
`tomli` so all valid TOML profile syntax is parsed correctly. Native Astra work needs no Python helper.

Do not activate a copied Luna model catalog as routine setup. Custom catalogs freeze upstream model
metadata and the runtime audit rejects stale or unattested overrides. Prefer stock native routing;
use the guarded CLI adapter for a justified compatibility gap in explicitly selected economy work.

GPT Engineer 2 defaults to exact `gpt-6-astra` for the lead and optional children. The four bundled
roles are `astra_engineer` (high effort), `astra_explorer`, `astra_worker`, and `astra_verifier`
(medium effort). A runtime with explicit model/effort selection can delegate without installed
custom roles. Existing Terra/Luna routes are available through explicit economy selection; Sol is
historical. Astra's [official migration guidance](https://developers.openai.com/api/docs/guides/latest-model)
informs the shorter prompts, selective delegation, persistent user intent, and calibrated testing.
See [runtime choices and API compatibility](skills/gpt-engineer/references/dynamic-workflows.md)
before building a controller: native Codex, Codex SDK, Agents API, and Responses expose different
capabilities. The skill does not enable experimental context settings, Fast mode, or hosted sessions.

Long GPT Engineer runs use private state outside the checkout by default. Inspect or resume that
state with `run_journal.py`; opt a repository into a local `.engineer` control directory only with an
explicit init. Command evidence and fleet outcome analysis are separate, fail-closed tools:

```bash
python3 ~/.agents/skills/gpt-engineer/scripts/run_journal.py --help
python3 ~/.agents/skills/gpt-engineer/scripts/cache_gates.py --help
python3 ~/.agents/skills/gpt-engineer/scripts/join_fleet_outcomes.py --help
```

These tools store normalized lifecycle, requirement, gate, and outcome evidence—not raw prompts,
responses, reasoning, child transcripts, stderr, or telemetry logs.

Install and register the Codex-only Spark fleet separately:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill gpt-engineer-spark --agent codex --global --yes
python3 ~/.agents/skills/gpt-engineer-spark/scripts/bootstrap.py --global
python3 ~/.agents/skills/gpt-engineer-spark/scripts/bootstrap.py --check --global
```

Spark fallback writers use isolated candidate copies and return reviewable change bundles. The capable
main agent integrates those bundles, owns the final repository checks, and reclaims task-owned agents,
subprocesses, listeners, and temporary worktrees. Shared MCP services and other active tasks are never
cleanup targets.

Install the Claude team/workflow adapter and bootstrap it into a target repository:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill claude-multi-agent --agent claude-code --global --yes
bash ~/.agents/skills/claude-multi-agent/scripts/bootstrap.sh --global
cd /path/to/repository
bash ~/.agents/skills/claude-multi-agent/scripts/run-workflow.sh \
  "Research, implement, verify, and gap-close this engineering goal"
```

The saved `.claude/workflows/gpt-engineer-dynamic.js` uses Claude's native workflow runtime. The
default runner starts from the exact clean `HEAD` and returns an isolated candidate patch; exit `3`
means the outer engineer must integrate and verify it. The outer GPT Engineer remains responsible
for any transition to Codex Astra, explicitly selected economy routes, or Spark.

Project hooks/settings are optional: run `bootstrap.sh /path/to/repository`, then commit those files
before an isolated workflow run (or explicitly use `IN_PLACE=1`). Workflow evidence defaults to a
unique directory under `${CLAUDE_CONFIG_DIR:-~/.claude}/workflow-runs/`, outside the repository.

Or just copy the skill folder into your own agent's skill directory (e.g. `.claude/skills/`,
`.codex/skills/`, or wherever your agent looks for skills — see the `skills` CLI's supported-agent
table for the exact path per agent).
