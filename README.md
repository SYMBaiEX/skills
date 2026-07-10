# skills

Public [Agent Skills](https://agentskills.io/home) — portable `SKILL.md` capability packages that
work across Claude Code, Codex, Cursor, and other Skills-compatible agents.

## Skills

- [`skills/claude-multi-agent/`](skills/claude-multi-agent/) — delegate real engineering work to
  Claude Code CLI as an autonomous multi-agent team: an Opus 4.8 orchestrator delegating to
  Sonnet 5 subagents, driven headlessly via `claude -p` / `claude --bg`. Built for hand-off from
  another agent (e.g. OpenAI Codex acting as the product owner) that wants to give Claude Code a
  task and walk away.
- [`skills/gpt-orchestration/`](skills/gpt-orchestration/) — coordinate native agent fleets for
  repository-wide audits and implementation work with explicit ownership, safe concurrency,
  runtime-honest model handling, and independent verification.

## Install a skill

Skills in this repo follow the open [Agent Skills spec](https://agentskills.io/specification):
a folder with a `SKILL.md` (metadata + instructions) plus optional `scripts/`, `references/`, and
`assets/`, kept under `skills/<name>/` so the [`skills` CLI](https://github.com/vercel-labs/skills)
(the tool behind [skills.sh](https://www.skills.sh/)) auto-discovers them:

```bash
npx skills add SYMBaiEX/skills                         # interactive: pick agent + skill
npx skills add SYMBaiEX/skills --skill claude-multi-agent -y
npx skills add SYMBaiEX/skills --skill gpt-orchestration -y
```

Or just copy the skill folder into your own agent's skill directory (e.g. `.claude/skills/`,
`.codex/skills/`, or wherever your agent looks for skills — see the `skills` CLI's supported-agent
table for the exact path per agent).
