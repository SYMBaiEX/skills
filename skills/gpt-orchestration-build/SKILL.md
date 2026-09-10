---
name: gpt-orchestration-build
description: Turn an existing audit, finding list, issue set, review, failing-test report, or implementation plan into completed, verified code through a coordinated agent fleet. Use when the user asks to build from findings, implement every audit item, finish a known backlog, remediate review results, or continue from research without repeating the whole investigation. Validate each finding, preserve repository state, assign non-overlapping writers, integrate in dependency order, and track every item to an explicit disposition.
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.0.0"
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

Use the runtime's available concurrency and include the orchestrator in the resource budget. Give one writer ownership of each file or tightly coupled subsystem. Read the installed `gpt-engineer` skill and follow its routing contract; do not duplicate a conflicting wrapper policy or assume profiles were installed.

Without the core skill, request `gpt-6-astra` for the parent and every child: `astra_engineer` at `high`, and `astra_worker`, `astra_explorer`, and `astra_verifier` at `medium`. Terra/Luna economy lanes require explicit opt-in; Sol is retired. Prefer native exact profiles or direct model selection before Python helpers. Use the official Codex SDK or feature-detected app-server APIs for programmatic control; use the core skill's guarded CLI adapter only when needed. Record requested model/effort and effective metadata separately, marking attestation unavailable when not exposed. Never silently substitute an older model; if exact selection is unavailable, report it and continue only with a suitable available parent or seek direction.

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

After all waves, run checks selected by the changed behavior and acceptance criteria:

- regenerate code only when its source schema changed and regenerate lockfiles only when dependency inputs changed;
- always run diff hygiene plus the focused lint, static analysis, type checks, tests, build, or runtime checks that cover the affected system;
- reserve repository-wide gates and production builds for cross-cutting changes, broad completion claims, or explicit acceptance criteria;
- exercise the affected user path against a verified local or disposable target;
- inspect scripts before running them and never let a smoke command default to production;
- run a residual search for the original findings and incomplete-code markers;
- compare the final worktree with the captured baseline.

Keep credentialed, destructive, deployment, messaging, merge, and push actions outside scope unless the user separately authorized them.

## Tear down the build fleet

After accepting the last implementation result, wait for every required handoff and inspect the live agent tree. Interrupt superseded or stale agents, then verify that no bounded worker remains active.

Track every background process or temporary resource launched by the fleet. Preserve evidence, then stop and reap task-owned subprocess groups, watchers, servers, and listeners and remove task-owned temporary worktrees unless the user explicitly requested continued runtime. Classify ownership using agent state, parent process, working directory, launch time, and recorded PID or resource identifier. Never kill by process name alone, and never terminate shared MCP services, the host application, another task's cohort, or an unclassified process. Report host-retained helpers when the runtime provides no safe task-scoped teardown.

## Close the ledger

Return the outcome first, followed by the finding ledger disposition summary, changed subsystems, verification matrix, fleet teardown result, preserved user work, and exact blockers. Claim completion only when every confirmed finding has an acceptance result, no required build work remains, and task-owned resources have been reclaimed or explicitly retained.
