# Handoff protocol

The exact state this skill's scripts read and write, so you can build your own wrapper (in Codex,
a CI pipeline, another Claude Code instance, anything with a shell) instead of using the bundled
`scripts/*.sh` verbatim.

## State directory: `.claude-team/`

Created in the current working directory (the target repo) on first run.

| File | Written by | Contents |
|---|---|---|
| `.claude-team/last-result.json` | `run-team.sh`, `resume-team.sh` | The full `--output-format json` payload from the most recent synchronous call: `result` (text), `session_id`, `total_cost_usd`, `is_error`, `num_turns`, plus per-model cost breakdown. |
| `.claude-team/last-session-id` | `run-team.sh`, `resume-team.sh` | Just the session id string, so the next `resume-team.sh` call knows what to `--resume`. |
| `.claude-team/done-<session_id>.json` | `on-stop-notify.sh` hook | `{"session_id": "...", "status": "done"}`. Written the moment the orchestrator's `Stop` event fires — this is what a walk-away poller should watch for instead of scraping `claude logs`. |

None of this is Claude Code's own state (that lives under `~/.claude/`) — it's a plain,
grep/jq-able contract this skill defines on top, so the calling agent doesn't need to understand
Claude Code's internal transcript format at all.

## The loop, end to end

```
Codex (or any orchestrator)
  │
  ├─▶ scripts/run-team.sh "<task>"          (blocking)      ─┐
  │     or                                                    │  either path produces
  ├─▶ scripts/launch-team-bg.sh "<task>"     (walk away)     ─┘  .claude-team/last-session-id
  │        │
  │        ▼ (only for the walk-away path)
  │   poll: scripts/check-team.sh              — list sessions
  │         scripts/check-team.sh <id>          — tail one
  │         test -f .claude-team/done-<id>.json — cheap "is it finished" check
  │
  ├─▶ read .claude-team/last-result.json, decide what's next
  │
  ├─▶ scripts/resume-team.sh "<feedback, as if Codex were the user>"
  │        (repeats: reads .claude-team/last-session-id, calls `claude -p --resume`)
  │
  └─▶ repeat resume-team.sh for as many rounds as needed, then inspect the
      worktree diff and merge/discard.
```

Every step after the first can be re-derived from the state files alone — nothing requires holding
conversation history in the calling agent's own context. This is the point: Codex doesn't need to
remember what it asked for three rounds ago, because `--resume` means Claude Code's own session
already has that context, and `last-result.json` has whatever it needs to decide the next
instruction.

## Hook events relevant to this protocol

Full event list is large (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `PermissionRequest`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`,
`PostCompact`, and more) — see Claude Code's own hooks documentation for the complete reference.
The two this skill wires up:

- **`PostToolUse`** matching `Edit|Write` → `scripts/hooks/post-edit-lint.sh`. Fires after every
  file change, any subagent or the orchestrator itself. Always exits 0 (a linting hook should never
  be the reason a task fails).
- **`Stop`** (no matcher — fires once per session end) → `scripts/hooks/on-stop-notify.sh`. This is
  what writes the `done-<session_id>.json` marker. Note: the *same* hook body, if defined in a
  subagent's own frontmatter instead of `settings.json`, is auto-converted to `SubagentStop` and
  fires per-subagent instead of per-session — useful if you want a marker file per subagent
  finishing rather than only the top-level orchestrator.

If you want finer-grained signals — e.g. "notify after the reviewer subagent specifically
finishes" — add a `SubagentStop` hook in `settings.json` with a matcher on the agent's `name`
(`"matcher": "reviewer"`), or add the hook directly to that agent's frontmatter in
`assets/agents/reviewer.md`.

## Extending the protocol

Anything beyond "did it finish and what did it say" — e.g. posting to a webhook, pinging a Slack
channel, updating a ticket — is a job for another hook (`type: command` running a script, or a
`type: http` hook posting to an endpoint) rather than polling. Wire it into whichever event fires
at the right time (`SubagentStop` for per-subagent, `Stop` for the whole run, `PostToolUse` for
every file change) and leave the state-file contract above alone so the bundled scripts keep
working alongside your addition.
