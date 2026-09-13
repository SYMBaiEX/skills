---
name: gpt-orchestration-build
description: "Implement an existing audit, issue set, review, or failing-test report through verified code. Use when the user asks to build from findings or remediate a known backlog without repeating broad discovery."
license: MIT
metadata:
  author: SYMBaiEX
  version: "2.1.0"
---

# GPT Orchestration Build

Use installed GPT Engineer for the shared engineering contract. This wrapper adds findings-driven
execution, not a separate model policy. Installation does not resolve a core dependency or register
profiles/hooks. If the core is unavailable, preserve the current parent and apply the bounded
workflow below directly.

Respect the selected `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, or `gpt-5.6-luna`
parent. A fleet is optional. Request useful same-model children explicitly, or select a mixed-model
policy with exact routes and reasons. Never silently substitute an older model or change provider.

Read repository instructions and current Git state; preserve user/concurrent edits. Carry prior
authorization within this task. Validate supplied findings against current source, tests and relevant
primary documentation. Track ID, root cause, impact, paths, dependencies, owner, acceptance and
disposition. Do not restart broad discovery unless the evidence is unusable.

Order confirmed changes by dependencies: shared contracts before dependent implementations, then
integration and final verification. Keep coupled edits together. Give disjoint parallel writers
isolated candidates and tell them they are not alone; never overlap shared file ownership.
Dispatch independent ready work while integrating completed lanes.

Implement each confirmed in-scope finding or name its concrete blocker. Mark invalid, duplicate and
already-satisfied items explicitly. Deferral needs authority. Review candidate changes and run
focused checks before dependent stages; use risk-appropriate integrated gates after the relevant
writes. A removed stub, build success, or agent summary does not prove the user flow.

Close with reconciled findings and pass/fail/skip/not-run evidence. Teardown task-owned agents,
processes, listeners, and candidates only; preserve shared MCP services and other tasks. Commit,
push, or deploy only when authorized. State release status and remaining required action.
