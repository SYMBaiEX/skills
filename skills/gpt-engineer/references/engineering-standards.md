# Engineering standards

Read this reference for Broad or Team work, release-readiness claims, or a change that touches a
high-consequence boundary. The goal is a consistent definition of done without forcing every
repository into one stack or loading a universal checklist into every child.

## Build the standard in three layers

1. **Repository-derived contract:** read applicable `AGENTS.md` and override files, manifests,
   package scripts, CI workflows, generated-code rules, ownership files, release docs, runbooks,
   migrations, and existing test conventions. Inspect what commands actually execute.
2. **Universal invariants:** preserve user work; trace requirements to evidence; fit the existing
   architecture; handle relevant failure paths; add the narrowest regression proof; review the
   integrated diff; and give documentation an explicit disposition.
3. **Conditional gates:** activate only the gates implied by the impact map below. A gate that is
   irrelevant is `not_applicable` with one short reason, not silently omitted.

Closer repository instructions override broader preferences. They may strengthen the baseline but
cannot redefine a required skip, missing environment, or untested production-only behavior as a
pass.

## Create the impact map once

For non-trivial work, assign requirement IDs and mark which boundaries may change:

- execution path or public behavior;
- persisted data, schema, migration, or transaction semantics;
- API, event, file-format, CLI, or backward-compatibility contract;
- authentication, authorization, secrets, privacy, payments, or untrusted input;
- external SDK, dependency, generated client, lockfile, or runtime version;
- user journey, accessibility, responsive layout, or failure-state UX;
- latency, throughput, memory, concurrency, availability, or resource budgets;
- logs, metrics, traces, alerts, supportability, deployment, rollback, or operator workflow;
- public documentation, configuration, changelog, migration guide, or runbook.

The lead selects gates from this map and sends children only the relevant requirement and gate IDs.
Do not paste this reference into every prompt.

## Universal definition of done

Every implemented requirement needs:

- an evidence-backed final disposition;
- the smallest complete design consistent with current architecture and supported platforms;
- proportionate verification at the lowest meaningful layer, with regression tests when behavior warrants them;
- inspected success, error, empty, retry, cancellation, and concurrency behavior when relevant;
- integrated-diff review that includes user-owned changes in the chosen review scope;
- passed, failed, skipped, and not-run results reported separately;
- a documentation disposition: `updated`, `not_applicable`, or `blocked`;
- no unresolved incomplete marker, roadmap promise, audit finding, or user-visible placeholder within
  the authorized scope.

A command name is not evidence. Inspect aliases and workflow conditions. A typecheck labeled `lint`
does not prove linting; a zero exit code with required integration cases skipped does not prove the
integration; a build does not prove a user journey.

For a later delta-only cycle, reuse a prior command result only when `scripts/cache_gates.py` proves
that repository content, command truth, normalized argv, scope, allowlisted environment, and the
complete successful result still match. Any timeout, truncation, skip, failure, corruption, or
unknown/global scope is a cache miss. Path-scoped invalidation may spare unrelated focused gates;
the applicable final broad gate still runs after integration.

## Conditional quality gates

| Gate | Activate when | Required proof |
| --- | --- | --- |
| Correctness and compatibility | Behavior, API, concurrency, retry, or version contracts change | Representative success and failure cases, compatibility decision, regression test, and relevant race/idempotency evidence |
| Security and privacy | A trust boundary, identity, secret, permission, payment, personal data, untrusted input, or privileged integration changes | Boundary and abuse/failure case, mitigation, targeted test or scan, dependency impact, and unresolved risk |
| SDK and dependencies | An external API, SDK, dependency, generated client, runtime, or lockfile changes | Current primary documentation, official-SDK-versus-custom decision, supported version, lockfile/generated-file effect, integration proof, and deprecation/security review |
| Data and migration | Persisted schema, indexes, data meaning, or transactional behavior changes | Forward path, compatibility/backfill, idempotence, representative dry run or migration test, restore/rollback boundary, and production authorization status |
| User experience | A visible flow or interaction changes | Real rendered/runtime journey at relevant viewport and state, loading/empty/error behavior, keyboard/accessibility evidence, and screenshot or reproduction evidence when useful |
| Performance and reliability | Hot paths, scale, availability, concurrency, queues, or resource use can change | Existing budget or explicitly stated baseline, bounded representative measurement, failure/timeout behavior, and capacity conclusion; do not invent an SLO |
| Operability and release | Production runtime, deployment, background jobs, integrations, or support workflows change | Detection signal, actionable logs/metrics/traces where the repository supports them, configuration and secret handling, rollout/rollback or feature-flag plan, smoke/canary evidence, and external authorization status |
| Documentation | Public behavior, API, configuration, migration, or operator workflow changes | Updated canonical documentation/changelog/runbook or a concrete `not_applicable` reason |

Never manufacture a tool, test type, SLO, deployment policy, or documentation location that the
repository does not support. When a necessary harness is missing, either add it within scope or mark
the gate blocked/not run and explain what would be needed.

## Logical engineering-team lanes

These are optional task lenses, not a requirement to spawn a team. One Astra agent can cover several
lenses coherently. Delegate only independent work that reduces elapsed time or adds useful review:

| Logical lane | Normal route | Output |
| --- | --- | --- |
| Requirements and product completeness | Lead or `astra_explorer` | Requirement map, incomplete journeys, stale promises, acceptance gaps |
| Architecture and boundaries | Lead or `astra_engineer` | Execution/data/API map, coupling and migration risks, decision options |
| Correctness and compatibility | Lead or `astra_verifier` | Concrete defects, races, error paths, compatibility and regression risks |
| Security and privacy | Lead or `astra_engineer` | Trust boundaries, abuse cases, auth/data/supply-chain findings, required proof |
| SDKs, dependencies, and deprecations | Lead or `astra_explorer` | Primary-source version/API evidence, official SDK opportunities, drift and lockfile impact |
| Tests and user journeys | Lead or `astra_verifier` | Gate inventory, actual pass/fail/skip counts, missing layers, runtime/browser evidence |
| Performance, reliability, and observability | Lead or a bounded Astra lane | Baselines, hot paths, capacity/failure evidence, missing operational signals |
| Operations, release, and documentation | Lead or `astra_explorer` | CI/CD truth, configuration, rollback/canary/runbook and documentation dispositions |

Combine lanes when the repository is small. Split them by subsystem when the codebase is large. The
lead deduplicates findings before any build wave and keeps architecture, security acceptance,
integration, and final completion judgment accountable to the Astra lead. Explicit economy mode may
route bounded task lenses to the retained Terra/Luna profiles; it does not transfer final acceptance.

## Qualify an eight-reader Team wave

Broad remains the default six-reader ceiling. Use Team mode only when:

- at least seven bounded read-only lanes are independently ready;
- every lane unblocks a named downstream decision and has non-overlapping evidence ownership;
- exact selected-suite route attestation passes;
- the host shows no resource pressure and the previous comparable wave did not show high failure;
- the wave is a discovery or post-integration review barrier, never a shared-write wave;
- a paired comparison will measure accepted findings, wall time, failures, context, and rework.

Attest those conditions separately with `--team-qualified --routes-attested
--lanes-independent --paired-comparison`. The planner rejects Team under resource pressure, a prior
failure rate of 20% or higher, fewer than seven ready reads, or live capacity below seven; re-plan in
Broad rather than labeling a shrunken wave Team.

If Team mode adds duplicate findings, queueing, command contention, or synthesis cost without a
measured quality or latency gain, return to Broad. Available slots are not a reason to fill them.

## Evidence semantics

- `passed`: the required behavior ran and its result was inspected.
- `failed`: it ran and did not meet the criterion.
- `skipped`: the enclosing command ran but one or more relevant cases did not.
- `not_run`: it did not execute, including missing secrets, environment, service, device, or harness.
- `not_applicable`: the impact map proves the gate does not apply.
- `blocked`: required proof needs new authority or an external state change.

Record skip counts even when the enclosing command exits zero. Production readiness cannot be
inferred from local substitutes, source-string tests, a healthy build, or an unauthenticated smoke
when the requirement is an authenticated or production-only journey.

## Improve the engineer with evidence

Mine representative completed and failed runs into a small regression set. Compare prompt, routing,
effort, and fleet changes against task completion, requirement coverage, accepted findings, user
corrections, wall time, retries, compactions, tokens, and post-change defects. Use trace grading when
an SDK workflow exposes end-to-end traces; otherwise retain the same criteria in the local run
ledger. Change defaults only when repeated evaluations show a benefit.

## Official sources

- Astra model and prompt guidance: https://developers.openai.com/api/docs/guides/latest-model
- Codex subagents and custom agents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex instruction layering: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex code review: https://learn.chatgpt.com/docs/code-review
- Evaluation best practices: https://developers.openai.com/api/docs/guides/evaluation-best-practices
- Agent workflow evaluation: https://developers.openai.com/api/docs/guides/agent-evals
