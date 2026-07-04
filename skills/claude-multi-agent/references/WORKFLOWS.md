# Dynamic workflows — when the orchestrator should reach for one

This skill's default mode is plain [subagents](https://code.claude.com/docs/en/sub-agents): the
Opus orchestrator decides, turn by turn, what to delegate to a Sonnet `engineer`/`reviewer`/
`tester`/`planner`. That's the right tool for a single scoped engineering task — a bugfix, a
feature, a focused refactor.

[Dynamic workflows](https://code.claude.com/docs/en/workflows) are a different, separate Claude
Code primitive: a JavaScript script (Claude writes it, a runtime executes it in the background)
that holds the orchestration itself — the loop, the branching, and the intermediate results — so
Claude's own context only ever holds the final answer. They scale to dozens or hundreds of agents
per run and are resumable within the same session. Reach for one when the task is:

- a codebase-wide sweep (e.g. "audit every route handler for missing auth checks")
- a large migration across many files, each done in isolation
- research that needs several sources cross-checked against each other before you trust a claim
- a plan worth drafting from multiple independent angles and weighing before committing
- "keep fixing until a check passes" — a bounded retry loop across a whole test/type-check suite

If the task Codex hands to `run-team.sh`/`launch-team-bg.sh` looks like one of those, don't rely
on the bundled subagents alone — give the orchestrator a reason to write a workflow instead.

## How to trigger one from this skill's scripts

Workflows activate on a **literal trigger in the prompt text**, which means it works exactly the
same in headless `claude -p`/`--bg` as it does interactively — there's no separate flag:

- Prepend the literal keyword `ultracode` to the task, e.g. `ultracode: migrate every component
  under src/components/ from styled-components to Tailwind, each in its own isolated copy`
- Or just phrase the task in natural language as a workflow request: `"use a workflow to audit
  every endpoint under src/routes/ for missing auth checks, then adversarially verify each
  finding"`

Either form works as-is with `run-team.sh "ultracode: <task>"` or `launch-team-bg.sh "use a
workflow to <task>"` — no script changes needed, since the trigger lives in the prompt string this
skill already passes straight through to `claude -p`/`claude --bg`.

Don't reach for `ultracode` (or `/effort ultracode`) as a blanket default for every task through
this skill: per Anthropic's own guidance it multiplies token spend meaningfully versus working the
same task turn-by-turn, and most single-feature tasks this skill is meant for don't need
dozens-of-agents scale. Use the natural-language trigger only when the task actually matches the
shapes above.

## Model routing inside a workflow script

`CLAUDE_CODE_SUBAGENT_MODEL=sonnet` (this skill's global lever, see [SKILL.md](../SKILL.md#model-configuration))
forces every *classic* subagent onto Sonnet regardless of frontmatter. Workflows are a distinct
runtime and Anthropic's own docs state the weaker default here: **"Every agent in a workflow uses
your session's model unless the script routes a stage to a different one."** That means a workflow
spawned from our Opus-orchestrator session may default every one of its `agent()` calls to Opus
unless the script explicitly overrides it — the env var is not documented to reach into workflow
`agent()` calls the way it reaches classic subagents, so don't rely on it there.

If you want a workflow's worker stages on Sonnet (which you almost always do, for the same cost
reasons this skill exists), say so directly in the task prompt: `"...and route the per-file worker
agents in the workflow to Sonnet, keeping only the planning/synthesis stage on Opus."` Claude
writes the script with `agent(prompt, { model: 'sonnet' })` on the stages you named. This is a
prompt-level instruction, not a flag — there's nothing in this skill's scripts that can force it
from outside the session.

## Safety implications specific to workflows

Read this in addition to [SAFETY.md](SAFETY.md) — workflows change the safety envelope in ways
that aren't covered by this skill's permission-mode defaults:

- **Workflow-spawned subagents always run in `acceptEdits`, regardless of the session's permission
  mode.** Even if `launch-team-bg.sh` started the orchestrator under `bypassPermissions`, a
  workflow it spawns gets its file edits auto-approved under `acceptEdits` specifically — not
  looser, not stricter, just different. Shell commands, web fetches, and MCP tools outside your
  allowlist can still prompt mid-run in an interactive session; in headless mode they instead
  follow your configured permission rules with no one to answer a prompt, same as everywhere else
  in this skill.
- **In `claude -p` and `claude --bg`, the workflow launch approval step never appears — the run
  starts immediately.** Interactively you'd see a "planned phases" confirmation; headless, there is
  no one to show it to, so a workflow the orchestrator decides to write just starts, up to the
  runtime's cap of 16 concurrent / 1,000 total agents per run. That cap is the real backstop in
  headless mode, not a permission prompt.
- **Cost scales with agent count, not with task size as you'd estimate it turn-by-turn.** This
  skill's `MAX_BUDGET_USD` / `MAX_TURNS` env vars (read by `run-team.sh`, `resume-team.sh`,
  `launch-team-bg.sh`) are still the right lever to bound a run that turns into a workflow — set
  them before handing off anything migration- or audit-shaped, especially in walk-away mode where
  no one is watching the token counter.

This skill's `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` default (see
[HANDOFF-PROTOCOL.md](HANDOFF-PROTOCOL.md#a-failure-mode-this-protocol-used-to-have-and-how-its-fixed-now))
does not affect workflows — that env var scopes to ad hoc subagent/background-Bash-task
backgrounding specifically. Workflows have their own separate toggle
(`disableWorkflows`/`CLAUDE_CODE_DISABLE_WORKFLOWS`) and Anthropic's own docs already have `claude
-p` properly wait for a workflow to finish before returning its result, unlike the subagent race
this skill's other default fixes.

## Requirements

Dynamic workflows need Claude Code v2.1.154 or later, and are available on all paid plans, direct
Anthropic API access, Amazon Bedrock, Google Cloud's Agent Platform, and Microsoft Foundry. On a
Pro plan specifically, they're off by default and need the "Dynamic workflows" toggle turned on in
`/config` first — if the orchestrator never seems to write a workflow no matter how you phrase the
task, check that before assuming the natural-language trigger isn't working.
