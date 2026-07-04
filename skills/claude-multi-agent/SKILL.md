---
name: claude-multi-agent
description: Hand off real engineering work to Claude Code CLI as an autonomous, staffed multi-agent team - an Opus 4.8 orchestrator that plans, delegates to Sonnet 5 subagents (engineer, reviewer, tester, planner), and reports back. Use when another agent (e.g. OpenAI Codex acting as the product owner/user) needs Claude Code to act as the engineering team on a task and run headlessly via `claude -p` / `claude --bg`, including "give it a task and walk away" autonomous runs, iterative design follow-up loops, CI automation, or setting up `.claude/agents`, hooks, and permission modes for headless multi-agent Claude Code work.
license: MIT
compatibility: Requires the `claude` CLI (Claude Code) installed, authenticated, and on PATH, plus `git` and `jq`. Meant to be invoked by another shell-capable agent (OpenAI Codex, another Claude Code instance, a CI runner, or any orchestrator with Bash access).
metadata:
  author: SYMBaiEX
  version: "1.0"
allowed-tools: Bash(claude:*) Bash(git:*) Bash(jq:*) Read Write
---

# Claude Multi-Agent

Turn Claude Code into an autonomous engineering team that another agent can delegate to. The
calling agent (Codex, another orchestrator, CI) plays **product owner / user**. Claude Code plays
**the engineering team**: an Opus 4.8 orchestrator that thinks, plans, and delegates concrete
subtasks to Sonnet 5 subagents that do the heavy lifting.

Never use Fable in this setup. Fable is a lightweight/fast-path model not suited for either the
orchestrator seat (needs Opus's reasoning) or the worker seat (needs Sonnet's coding reliability).

## The core mechanism

Three levers control who does what and how reliably, and all three ship pre-wired in this skill:

1. **The orchestrator is the main session**, launched with `--model opus`. It's the thing making
   decisions, writing the plan, and deciding what to delegate vs. do itself.
2. **Every subagent is forced onto Sonnet** via the `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`
   environment variable. This is the highest-priority entry in Claude Code's model-resolution
   order — it overrides `model: inherit` on built-in subagents (Explore, Plan, general-purpose)
   *and* any custom subagent, so you don't have to hunt down every agent file to keep costs sane.
   The bundled custom agents in `assets/agents/` also set `model: sonnet` explicitly, belt-and-suspenders.
3. **Every subagent runs in the foreground**, via `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (Claude
   Code's default since v2.1.198 is background). This makes the Agent tool call itself the join —
   it blocks until the subagent returns, so the orchestrator can't end its turn while one is still
   working, and there's nothing for it to poll or sleep-wait on. See
   [references/HANDOFF-PROTOCOL.md](references/HANDOFF-PROTOCOL.md#a-failure-mode-this-protocol-used-to-have-and-how-its-fixed-now)
   for the real bug this fixes.

Everything below is just plumbing around those three facts.

## Quickstart

```bash
# 1. One-time: install the bundled subagents, settings, and hooks into the target repo
bash scripts/bootstrap.sh /path/to/target/repo

# 2. Kick off a synchronous run (blocks until done, prints JSON result)
cd /path/to/target/repo
bash /path/to/claude-multi-agent/scripts/run-team.sh "Implement rate limiting on the /login endpoint"

# 3. Or: fire it and walk away (returns immediately, check back later)
bash /path/to/claude-multi-agent/scripts/launch-team-bg.sh "Migrate the test suite from Jest to Vitest"
bash /path/to/claude-multi-agent/scripts/check-team.sh          # list background sessions
bash /path/to/claude-multi-agent/scripts/check-team.sh <id>     # tail a specific one

# 4. Follow up like a user reviewing the work (Codex plays this role)
bash /path/to/claude-multi-agent/scripts/resume-team.sh "Good, now also add a test for the 429 response"
```

Run `bootstrap.sh` once per target repo. The `scripts/*.sh` themselves can live anywhere (this
skill folder, a copied-out location, wherever) — they only assume they're invoked from *inside*
the target repo's working directory, because Claude Code session lookups are scoped to cwd.

## The three usage patterns

### 1. Synchronous — you're driving the loop yourself

`scripts/run-team.sh "<task>"` calls `claude -p --output-format stream-json --verbose` and blocks
until the orchestrator finishes. The full turn-by-turn stream is teed to `.claude-team/stream.jsonl`
(`tail -f` it for a liveness signal — don't assume a slow run is a hung one) while the final
`result` event (same fields as plain `--output-format json`: `result`, `session_id`,
`total_cost_usd`, `is_error`, `num_turns`) is filtered into `.claude-team/last-result.json`, and
the session id into `.claude-team/last-session-id`. Use this when the calling agent is scripted
and fine waiting synchronously for each round.

### 2. Walk away — true fire-and-forget

`scripts/launch-team-bg.sh "<task>"` uses `claude --bg`, which starts a background session and
returns immediately (it cannot be combined with `-p`). Claude Code's own supervisor keeps it
running. Come back later with:

- `claude agents --json --cwd <path>` (wrapped by `scripts/check-team.sh`) to list active/completed sessions
- `claude logs <id>` to see recent output
- `claude attach <id>` to reconnect interactively
- `claude stop <id>` to kill it

The `Stop` hook (see [Hooks](#hooks)) also drops a `.claude-team/done-<session_id>.json` marker
file the moment the orchestrator finishes, so a polling loop doesn't have to parse `claude logs`
output to know when it's safe to check results. Because subagents run in the foreground (see
above), that marker reliably means the whole run — not just the top-level turn — is done.

### 3. Iterative follow-up — Codex as the user

This is the "Codex directs design, Claude does the engineering" loop. After a run, read
`.claude-team/last-result.json`, decide what's next, and call `scripts/resume-team.sh "<feedback>"`.
That resumes the *same session* via `--resume`, so the orchestrator keeps full context of what it
already did — it does not re-plan from scratch. Repeat as many rounds as needed. This is the same
mechanism a human reviewing Claude Code's work in the terminal would use; the calling agent is
just standing in for the human.

Session resume is scoped to the directory it was started in — always run these scripts from the
same working directory (or the worktree, if you used `-w`) as the original invocation.

## Working directly in a dirty repo

`--worktree` isolation (the default) makes a fresh checkout — it does **not** carry over your
current uncommitted changes, since a new worktree branches from the last commit, not your working
tree's dirty state. If the task genuinely needs to operate on a repo that has uncommitted changes
present, set `IN_PLACE=1` to skip `--worktree` entirely and run directly against the current
checkout:

```bash
IN_PLACE=1 bash scripts/run-team.sh "Finish the half-done refactor in the working tree"
```

This trades away the disposable-branch safety net described in
[references/SAFETY.md](references/SAFETY.md) — commit or stash first if you want a rollback point,
since changes now land directly on whatever you're checked out to.

## Model configuration

| What | How | Why |
|---|---|---|
| Orchestrator model | `--model opus` on the top-level `claude` invocation | `opus` always resolves to the latest Opus (currently 4.8) |
| Subagent model | `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` env var | Highest-priority override, catches every subagent regardless of its own frontmatter |
| Subagent model (belt-and-suspenders) | `model: sonnet` in each `assets/agents/*.md` file | Explicit in case the env var isn't propagated by whatever wraps this |
| Pinning instead of "latest" | `--model claude-opus-4-8`, `model: claude-sonnet-5` | Use if you need reproducible behavior across a model upgrade rather than always-latest |
| Fallback on overload | `--fallback-model sonnet` (never include `fable`) | Keeps a degraded-but-capable path without dropping to a model unsuited for either seat |

Full flag reference: [references/CLI-CHEATSHEET.md](references/CLI-CHEATSHEET.md).

## Safety — read before using `bypassPermissions`

Autonomous "walk away" runs need a permission mode that doesn't stop to ask. The scripts default
to `acceptEdits` (auto-accepts file edits and common filesystem commands, but still gates network
calls and unusual shell commands) and support `bypassPermissions` (skips prompts entirely) via the
`PERMISSION_MODE` env var. `bypassPermissions` is real risk: an unattended agent can run arbitrary
commands with no human in the loop. Full guidance, including why every script defaults to
`--worktree` isolation, is in [references/SAFETY.md](references/SAFETY.md) — read it before
pointing this at anything with production credentials, a shared branch, or write access to
external systems.

## Hooks

Two hooks ship in `scripts/hooks/` and get wired into `assets/settings.json`:

- **`post-edit-lint.sh`** (`PostToolUse`, matches `Edit|Write`): best-effort auto-format after
  every file change (prettier/ruff/rustfmt/gofmt, whichever applies), so the Sonnet engineer
  subagent's output stays consistent without needing to remember to run a formatter. Never blocks
  — always exits 0.
- **`on-stop-notify.sh`** (`Stop`): writes the `.claude-team/done-<session_id>.json` completion
  marker described above, the signal a walk-away poller waits for.

Add your own — a `PreToolUse` hook to block writes outside an allowed path, a `SubagentStop` hook
to log per-subagent cost, whatever the target repo needs. See
[references/HANDOFF-PROTOCOL.md](references/HANDOFF-PROTOCOL.md) for the full hook event list and
the state-file contract the scripts rely on.

## Bundled subagents

`assets/agents/` ships four focused Sonnet subagents the orchestrator delegates to. Copy them into
`.claude/agents/` (bootstrap.sh does this) and the orchestrator will pick them up automatically by
description-matching, or you can name them explicitly in the task prompt ("use the tester
subagent to confirm this works"):

- **`engineer.md`** — implements scoped changes. Read/Write/Edit/Bash/Grep/Glob.
- **`reviewer.md`** — read-only review for correctness/security/quality. No Write/Edit.
- **`tester.md`** — discovers and runs the project's test suite, diagnoses failures.
- **`planner.md`** — breaks ambiguous tasks into an ordered plan before code gets touched.

These are starting points, not a fixed roster — edit them, add more (e.g. a `docs.md` subagent),
or delete what the target repo doesn't need. Keep every one of them on `model: sonnet`; if you add
an agent that genuinely needs Opus-level reasoning for its own subtask, that's a signal the
orchestrator should be doing that piece itself rather than delegating it.

## Subagents vs. dynamic workflows

Everything above is the classic subagent mechanism: the Opus orchestrator decides, turn by turn,
what to delegate. That's the right default for a single scoped task. Claude Code separately has
[dynamic workflows](https://code.claude.com/docs/en/workflows) — a JS script Claude writes and a
runtime executes in the background, holding the orchestration itself instead of Claude's turn-by-
turn context, scaling to hundreds of agents per run. This skill does **not** turn workflows on by
default, but the orchestrator can reach for one on its own if the task calls for it — a
codebase-wide audit, a large multi-file migration, or research that needs cross-checking. Trigger
it by phrasing the task as a workflow request (e.g. `"use a workflow to migrate every component
under src/ from styled-components to Tailwind, each in its own isolated copy"`) — it's plain prompt
text, so it works the same in headless `-p`/`--bg` mode as interactively. See
[references/WORKFLOWS.md](references/WORKFLOWS.md) for when to reach for one, how to route a
workflow's own agents onto Sonnet, and the safety implications that differ from the rest of this
skill (workflow subagents always run in `acceptEdits`, and headless launches never prompt for
approval).

## Reference material

- [references/CLI-CHEATSHEET.md](references/CLI-CHEATSHEET.md) — every `claude` CLI flag this skill touches, condensed
- [references/HANDOFF-PROTOCOL.md](references/HANDOFF-PROTOCOL.md) — the exact state files and loop the scripts implement, for building your own wrapper instead of using the bundled ones
- [references/SAFETY.md](references/SAFETY.md) — permission modes, worktree isolation, budget/turn caps, and what `bypassPermissions` does and doesn't skip
- [references/WORKFLOWS.md](references/WORKFLOWS.md) — when the orchestrator should reach for a dynamic workflow instead of plain subagents, how to route a workflow's agents onto Sonnet, and workflow-specific safety notes
