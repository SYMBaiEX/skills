# skills

Public [Agent Skills](https://agentskills.io/home) — portable `SKILL.md` capability packages that
work across Claude Code, Codex, Cursor, and other Skills-compatible agents.

This repository is also a conformant [Agent Plugins 1.0](https://agent-plugins.org/specification)
package. Root [`plugin.json`](plugin.json) describes the package and [`mcp.json`](mcp.json) points
compatible clients at the authenticated SYMBaiEX Streamable HTTP MCP server. Read [`AGENTS.md`](AGENTS.md)
for the repository-wide credential and approval boundaries.

## Skills

- [`skills/gpt-engineer/`](skills/gpt-engineer/) — the primary end-to-end GPT engineer: strict
  GPT-5.6 Sol/Terra/Luna research, implementation, integration, verification, bounded goal
  persistence, and task-owned resource teardown.
- [`skills/gpt-engineer-mem/`](skills/gpt-engineer-mem/) — the memory-aware GPT engineer: bounded
  Claude Mem/Codex recall, live freshness checks, GPT-5.6 Sol/Terra/Luna delivery, and read-only
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
`--upgrade` replaces only bundled agent-profile destinations. Use `--provider all --upgrade` only
when Claude profiles are explicitly wanted. For project-local profiles and conservative Codex hooks,
replace `--global` with `/path/to/repository`.

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
for any transition to Codex Sol, Terra, Luna, or Spark.

Project hooks/settings are optional: run `bootstrap.sh /path/to/repository`, then commit those files
before an isolated workflow run (or explicitly use `IN_PLACE=1`). Workflow evidence defaults to a
unique directory under `${CLAUDE_CONFIG_DIR:-~/.claude}/workflow-runs/`, outside the repository.

Or just copy the skill folder into your own agent's skill directory (e.g. `.claude/skills/`,
`.codex/skills/`, or wherever your agent looks for skills — see the `skills` CLI's supported-agent
table for the exact path per agent).
