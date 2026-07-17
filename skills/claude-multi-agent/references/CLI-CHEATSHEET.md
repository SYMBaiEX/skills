# Claude Code CLI cheat sheet (for this skill)

Condensed from the official CLI reference. Only flags this skill's scripts use or that you'll
likely need when extending them. Run `claude --help` for the rest — note that `--help` doesn't
list every flag, so absence there doesn't mean unavailable.

## Modes

| Flag | Effect |
|---|---|
| `-p`, `--print "task"` | Non-interactive, blocking. Prints the result and exits. This is "headless" mode. |
| `--bg`, `--background "task"` | Starts a background session and returns immediately. **Cannot combine with `-p`.** Prints a session id + management commands. |
| `--continue`, `-c` | Resume the most recent conversation in the current directory. |
| `--resume`, `-r <id-or-name>` | Resume a specific session by id or name. |
| `--fork-session` | With `--resume`/`--continue`, branch into a new session id instead of continuing the same one. |

## Model selection

| Flag | Effect |
|---|---|
| `--model opus` \| `sonnet` \| `haiku` \| `fable` | Alias for the latest model in that tier. `opus` = Opus 4.8, `sonnet` = Sonnet 5, as of this writing. Never use `fable` for orchestrator or subagent seats in this skill. |
| `--model claude-opus-4-8` / `claude-sonnet-5` | Pin an explicit model id instead of "latest". |
| `--fallback-model <list>` | Comma-separated fallback chain tried in order if the primary is overloaded/unavailable. Keep `fable` out of this chain. |
| `CLAUDE_CODE_SUBAGENT_MODEL` (env var) | Forces **every** subagent (built-in and custom, regardless of their own `model:` frontmatter) onto this model. Highest priority in the resolution order. This is how the orchestrator/subagent split in this skill actually works. |

Subagent model resolution order (highest wins): `CLAUDE_CODE_SUBAGENT_MODEL` env var → per-invocation
`model` param (Claude sets this when spawning) → the subagent file's `model:` frontmatter → the
main conversation's model.

## Permissions

| Flag | Effect |
|---|---|
| `--permission-mode default\|acceptEdits\|auto\|dontAsk\|bypassPermissions\|plan` | Starting permission mode for the session. |
| `--dangerously-skip-permissions` | Shorthand for `--permission-mode bypassPermissions`. |
| `--allowedTools "Bash(git diff *)" "Read"` | Pre-approve specific tools/patterns without changing the whole mode. |
| `--disallowedTools "Edit"` | Deny specific tools/patterns; a bare tool name removes it entirely. |
| `--tools "Bash,Edit,Read"` | Restrict which built-in tools exist at all (not just permission-gated). |

See [SAFETY.md](SAFETY.md) for what each permission mode actually skips.

## Isolation

| Flag | Effect |
|---|---|
| `--worktree`, `-w <name>` | Runs the session in an isolated git worktree at `<repo>/.claude/worktrees/<name>`. Accepts `#<pr-number>` or a PR URL to branch from an existing PR. |
| `--add-dir <path...>` | Grants file access to additional directories (not their `.claude/` config). |

## Output & scripting

| Flag | Effect |
|---|---|
| `--output-format text\|json\|stream-json` | `json` gives `{result, session_id, total_cost_usd, is_error, num_turns, ...}` — parse with `jq`. `stream-json` is newline-delimited events for real-time streaming. |
| `--json-schema '<schema>'` | With `--output-format json`, validates the response into a `structured_output` field matching your JSON Schema. |
| `--session-id <uuid>` | Force a specific session id instead of letting Claude Code generate one. |
| `--max-turns <n>` | Hard cap on agentic turns; exits with an error at the limit. |
| `--max-budget-usd <n>` | Hard cap on spend for the invocation. |
| `--include-hook-events` | Include hook lifecycle events in a `stream-json` stream. |
| `--bare` | Skip auto-discovery of hooks/skills/plugins/MCP/CLAUDE.md/auto-memory for faster, reproducible one-off calls. **Do not use this for the orchestrator run** — it would also skip the `.claude/agents/` custom subagents this skill installs. Fine for narrow utility calls (e.g. a lint-only invocation). |

## Prompts & config for scripted calls

| Flag | Effect |
|---|---|
| `--append-system-prompt "text"` / `--append-system-prompt-file <path>` | Add instructions on top of the default system prompt. Preferred over replacing it, so tool guidance/safety instructions stay intact. |
| `--system-prompt "text"` / `--system-prompt-file <path>` | Replace the entire system prompt. Only do this if you're building a non-coding-agent pipeline that no human is watching. |
| `--settings <path-or-json>` | Load a settings file/inline JSON for this invocation; see `assets/settings.json`. |
| `--agents '<json>'` | Define custom subagents inline for the session (same fields as subagent frontmatter, plus `prompt`). Useful with `--bare` since it skips `.claude/agents/` discovery. |
| `--mcp-config <path-or-json...>` | Load MCP servers for this invocation. |

## Managing background sessions (the "walk away" surface)

| Command | Effect |
|---|---|
| `claude agents` / `claude agents --json [--cwd <path>] [--all]` | Interactive or scriptable list of background sessions. `--all` includes completed ones. |
| `claude logs <id>` | Print recent output from a background session. |
| `claude attach <id>` | Attach to a background session in the current terminal. |
| `claude respawn <id> [--all]` | Restart a stopped/crashed background session with conversation intact. |
| `claude stop <id>` (alias `claude kill`) | Stop a background session. |
| `claude rm <id>` | Remove a session from the list (transcript stays on disk, still resumable). |

## Dynamic workflows

There is no `claude workflow` CLI subcommand. Saved scripts live in `.claude/workflows/` or
`~/.claude/workflows/` and run as `/<name>`. For deterministic SDK invocation, use Agent SDK
v0.3.149+ `Workflow({ name | scriptPath | script, args, resumeFromRunId })`. Set
`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` for a headless call that must wait beyond the default
background ceiling. See [WORKFLOWS.md](WORKFLOWS.md) for the script/runtime contract.

## Session ids and resume

Session id lookup is **scoped to the current project directory and its git worktrees**. Always run
follow-up (`--resume`, `--continue`, `claude agents`, `claude logs`) from the same working directory
the original session started in, or against its `--worktree` path.
