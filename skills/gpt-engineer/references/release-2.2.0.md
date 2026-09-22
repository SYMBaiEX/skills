# GPT Engineer 2.2.0

Released September 22, 2026.

## GPT-6 routing

- GPT-6 Astra is parent/orchestrator-only. The skill no longer ships Astra worker, explorer,
  verifier, or engineer profiles and refuses Astra as a child route.
- GPT-6 Sol and GPT-6 Luna are the only bundled child model routes. Sol profiles target demanding,
  ambiguous work; Luna profiles target focused, repeatable work.
- Sol/Luna parents default to explicit same-model children. Astra parents explicitly route to Sol or
  Luna; cross-routing between Sol and Luna requires a deliberate mixed-model policy.
- Existing GPT-5.6 parent sessions are preserved during rollout, but no new GPT-5.6 child routes are
  created. Old route records remain classifiable as history; timestamps do not prove which skill
  version a live task loaded.

## Safe local migration

The optional Codex bootstrap backs up then retires only exact, previously shipped GPT Engineer
Astra-child and GPT-5.6 child profile files. Customized or unknown profiles are preserved for manual
review, not made valid dispatch targets. The project hook matcher now applies only to the new GPT-6
Sol/Luna profile IDs. No account model, permission, service tier, or model catalog setting is
changed.

## Official guidance

The routing starting point follows the [Codex models](https://learn.chatgpt.com/docs/models) and
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) documentation:
Sol for complex coding/agentic workflows, Luna for focused/repeatable tasks, and child models need
to be explicit when they should not inherit the parent. The Astra parent-only rule is a GPT Engineer
policy requested by the user, not a platform limitation. See OpenAI's
[GPT-6 launch](https://openai.com/index/introducing-gpt-6-sol-and-luna/) and the API pages for
[Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) and
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).

Validation policy for this release: no local test suite was run as part of the requested update.
The release does not claim runtime route attestation or performance gains.
