# Handoff protocol

The exact state this skill's scripts read and write, so you can build your own wrapper (in Codex,
a CI pipeline, another Claude Code instance, anything with a shell) instead of using the bundled
`scripts/*.sh` verbatim.

## A failure mode this protocol used to have, and how it's fixed now

Earlier versions of this skill let subagents run in the background (Claude Code's default since
v2.1.198). That produced a real bug in practice: the orchestrator spawned the `engineer` subagent
asynchronously, ended its own turn while the subagent was still running, and the `Stop` hook fired
right then — writing a `done-<session_id>.json` marker that only meant *the top-level turn ended*,
not that the engineer subagent had finished. Meanwhile `claude -p --output-format json` prints
nothing until the very end, so from the calling agent's side the run looked hung for a long
stretch, got interrupted, and killed the still-working subagent mid-task — landing a partial edit.

Two changes fix this:

1. **Subagents now run in the foreground by default.** `run-team.sh`, `resume-team.sh`, and
   `launch-team-bg.sh` all set `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (also baked into
   `assets/settings.json`), and the four bundled agents set `background: false` in their own
   frontmatter as a second layer. This means the Agent tool call spawning a subagent *is* the join
   — it blocks until the subagent returns, so there's nothing to poll and no window where the
   top-level turn can end while a subagent is still working. The scripts also append a system
   prompt telling the orchestrator this explicitly, so it doesn't try to build its own wait loop
   with `sleep` (which Claude Code blocks as a bare polling pattern anyway) or the `Monitor` tool
   (which isn't meant for this and needs its schema loaded before it's callable in the first
   place).
2. **`run-team.sh` and `resume-team.sh` now use `--output-format stream-json --verbose`** instead
   of plain `json`, teeing the full turn-by-turn stream to `.claude-team/stream.jsonl` so the
   calling agent has a liveness signal (`tail -f` it) instead of guessing "hung vs. still working"
   from total silence. The final `result`-type event in that stream is filtered out with `jq` into
   `last-result.json`, so the downstream contract below is unchanged.

With subagents forced to the foreground, `Stop` firing really does mean everything the orchestrator
spawned has finished — the failure mode above specifically required a background subagent still
in flight when `Stop` fired, and that state can no longer happen through this skill's scripts. If
you override `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` back to unset/`0` yourself, this guarantee no
longer holds and you're back to the original race.

## State directory: `.claude-team/`

Created in the current working directory (the target repo) on first run.

| File | Written by | Contents |
|---|---|---|
| `.claude-team/last-result.json` | `run-team.sh`, `resume-team.sh` | The final `type: "result"` event filtered out of the `--output-format stream-json` stream: `result` (text), `session_id`, `total_cost_usd`, `is_error`, `num_turns`, plus per-model cost breakdown. Same fields as plain `--output-format json` would give you — just sourced from the stream instead of a single blocking payload. |
| `.claude-team/stream.jsonl` | `run-team.sh`, `resume-team.sh` | The full turn-by-turn `stream-json` transcript, written as the run progresses (not just at the end). This is the liveness signal — `tail -f` it to see the orchestrator and its subagents actually working, instead of the old plain-`json` silence that made a slow run indistinguishable from a hung one. |
| `.claude-team/last-session-id` | `run-team.sh`, `resume-team.sh` | Just the session id string, so the next `resume-team.sh` call knows what to `--resume`. |
| `.claude-team/done-<session_id>.json` | `on-stop-notify.sh` hook | `{"session_id": "...", "status": "done"}`. Written the moment the orchestrator's `Stop` event fires. With subagents forced to the foreground (see above), this reliably means the whole run — orchestrator and every subagent it spawned — is finished, not just that the top-level turn ended. |

None of this is Claude Code's own state (that lives under `~/.claude/`) — it's a plain,
grep/jq-able contract this skill defines on top, so the calling agent doesn't need to understand
Claude Code's internal transcript format at all.

If `run-team.sh`/`resume-team.sh` exit with `error: no final result event captured`, the run
errored or was interrupted before producing a result — check `stream.jsonl` for what was happening
right before it stopped rather than assuming the process just hung.

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
