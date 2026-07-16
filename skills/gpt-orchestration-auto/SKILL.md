---
name: gpt-orchestration-auto
description: Autonomously pursue a sustained engineering outcome through repeated research, planning, multi-agent implementation, integration, verification, and gap-closing cycles. Use when the user asks for a /goal-style run, says do not stop, finish the whole codebase, research and build autonomously, babysit an outcome, or wants the orchestrator to keep working across continuations until genuinely complete. Use native goal tracking when explicitly requested and available; otherwise maintain an equivalent goal ledger without inventing tool capabilities or broadening authority.
---

# GPT Orchestration Auto

Own a durable engineering outcome from uncertainty to verified completion. Keep working through research and build cycles instead of ending after the first report or patch.

## Establish the authority envelope

1. Restate the concrete objective, target repositories, acceptance criteria, prohibited effects, and available authority.
2. Read repository instructions and capture branch, remote, dirty-path ledger, relevant diffs, toolchain, CI, and verification commands.
3. Treat existing changes as user-owned. Never reset, checkout, stash, delete, or overwrite unrelated work.
4. Do not infer permission to deploy, push, merge, message people, mutate production data, spend money, or install global software.
5. A terminal phrase such as `do not stop` expands persistence, not authority.

## Use goal tracking honestly

If the runtime exposes native goal tools and the user explicitly requested a goal or autonomous sustained outcome, create or adopt one concrete objective. Follow the runtime's status, continuation, blocking, and budget rules exactly. Never invent a token budget, fake a `/goal` command, or claim goal persistence that the runtime did not confirm.

Otherwise maintain a goal ledger in the working plan containing:

- objective and acceptance tests;
- current cycle and phase;
- finding ledger;
- completed evidence;
- active owners and path scopes;
- blockers and attempted alternatives;
- next highest-leverage action.

Keep the ledger stable across continuations and context compaction. Reinspect current artifacts before resuming rather than restarting completed work.

## Run the autonomous loop

Repeat these phases until the acceptance criteria are met:

1. **Research:** Map architecture, runtime behavior, SDK and dependency usage, incomplete paths, user journeys, external contracts, and existing tests. Use primary sources for unstable claims.
2. **Synthesize:** Convert evidence into a deduplicated finding ledger. Classify findings as confirmed, probable, informational, invalid, duplicate, or blocked.
3. **Plan:** Order confirmed findings by dependency, risk, and user value. Reserve non-overlapping write scopes and independent verification.
4. **Build:** Assign bounded implementation waves. Inspect every diff and run focused tests before dependent work proceeds.
5. **Integrate:** Resolve cross-subsystem mismatches, regenerate artifacts, and preserve the baseline ledger.
6. **Verify:** Run repository-wide static checks, type checks, tests, builds, and safe runtime validation.
7. **Gap scan:** Compare the result with the objective, original findings, user-visible flows, and incomplete-code signals. Start another cycle for every remaining confirmed gap.

Do not stop after research when the objective includes building. Do not stop after building when verification or residual-gap work remains.

## Staff the fleet

Inspect the live agent tree and tool schema before choosing a topology. Count the orchestrator as a concurrency slot. Use later waves rather than oversubscribing the runtime.

- Use confirmed `sol_engineer` / `gpt-5.6` routing for ambiguous architecture, hard implementation, and integration.
- Use confirmed `terra_explorer` and `terra_worker` / `gpt-5.6-terra` routing for read-heavy research and bounded routine implementation.
- Use confirmed `luna_verifier` / `gpt-5.6-luna` routing for high-volume mechanical verification and residual scans.
- Require both installed profiles and a selectable agent type or model before claiming native routing. If native selection is unavailable and the sibling `gpt-engineer` skill is installed, use its guarded Codex CLI fallback for model-pinned delegates. Otherwise disclose same-model inheritance.
- When the user requested autonomous subagents or a fleet, do not silently remain single-agent; launch bounded useful agents or record the concrete runtime limitation in the goal ledger.
- Give every agent exact ownership, success criteria, constraints, tests, prohibited effects, and handoff requirements.
- Keep one writer per file or tightly coupled subsystem.
- Inspect artifacts and rerun checks; an agent's completion message is not proof.

## Maintain forward progress

Choose the next action by leverage: unblock critical dependencies, close user-facing paths, remove false completion signals, and strengthen verification before cosmetic cleanup. When an approach fails, diagnose it, try safe alternatives, and record the evidence.

Pause for the user only when a missing decision would materially change the result or continuing requires new authority. Treat missing credentials or external state as a reported verification boundary, not permission to fabricate success.

Use the runtime's native blocked status only under its stated threshold and semantics. Difficulty, uncertainty, slow progress, or a nearly exhausted budget are not blockers by themselves.

Do not install a generic `Stop` hook to force persistence. Such hooks can create unbounded continuation loops and cannot determine whether new user authority is required. Prefer native goal state or the explicit goal ledger above.

## Complete the goal

Finish only when:

- every acceptance criterion has evidence;
- every confirmed in-scope finding has a final disposition;
- focused and repository-wide gates have passed or are explicitly unavailable for a concrete external reason;
- the final diff matches the authority envelope and preserves user work;
- no safe, required, in-scope action remains.

Mark a native goal complete only after those conditions hold. Return the outcome, cycles completed, finding dispositions, verification matrix, external-only checks, residual risks, and exact next action if anything remains.
