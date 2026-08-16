# Memory workflow

## Purpose

Use prior session evidence to reduce rediscovery while preventing stale state, excessive context,
or hidden side effects from controlling an engineering task.

## Supported backends

### Claude Mem MCP

Prefer the installed `mcp-search` server. Its useful read-only surface is:

- `search`: broad ranked lookup;
- `timeline`: chronological context around a selected result;
- `get_observations`: batch-fetch full selected records;
- `session_start_context`: bounded project context, at most once per task;
- `smart_search`, `smart_outline`, `smart_unfold`: optional code navigation;
- `list_corpora`: inventory only.

Corpus build, prime, rebuild, and reprime operations persist state and may invoke configured model
providers. They are outside the default workflow.

### Codex memory files

When MCP retrieval is unavailable, use the Codex memory hierarchy without scanning it wholesale:

1. Search `~/.codex/memories/MEMORY.md` for project path and task keywords.
2. Follow at most one or two directly referenced rollout summaries or memory skills.
3. Read only the line ranges needed to recover evidence.
4. Use the required Codex memory citation block when the runtime requires it.

Do not present memory-derived facts as current without verification.

## Query protocol

1. Anchor the query with the canonical repository path or recognized project name.
2. Add stable identifiers: feature, SDK, error string, function, issue, PR, or deployment target.
3. Search broadly but return no more than 20 candidates.
4. Use timeline context around only the strongest candidates.
5. Batch-fetch 3–8 observations once.
6. Stop retrieving when the next engineering action is supported. More history is not automatically
   better evidence.

For each selected observation record:

- source/backend and stable ID;
- timestamp and project identity;
- the specific claim it supports;
- whether it describes intent, implementation, verification, or external state;
- what current evidence can confirm it;
- sensitivity and whether it is safe to delegate.

## Freshness rules

- Git paths, branches, commits, dependencies, model catalogs, docs, pricing, APIs, deployments,
  reviews, CI, secrets, and running processes are drift-prone. Verify them live.
- Architectural rationale and explicit user preferences drift less, but compare them with current
  repository instructions and the present request.
- A historical test or health receipt proves only that earlier state.
- A recalled model string does not prove that model actually ran or incurred usage.
- A current contradiction wins. Preserve the contradiction in the finding ledger.

## Privacy and authorization

Memory can contain prompts, source code, filesystem paths, credentials-adjacent text, customer data,
and unrelated conversations. Minimize retrieval and redact before delegation. Never print tokens or
secret values. Historical authorization does not carry into the current task.

Cloud sync can transmit narratives and prompt text to an external service when a user has enabled
it. This skill neither enables nor configures sync and does not infer privacy from local-worker
health.

## Runtime diagnosis boundary

The read-only preflight may examine:

- active version and worker path;
- health/readiness, MCP manifests, worker toggle status, and client registrations;
- queue depth and provider/dependency signals;
- database/WAL size and immutable main-database snapshot counts;
- sync outbox totals grouped by operation.

Claude Mem 13.15.0's worker endpoint can report MCP disabled when a packaged client stores
`.mcp.json` at the plugin root instead of `plugin/.mcp.json`. Treat that as a layout-specific toggle,
not connection proof. Prefer the effective registration derived from the active manifest and the
enabled Codex/Claude plugin entries; a newly installed MCP still requires a client restart and a new
task before its tools appear.

Do not administer the worker automatically. If health and queue signals disagree, or storage/outbox
growth appears abnormal, continue engineering without memory and report a separate operational
finding. Cleanup requires its own scope, worker shutdown, and a verified database backup.

## Child handoff packet

```text
Task:
Owned paths:
Current acceptance:
Verified prior facts (ID + one sentence):
Stale/contradicted facts to avoid:
Relevant current code/docs:
Expected output:
Cleanup responsibility:
```

Keep raw observation bodies in the parent unless a child truly needs them.
