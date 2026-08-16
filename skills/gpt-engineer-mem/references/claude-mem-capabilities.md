# Claude Mem capability review

Claude Mem 13.15.0 exposes 19 bundled skills. This matrix records what GPT Engineer Mem adopts and
what remains an explicit, separate workflow.

| Claude Mem skill | Useful idea | GPT Engineer Mem decision |
|---|---|---|
| `mem-search` | Search, contextualize, then batch-fetch | Core bounded retrieval protocol |
| `smart-explore` | Index before payload | Use when available; fall back to `rg` and targeted reads |
| `make-plan` | Documentation-first evidence and anti-pattern checks | Adopt with current primary sources |
| `do` | Phase acceptance and review gates | Adopt; reject fixed fleets and automatic per-phase pushes |
| `pathfinder` | File/symbol evidence and flow mapping | Use selectively for architecture-heavy work |
| `oh-my-issues` | Cluster symptoms by root cause | Adopt analysis; issue mutations still need authority |
| `babysit` | Durable terminal conditions and a fresh final sweep | Adopt for explicitly authorized PR monitoring |
| `standup` | Read-only branch/worktree reconciliation | Adopt concept; use native agent handoffs, not a shared room file |
| `weekly-digests` | Bounded carry-forward between dependent phases | Adopt compact checkpoints only |
| `design-is` | Evidence before judgment and known-gaps fields | Use only for design review, not every task |
| `version-bump` | Manifest coverage and clean release state | Use repository-specific release conventions |
| `how-it-works` | Automatic capture and later retrieval | Treat runtime claims as version-specific; cloud sync is separate |
| `cloud-sync` | Secret-safe status verification | Do not enable, configure, or restart implicitly |
| `mode-creator` | Approval, dry-run, backups, atomic configuration | Keep separate; no settings or Telegram mutation |
| `knowledge-agent` | Focused persistent corpora | Opt-in only after privacy and lifecycle approval |
| `timeline-report` | Provenance and size confirmation | No full timeline by default; approve over 100k tokens |
| `learn-codebase` | Exhaustive source reading | Explicitly rejected as a default; use targeted exploration |
| `what-the` | Plain-language explanation | Tone guidance only |
| `wowerpoint` | Long-running artifact generation contract | Separate external upload/auth workflow |

## Integration principles

1. Memory is read-only and optional in the default path.
2. The current system is the source of truth.
3. Retrieval is bounded and project-scoped.
4. Sensitive history stays with the accountable parent unless strictly needed.
5. Memory service administration and external side effects require separate authority.
6. Engineering verification and task-owned teardown remain mandatory even when history is useful.
