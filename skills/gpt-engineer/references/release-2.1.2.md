# GPT Engineer 2.1.2

September 15, 2026. Focused guidance update from a recent local telemetry audit.

## Changes

- Distinguish native Guardian approval review from GPT Engineer's coding delegates and reviewers.
  Diagnose workspace mismatch and unnecessary escalation without changing security settings.
- Keep tool output decision-relevant; budget large mandatory instruction reads independently and
  recover missing ranges after truncation rather than repeatedly replaying complete bundles.
- Separate created-agent cohorts from resumed activity, loaded versions from installed versions,
  context estimates from completed compactions, and incremental usage from cumulative counters.
- Retain productive long-running work, adaptive delegation, selected models/effort, and existing
  acceptance and cleanup contracts. No new hooks, polling loop, mandatory fleet, or Python dependency.

The optional profiles/bootstrap assets remain 2.1.0 because they did not change. Companion skills
continue to use the installed core; this release does not relabel unchanged companion packages.

## Evidence limits

Validation: 202 existing automated tests, all 12 package structures, Agent Skills reference
validation, and Skills CLI discovery passed. A separate fresh-context review exercised four
hypothetical decisions without finding a blocker; it was not a live performance benchmark.
Thirteen regression tests also passed in the separate private telemetry-analysis repository.

The audit established approval-boundary friction and historical instruction truncation, not a
current-version context regression or a causal benefit from larger fleets. No guaranteed latency
or billing improvement is claimed. Validate the next ordinary engineering runs against comparable
task contracts before changing fleet size, effort, or runtime settings.

Official guidance checked: [Astra skills and prompts](https://learn.chatgpt.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
and [Codex auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review). The update uses targeted
guidance and progressive disclosure; private traces and project-specific evidence are not published.
