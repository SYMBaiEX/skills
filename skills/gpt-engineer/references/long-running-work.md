# Long-running work and prompt tuning

Use for multi-hour work, interruption recovery, or changes to the engineer's prompts. Guidance
reviewed September 13, 2026. These are workflow choices, not provider runtime guarantees.

## Continue from evidence

Define the requested outcome, relevant context, constraints, and observable completion criteria.
For a substantial migration or build, maintain a living plan with verifiable milestones, current
decisions, progress, and remaining requirements. Reuse the repository's plan format when present;
otherwise use the existing private journal when durable recovery is needed. Do not require a plan
document or a new `.engineer` directory for a small change.

Continue through authorized implementation, integration, verification, and correction of in-scope
failures. A first working patch need not be the requested outcome. Do not return merely because a
task takes hours, the initial estimate was exceeded, or native compaction occurred. Keep the same
coherent task; use independent children only where they improve the result. A skill cannot extend
a provider/session limit or create a scheduler. Use native goal tools only on an explicit goal
request and preserve their lifecycle; never install a generic continuation hook to imitate them.

## Checkpoints and limits have different jobs

At a useful milestone or reassessment point, inspect what changed: requirements satisfied,
uncertainty resolved, a decisive experiment, or progress from an existing process. Record only the
delta and next action. Continue without renewed approval when work remains within the same authority.
Progress is not measured by lines changed or verbose output; a quiet test or difficult investigation
may still be healthy. Inspect its state before canceling or duplicating it.

An estimate or checkpoint is a cue to reassess, not an automatic stop. Repeated identical failures,
no new evidence, a changed dependency, or host pressure call for a revised approach or narrower lane.
Do useful independent work while waiting. If a genuine blocker requires new authority or external
change, report it with preserved evidence. Do not retry endlessly or fabricate a new requirement
after acceptance is met.

Explicit user/operator deadlines, spending caps, cancellation, and runtime limits remain binding.
Do not extend them silently. End an affected attempt truthfully and preserve a resumable handoff.
The optional CLI adapter has no default duration cutoff; its explicit `--timeout` is a hard limit,
not a heartbeat interval. Process ownership, cancellation, output bounds, and honest evidence still
apply. Omission of a timeout requires supervision; it is not permission for an orphaned process.

## Keep prompts useful

Keep activation descriptions short and specific. Load only the reference needed for the current
decision. Supply acceptance criteria and meaningful constraints, allowing the selected model to
choose incidental implementation steps. Avoid mandatory fleet sizes, repeated whole-repository
reading, phase-by-phase permission rituals, or fixed test counts. Make inter-agent packets and
user updates concise; retain artifact pointers instead of duplicating logs or full documents.

At compaction or handoff, preserve decisions, open criteria, changed paths, current evidence, live
handles, and the next action. Retrieve older details when needed. In native Codex, use its context
management; do not recreate API compaction in the skill. An application-owned Responses controller
must follow the documented conversation-state and compaction protocol for its selected model.

Tune only a demonstrated failure: premature handoff, redundant testing, wrong routing, stale context,
or duplicated work. Compare previous/revised/no-skill behavior on the same acceptance contracts;
change one variable for causal comparisons. Keep genuine safety boundaries and remove redundant
instructions. Structural tests prove implementation properties, not faster or cheaper engineering.

## Research basis

- [Astra prompting](https://developers.openai.com/api/docs/guides/latest-model): explicitly encourage
  follow-through, useful delegation, proportionate verification, and clear instruction precedence.
- [Rethinking skills and prompts for Astra](https://learn.chatgpt.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
  (September 11): shorten descriptions, route to relevant references, and reconsider unnecessary
  pauses and procedures. This supports the compact core, not removal of required acceptance checks.
- [Codex long-running work](https://learn.chatgpt.com/docs/long-running-work): define verifiable
  outcomes, steer the same coherent task, and preserve access boundaries. Goals do not grant access.
- [Codex best practices](https://learn.chatgpt.com/guides/best-practices): relevant context, practical
  repository guidance, living plans when useful, and native context management.
- [Multi-hour execution plans](https://developers.openai.com/cookbook/articles/codex_exec_plans):
  historical evidence for sustained milestone-based work. Its older model recommendation and long
  template are not the current model policy or a mandatory document for every task.
- [Responses compaction](https://developers.openai.com/api/docs/guides/compaction): supports ongoing
  interactions through reduced context while retaining state; it is not task completion.

No source establishes an optimal fleet size, universal duration limit, or measured speedup for this
skill. Validate those hypotheses against comparable accepted outcomes in subsequent runs.
