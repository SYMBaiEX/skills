# Native dynamic workflows

Read this reference when choosing, installing, invoking, or editing a Claude Code workflow.

## Choose the correct primitive

| Primitive | Plan owner | Best fit |
| --- | --- | --- |
| Subagent | Lead Claude turn | A few bounded delegated tasks |
| Agent team | Lead peer session | A handful of long-running peers that communicate |
| Dynamic workflow | JavaScript runtime | Repeatable DAGs, broad audits, migrations, cross-checked research, bounded loops |

Use `scripts/run-team.sh` for a normal scoped build. Use `scripts/run-workflow.sh` when the task
benefits from the bundled research -> plan -> build -> verify -> gap-close script. Claude Code
dynamic workflows require v2.1.154 or later.

## Programmatic invocation

Do not depend on `ultracode` prompt text in `claude -p`. In current Claude Code versions, keyword
opt-in is limited to human-origin prompts. Invoke a saved `/<name>` workflow directly, as
`scripts/run-workflow.sh` does, or use Agent SDK v0.3.149+ and the `Workflow` tool:

```ts
Workflow({
  scriptPath: "/absolute/path/to/workflow.js",
  args: { goal: "Migrate every route and verify auth behavior" },
})
```

Always inspect the returned `error` field even when status is `async_launched`, then wait for the
later task-completion event. Preserve `runId`, `scriptPath`, and `transcriptDir` as evidence.

For headless CLI runs, set `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` or an explicit high ceiling;
otherwise a long background workflow can outlive the print-mode wait.
The bundled wrapper also applies a JSON output schema and treats only `complete: true`,
`status: "complete"`, and an empty `gaps` array as shell success. Transport success alone is not
completion.

The wrapper requires the saved workflow to be installed globally. Its default isolated mode
rejects a dirty checkout, creates a detached temporary worktree from the exact current `HEAD`, and
bundles `candidate.patch`, changed paths, and deleted paths before removing the checkout. Exit `3`
means Claude finished its candidate, but the outer engineer must still integrate it and verify the
real checkout. Evidence defaults outside the repository under
`${CLAUDE_CONFIG_DIR:-~/.claude}/workflow-runs/`. Use `IN_PLACE=1` only when direct mutation is
explicitly intended. If a writer creates a commit, the wrapper diffs against the captured baseline,
preserves the patch, and fails closed.

## Saved script contract

Project workflows live at `.claude/workflows/<name>.js`; personal workflows live at
`${CLAUDE_CONFIG_DIR:-~/.claude}/workflows/<name>.js`. The nearest project definition wins.

The first statement must be a literal metadata export:

```js
export const meta = {
  name: "audit-routes",
  description: "Audit every route and verify each finding",
  phases: [{ title: "Audit", detail: "Read-only fan-out", model: "sonnet" }],
}
```

The body is plain JavaScript with top-level `await` and `return`. Use:

- `agent(prompt, options)` for one subagent;
- `parallel([() => agent(...), ...])` for a barrier;
- `pipeline(items, item => agent(...))` for bounded item fan-out;
- `phase("Name")` and `log(message)` for progress.

The workflow script itself cannot read files, run shell commands, or use Node APIs. Agents perform
all external work. Avoid `Date.now()`, `Math.random()`, and argumentless `new Date()` because resume
requires deterministic call inputs. Pass variable inputs through the global `args` value.

## Model routing

Route each agent explicitly:

```js
await agent("Synthesize the verified plan", { model: "opus", effort: "high" })
await agent("Inspect this bounded subsystem", { model: "sonnet", effort: "high" })
```

`meta.phases[].model` is display metadata, not execution routing. The environment variable
`CLAUDE_CODE_SUBAGENT_MODEL` overrides every per-agent model, including workflow agents. Leave it
unset for a mixed Opus/Sonnet workflow. `scripts/run-workflow.sh` unsets it deliberately.
That wrapper has no default fallback; set `FALLBACK_MODEL` only when the alternate model is an
authorized route and record the change in the run evidence.

Claude workflow agents can select only Claude models. They cannot select GPT Sol, Terra, Luna, or
Spark. Sequence those providers in the outer GPT Engineer orchestration.

## Safety, completion, and scale

- Workflow subagents always use `acceptEdits` and inherit the session tool allowlist.
- Headless and Agent SDK launches do not show a workflow approval prompt.
- Keep one coordinated writer per shared checkout. Put parallel writers in isolated worktrees and
  integrate them through an explicit parent gate.
- Treat agent text as a claim. Completion requires structured results plus direct repository and
  command evidence.
- Up to 16 agents run concurrently and up to 1,000 may be created per run. Start on a small slice
  and set budget/turn limits before broad work.
- There is no mid-run user sign-off. Split approval boundaries into separate workflow runs.

Pause and resume from `/workflows` in the same session. Completed unchanged `agent()` calls are
cached; an agent that was still running restarts. Exiting the session makes the next run start
fresh, so never represent cross-session restart as a resume.

Claude Code has no dedicated workflow-start/workflow-stop hook. The bundled settings log the
`Workflow` tool plus `SubagentStart`, `SubagentStop`, and `TaskCompleted` events to
`.claude-team/workflow-events.jsonl`; use the final task result, not that log alone, as the
completion barrier.

Official references: [dynamic workflows](https://code.claude.com/docs/en/workflows),
[Agent SDK Workflow tool](https://code.claude.com/docs/en/agent-sdk/typescript), and
[worktree isolation](https://code.claude.com/docs/en/worktrees).
