---
name: gpt-orchestration-build
description: Turn an existing audit, finding list, issue set, review, failing-test report, or implementation plan into completed, verified code through a coordinated agent fleet. Use when the user asks to build from findings, implement every audit item, finish a known backlog, remediate review results, or continue from research without repeating the whole investigation. Validate each finding, preserve repository state, assign non-overlapping writers, integrate in dependency order, and track every item to an explicit disposition.
---

# GPT Orchestration Build

Convert findings into working software. Own the implementation result; do not merely redistribute the list or return another plan.

## Establish the build contract

1. Read repository instructions and capture the branch, dirty-path ledger, relevant diffs, manifests, and available verification commands.
2. Confirm that the user authorized implementation. Treat review-only or audit-only requests as read-only.
3. Gather all supplied findings from the conversation, reports, plans, issues, test output, and working tree.
4. Normalize them into a finding ledger with:
   - stable identifier and concise outcome;
   - evidence and affected paths;
   - confidence, severity, and user impact;
   - prerequisites and conflicts;
   - owner and write scope;
   - acceptance test;
   - final disposition.
5. Preserve pre-existing user changes. Never reset, checkout, stash, or overwrite unrelated work.

## Validate before writing

Trace each finding to current repository truth. Mark it `confirmed`, `already satisfied`, `duplicate`, `invalid`, or `blocked`. Do not implement stale advice blindly. Research only the gaps needed to make a safe build decision; avoid restarting a broad audit unless the findings are unusable.

If current APIs, dependencies, standards, or security guidance affect the implementation, verify them with primary sources. Adapt the result to the repository's actual stack.

## Plan implementation waves

Order confirmed work by dependency and blast radius:

1. contracts, schemas, and shared types;
2. core services and persistence boundaries;
3. SDKs, adapters, and integration seams;
4. product routes and user-facing behavior;
5. cleanup, documentation, and generated artifacts;
6. independent verification and residual-gap scan.

Use the runtime's available concurrency, counting the orchestrator as a slot. Give one writer ownership of each file or tightly coupled subsystem. When confirmed Codex custom agents are installed and selectable, use `sol_engineer` (`gpt-5.6`) for hard integration, `terra_worker` (`gpt-5.6-terra`) for bounded implementation, `terra_explorer` for read-heavy gaps, and `luna_verifier` (`gpt-5.6-luna`) for high-volume mechanical checks. If the native spawn schema cannot select a model and the sibling `gpt-engineer` skill is installed, use its guarded CLI runner for model-pinned delegates. Otherwise disclose the limitation. When the user asked for a fleet, do not silently complete the task with only the parent agent.

Every writer contract must include exact paths, success criteria, prohibited side effects, required tests, baseline constraints, and expected handoff evidence. Keep overlapping work read-only.

## Build every confirmed finding

For each wave:

1. Assign non-overlapping changes.
2. Continue useful integration work while agents run.
3. Inspect every returned diff rather than trusting the summary.
4. Reject scope drift, placeholder replacements, silent fallbacks, and unverified completion claims.
5. Run focused tests before dependent work begins.
6. Update the finding ledger immediately.

Do not drop difficult items. A confirmed in-scope finding must end as implemented or blocked by a concrete missing authority, credential, external dependency, or mutually exclusive user decision. Do not use `deferred` unless the user explicitly accepts deferral.

## Integrate and prove the result

After all waves:

- regenerate code and lockfiles with the repository's pinned toolchain;
- run diff hygiene, lint or static analysis, type checking, tests, and production build as applicable;
- exercise the affected user path against a verified local or disposable target;
- inspect scripts before running them and never let a smoke command default to production;
- run a residual search for the original findings and incomplete-code markers;
- compare the final worktree with the captured baseline.

Keep credentialed, destructive, deployment, messaging, merge, and push actions outside scope unless the user separately authorized them.

## Close the ledger

Return the outcome first, followed by the finding ledger disposition summary, changed subsystems, verification matrix, preserved user work, and exact blockers. Claim completion only when every confirmed finding has an acceptance result and no required build work remains.
