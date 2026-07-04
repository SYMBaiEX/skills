# Safety guidance for autonomous runs

Handing a task to Claude Code and walking away means nobody is watching for a dangerous command in
real time. Read this before enabling `bypassPermissions` or leaving a `--bg` session unattended for
a long task.

## Permission modes, from safest to loosest

| Mode | What it does |
|---|---|
| `default` | Prompts for everything not pre-approved. Useless for unattended runs — it'll just hang waiting for input that never comes. |
| `plan` | Read-only exploration, no mutations. Good for a first pass where you want a plan back before committing to changes. |
| `dontAsk` | Auto-*denies* anything not explicitly allowed. Safe default for locked-down CI: nothing unexpected happens, but the run may fail partway if it needed something you didn't pre-approve. |
| `acceptEdits` | Auto-accepts file edits and common filesystem commands (`mkdir`, `touch`, `mv`, `cp`) within the working directory / `additionalDirectories`. Other shell commands and network requests still need an explicit `--allowedTools` entry or `permissions.allow` rule. **This is the default in `scripts/run-team.sh` and `scripts/resume-team.sh`.** It's the sweet spot for most autonomous engineering tasks: Claude can freely make the changes and run the build, but a genuinely novel or risky shell command still needs a rule.
| `auto` | Background classifier reviews commands and protected-directory writes at runtime. |
| `bypassPermissions` | Skips permission prompts entirely, including writes to `.git`, `.config/git`, `.claude`, `.vscode`, `.idea`, `.husky`, `.cargo`, `.devcontainer`, `.yarn`, `.mvn`. Explicit `ask` rules and root/home-directory removals (`rm -rf /`) still prompt. **This is what `scripts/launch-team-bg.sh` defaults to**, because a walk-away background session with no human watching has no one to answer a permission prompt anyway — if it hits one under a stricter mode, the run just stalls forever instead of failing loud.

Override any script's default with the `PERMISSION_MODE` env var, e.g.
`PERMISSION_MODE=dontAsk bash scripts/run-team.sh "..."`.

## Why every script defaults to `--worktree`

`bypassPermissions` (and even `acceptEdits`, to a lesser degree) trades human review for
throughput. The mitigation this skill relies on is **blast-radius containment, not permission
strictness**: every script passes `--worktree <name>`, which runs the session against an isolated
git worktree at `<repo>/.claude/worktrees/<name>` rather than your actual checkout. A runaway or
wrong-headed change lands in a disposable branch you can inspect, diff, or delete — it never
touches your working tree directly.

Before merging anything a walk-away run produced:

1. Read the diff on the worktree branch yourself (or have a reviewer subagent/human do it) — don't
   merge on the orchestrator's word alone.
2. Run the real CI, not just what the tester subagent ran locally.
3. Delete the worktree once you've either merged or discarded the change (`git worktree remove`).

## Additional containment for genuinely unattended, long-running work

If you're running this against a repo with real credentials, deploy access, or write access to
external systems (cloud resources, payment APIs, production databases), worktree isolation alone
isn't enough — the worktree still has the same filesystem, network access, and ambient credentials
as the host. For that class of task:

- Run inside a container or VM with only the credentials the task actually needs, not your full
  developer environment.
- Set `--max-turns` and/or `--max-budget-usd` as a hard stop, so a confused orchestrator can't loop
  indefinitely or run up an unbounded bill. `scripts/run-team.sh` and `scripts/launch-team-bg.sh`
  both read `MAX_TURNS` / `MAX_BUDGET_USD` env vars for this.
- Prefer `--allowedTools`/`permissions.allow` scoped to exactly the commands the task needs over a
  blanket `bypassPermissions`, if you can predict the shape of the work in advance.
- Keep secrets out of the prompt and out of files the orchestrator can read/exfiltrate through a
  tool call — MCP servers or Bash commands it's allowed to run are an exfiltration path if
  `bypassPermissions` is on.

## If the orchestrator writes a dynamic workflow

Everything above assumes plain subagents. If the task prompt nudges the orchestrator into writing
a [dynamic workflow](https://code.claude.com/docs/en/workflows) instead (see
[WORKFLOWS.md](WORKFLOWS.md)), the envelope changes in ways this skill's `PERMISSION_MODE` doesn't
control:

- Workflow-spawned subagents always run in `acceptEdits`, regardless of whatever `PERMISSION_MODE`
  the orchestrator session itself is running under. A `bypassPermissions` walk-away session doesn't
  make a workflow's agents any less restricted — they get `acceptEdits` specifically either way.
- In headless `-p`/`--bg` mode, the interactive "here's the planned phases, run it?" approval step
  never appears — the workflow just starts. The runtime's own cap (16 concurrent / 1,000 total
  agents per run) is the real backstop here, not a permission prompt.
- Cost scales with agent count, not with how big the task looked when you wrote the prompt. Set
  `MAX_BUDGET_USD` before handing off anything migration- or audit-shaped, especially in walk-away
  mode where nothing is watching the token counter.

## Never use Fable here

Don't set `model: fable` on the orchestrator or any subagent, and don't include `fable` in a
`--fallback-model` chain for this workflow. Fable is a fast/lightweight tier not suited to either
seat this skill defines: the orchestrator needs Opus's planning quality, and the worker subagents
need Sonnet's coding reliability. If cost is a concern, tune `--max-budget-usd` and scope the task
smaller — don't downgrade the model tier.
