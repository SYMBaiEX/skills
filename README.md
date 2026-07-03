# skills

Public [Agent Skills](https://agentskills.io/home) — portable `SKILL.md` capability packages that
work across Claude Code, Codex, Cursor, and other Skills-compatible agents.

## Skills

- [`claude-multi-agent/`](claude-multi-agent/) — delegate real engineering work to Claude Code CLI
  as an autonomous multi-agent team: an Opus 4.8 orchestrator delegating to Sonnet 5 subagents,
  driven headlessly via `claude -p` / `claude --bg`. Built for hand-off from another agent (e.g.
  OpenAI Codex acting as the product owner) that wants to give Claude Code a task and walk away.

## Install a skill

Skills in this repo follow the open [Agent Skills spec](https://agentskills.io/specification):
a folder with a `SKILL.md` (metadata + instructions) plus optional `scripts/`, `references/`, and
`assets/`. Any Skills-compatible agent can consume them directly, or install via
[skills.sh](https://www.skills.sh/):

```bash
npx skills add <owner>/skills
```

Or just copy the skill folder into your project's own skill directory (e.g.
`.claude/skills/`, `.codex/skills/`, or wherever your agent looks for skills).
