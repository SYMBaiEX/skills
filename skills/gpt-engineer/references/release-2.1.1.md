# GPT Engineer 2.1.1

September 13, 2026. A focused follow-up to 2.1 for productive long-running work.

## Changes

- Remove the optional CLI adapter's automatic 30-minute child deadline. Omitted `--timeout` means
  no duration deadline; an explicitly supplied timeout must be positive and remains binding.
- Clarify in GPT Engineer and GPT Orchestration Auto that progress checkpoints and estimates do not
  end a healthy task. Continue authorized implementation, verification, and correction through the
  requested outcome, including multi-hour work and compaction.
- Keep explicit user/operator limits, runtime limits, ownership, cancellation, acceptance evidence,
  and safeguards against repeated unproductive attempts. Persistence does not expand authority.
- Fix an existing shutdown gap: a descendant could survive once its group leader exited. Escalation
  now checks the owned group independently; uncertain cleanup fails acceptance. Processes escaping
  into another session still require separate owned handles.
- Shorten activation descriptions and provide an optional
  [long-running and prompt-tuning reference](long-running-work.md). Native context management and
  the existing plan/journal preserve progress without creating another transcript or continuation hook.

The source review includes OpenAI's September 11 article,
[Rethinking skills and prompts for Astra](https://learn.chatgpt.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra),
current [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model), and
[Codex long-running work](https://learn.chatgpt.com/docs/long-running-work). The reference maps each
recommendation to its source and distinguishes older execution-plan examples from current model policy.

## Migration

Headless operators who relied on the old implicit deadline must now pass `--timeout 1800` to retain
that 30-minute ceiling, or choose a deadline appropriate to their task. Keep a supervisor and the
process handle when omitting a deadline. Operational timeouts for lock acquisition, metadata probes,
and shutdown remain separate. Bounded output retention remains; truncation fails acceptance.

The selected parent, routing policy, profile assets, hook configuration, and trust remain unchanged.
The optional profile/bootstrap bundle remains 2.1.0 because its assets did not change.

Update only the affected installed skills:

```bash
bunx skills@1.5.26 add SYMBaiEX/skills \
  --skill gpt-engineer gpt-orchestration-auto --agent codex claude-code --global --yes
```

Updated skill guidance is available on subsequent activation. No native profile reload or new hook
trust is needed for this patch.

## Evidence boundaries

All 202 automated tests passed (158 core, 44 companion), along with validation and discovery of all
12 skills. Independent review found no remaining release blocker after the shutdown fix.

Adapter regressions cover omitted deadlines, invalid deadlines rejected before launch, explicit
timeout failure, interruption cleanup, and a real descendant that ignores graceful signals after
its leader exits. A separate six-scenario decision review covers productive
multi-hour work, hard caps, quiet processes, compaction, stalled experiments, and completed scope.
These are deterministic checks and a prompt decision exercise, not a live multi-hour soak or proof
of faster/cheaper engineering. Measure accepted outcomes, context, retries, and elapsed time on
subsequent comparable real runs before claiming a performance improvement.
