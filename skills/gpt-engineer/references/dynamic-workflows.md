# Dynamic engineering workflows

Start with direct Astra execution. Add independent children only when their work shortens the
critical path or adds useful review. A large task or a strong model alone does not decide topology.

## Choose the runtime by the work it must do

| Surface | Appropriate use | Operational boundary |
| --- | --- | --- |
| Native Codex collaboration | Interactive engineering with a supervising lead | Live model/effort/capacity/permission schema governs; own child handles and compact handoffs |
| Official Codex SDK / app-server | Local programmatic coding, thread resume, custom UI, and per-thread configuration | Prefer SDK; app-server protocols may need version pinning and feature detection; application owns release and isolation |
| Agents API | Managed Codex harness for durable application sessions, orchestration, compaction and recovery | Public beta; currently US residency and not ZDR; subagents share environment filesystem, inherit MCP permissions, and do not support function tools |
| Responses Multi-agent | Model-managed independent fan-out in an API application | Children share request model/tools; no Codex worktree isolation; app executes function calls from every agent |
| Agents SDK | An application-owned orchestration loop with typed tools/handoffs/tracing | Application owns execution, state, deployment and lifecycle; distinct from managed Agents API |
| CLI compatibility adapter | Existing headless/isolation or cross-provider compatibility gaps | Recorded reason, bounded processes, candidate writes and evidence; native/SDK first |
| Spark or Claude skills | User-selected provider/model workflows | Preserve their explicit routing and keep one accountable outer owner |

Codex SDK is local coding automation; Agents API is a managed harness; Responses is lower-level
model control. Do not rebuild the normal Codex loop merely to gain another wrapper. `codex mcp-server`
is deprecated; prefer current Codex SDK/app-server integration for new controllers.

## Execute a dependency graph without global waiting

Give each stage an ID, objective, owned paths, authority, prerequisites, accepted output, route,
attempt, and cancellation condition. Launch all useful independent ready stages within capacity,
then continue useful lead work. Validate results as they arrive and unlock only stages whose
prerequisites are satisfied. An unrelated slow reader need not block a ready independent branch.

Keep explicit integration barriers for shared files, dependent writes and final acceptance. Reject
cycles, missing prerequisites, conflicting writers and stale evidence. Cancel downstream work when
a prerequisite is invalidated. Reuse related child context with a compact delta; use a fresh child
when earlier context is irrelevant. Nested delegation stays inside the same root capacity/ownership
budget and needs a specific benefit.

For durable or multi-wave work, use [run-journal.md](run-journal.md) to persist the resolved graph,
attempts and evidence. The lead is the logical writer. The journal does not schedule work or replace
native conversation history. Resumption must reconcile existing handles and side effects before
redispatch, and every started journal must close truthfully.

## Size optional parallel work

The planner retains conservative ceilings: Fast 1, Standard 3, Broad reads 6. Team permits 7/8 reads
only for an explicitly qualified experiment with enough independent work, route attestation, no
host pressure, and a comparable outcome plan. These are local policy ceilings, not OpenAI claims of
optimal capacity. Always clamp them to the runtime's actual limit. Shared checkout writes stay at
one; two isolated writers need disjoint candidate paths, with at most two supporting readers.

```bash
python3 scripts/plan_fleet.py --mode team \
  --team-qualified --routes-attested --lanes-independent --paired-comparison \
  --runtime-child-cap 8 --ready-reads 8 --ready-writers 0 --json
```

Team rejects missing admission criteria, resource pressure, high prior failures, insufficient ready
work or capacity, and writers. Re-plan in Broad when it is not justified. Default route evidence
requirements remain as described in the main skill; Team is the stricter experiment. More model
capacity does not justify more agents, and no mode requires filling all slots.

## Astra features for API controllers

These are implementation choices for an actual API application. Feature-detect them; do not add API
fields to Codex tools or claim a local skill enabled server features.

- **Async tools:** `async: true` applies to application-run function/custom tools. Start each job
  once, retain its original `call_id` and unique task handle, and return results to those calls.
  The app owns pending work, cancellation and recovery. Async does not apply to hosted tools or
  Programmatic Tool Calling; in Responses Multi-agent, do not combine it with parallel tool calls.
- **Steering:** Astra WebSocket steering queues additional input into a continuation. Acceptance
  does not undo started actions. Reconcile accepted input and pending tools on reconnect; do not
  resend accepted steering or launch duplicate work. Preserve the continuing user goal.
- **Reasoning changes:** `configuration_update` preserves cache while changing effort only in
  Astra standard single-agent Responses. Keep request-level effort unchanged, avoid adjacent
  updates, and do not combine with automatic compaction/truncation or `/responses/compact`.
  Explicit `compaction_trigger` is supported; reapply effort afterward. The response's reported
  request-level effort does not attest the active update.
- **Responses migration:** tool calling requires Responses. Remove temperature, top_p and
  top_logprobs; also Chat Completions logprobs and Responses output-logprobs include. Replace
  none/minimal with low. EU data residency excludes Astra Fast/priority processing.
- **Caching:** preserve stable message/tool prefixes and append deltas; avoid gratuitous schema,
  tool ordering or prompt rewrites. GPT-5.6+ supports `prompt_cache_options.ttl: "30m"` and explicit
  cache boundaries. Cache writes and reads have distinct billing; a high hit rate alone is not
  task efficiency. Use current diagnostics when API cache misses are a measured bottleneck.
- **Safeguards:** surface actual safety/approval interruptions as their own outcomes, preserve
  completed evidence, and follow the runtime's review path. Do not retry a denied action as a
  different model or classify a review stop as an ordinary transient error.

Responses Multi-agent defaults to three concurrent descendants across the tree, excluding the root;
Agents API's separate default is six. Do not transfer one runtime's limits to another. Responses
hosted collaboration actions are server-managed, while application function calls remain yours.
WebSocket result injection needs accepted/failed/completed-race handling. API mode does not isolate
repository writers, and HTTP continuation does not promise early per-agent delivery.

Programmatic Tool Calling is useful for bounded joining, filtering and aggregation when supported.
Its JavaScript has no direct host access but may call eligible mutation tools; keep tool authority
consistent with the task. It is not a substitute for the required ownership and integration checks.

## Verification and teardown

Keep one owner and process handle for long commands. A client wait timeout is not command failure.
Inspect the existing process/output before retrying; use bounded retries for classified transient
errors and honor Retry-After. Run focused checks during writes and the required integrated checks
after relevant writes finish. Later changes invalidate affected evidence rather than restarting all
discovery.

Native children return handoffs and terminal metadata; compatibility adapters additionally return
result.json and candidate bundles. Managed API sessions, turns and jobs have their own lifecycle.
Record the real identifiers and truthful results for the chosen surface. Close task-owned work and
the journal; preserve unrelated shared services. Use [fleet-observability.md](fleet-observability.md)
to compare accepted results, time, rework and usage with the historical baseline.

## Official sources

- [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [Runtime comparison](https://developers.openai.com/api/docs/guides/agents#compare-agent-runtimes)
- [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview)
- [Agents API multi-agent](https://developers.openai.com/api/docs/guides/agents-api/multi-agent)
- [Responses multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent)
- [Async tool calling](https://developers.openai.com/api/docs/guides/async-tool-calling)
- [Steering](https://developers.openai.com/api/docs/guides/steering)
- [Reasoning updates](https://developers.openai.com/api/docs/guides/reasoning#change-reasoning-mid-conversation)
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Misalignment monitoring](https://developers.openai.com/api/docs/guides/safety-checks/misalignment-monitoring)
