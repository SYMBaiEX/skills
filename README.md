# skills

Public [Agent Skills](https://agentskills.io/home) — portable `SKILL.md` capability packages that
work across Claude Code, Codex, Cursor, and other Skills-compatible agents.

## Skills

- [`skills/gpt-engineer/`](skills/gpt-engineer/) — the primary end-to-end GPT engineer: provider-routed
  research, implementation, integration, verification, goal persistence, and Codex/Claude bootstrap.
- [`skills/gpt-engineer-spark/`](skills/gpt-engineer-spark/) — keep a capable lead in control while
  a model-pinned GPT-5.3-Codex-Spark fleet handles bounded parallel exploration, candidate edits, and checks.
- [`skills/claude-multi-agent/`](skills/claude-multi-agent/) — delegate real engineering work to
  Claude Code CLI as an autonomous multi-agent team: an Opus 4.8 orchestrator delegating to
  Sonnet 5 subagents, driven headlessly via `claude -p` / `claude --bg`. Built for hand-off from
  another agent (e.g. OpenAI Codex acting as the product owner) that wants to give Claude Code a
  task and walk away.
- [`skills/gpt-orchestration/`](skills/gpt-orchestration/) — coordinate native agent fleets for
  repository-wide audits and implementation work with explicit ownership, safe concurrency,
  runtime-honest model handling, and independent verification.
- [`skills/gpt-orchestration-build/`](skills/gpt-orchestration-build/) — take an existing audit,
  finding list, or implementation plan and build every confirmed item through verified waves.
- [`skills/gpt-orchestration-auto/`](skills/gpt-orchestration-auto/) — run a persistent `/goal`-style
  research, implementation, verification, and gap-closing loop until the outcome is complete.

## Install a skill

Skills in this repo follow the open [Agent Skills spec](https://agentskills.io/specification):
a folder with a `SKILL.md` (metadata + instructions) plus optional `scripts/`, `references/`, and
`assets/`, kept under `skills/<name>/` so the [`skills` CLI](https://github.com/vercel-labs/skills)
(the tool behind [skills.sh](https://www.skills.sh/)) auto-discovers them:

```bash
npx skills add SYMBaiEX/skills                         # interactive: pick agent + skill
npx skills add SYMBaiEX/skills --skill gpt-engineer -y
npx skills add SYMBaiEX/skills --skill gpt-engineer-spark -y
npx skills add SYMBaiEX/skills --skill claude-multi-agent -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration-build -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration-auto -y
```

For the complete GPT Engineer workflow in Codex and Claude Code, install it globally, register the
bundled provider-native model profiles, then restart both clients:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill gpt-engineer --agent codex claude-code --global --yes
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --global
python3 ~/.agents/skills/gpt-engineer/scripts/bootstrap.py --check --global
```

The profile bootstrap is deliberately separate from skills.sh: it refuses conflicting files and does
not edit provider configuration. For project-local profiles and conservative Codex hooks, replace
`--global` with `/path/to/repository`.

Install and register the Codex-only Spark fleet separately:

```bash
npx skills add https://github.com/SYMBaiEX/skills \
  --skill gpt-engineer-spark --agent codex --global --yes
python3 ~/.agents/skills/gpt-engineer-spark/scripts/bootstrap.py --global
python3 ~/.agents/skills/gpt-engineer-spark/scripts/bootstrap.py --check --global
```

Spark fallback writers use isolated candidate copies and return reviewable change bundles. The capable
main agent integrates those bundles and owns the final repository checks.

Or just copy the skill folder into your own agent's skill directory (e.g. `.claude/skills/`,
`.codex/skills/`, or wherever your agent looks for skills — see the `skills` CLI's supported-agent
table for the exact path per agent).
