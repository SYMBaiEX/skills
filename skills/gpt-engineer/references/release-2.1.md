# GPT Engineer 2.1

Model-aware engineering, reviewed September 13, 2026. This release supports exactly
`gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna` as selected GPT parents.
It does not switch the parent or require a fleet. Spark and Claude remain explicit separate routes.

## Changes and migration

- Compact portable core and shorter audit/build/auto wrappers. Load model/runtime/engineering
  references on demand. Small fixes do not need an orchestration ceremony.
- Explicit same-model and mixed-model requests; unknown parent metadata does not guess a child.
  Keep requested controls separate from independently attributed effective child metadata.
- Optional route validation composes with normalized parent hook events. Subagent hook common
  model/session fields are not child attestation.
- Keep native delegation first. The guarded CLI adapter now accepts all four exact models with
  generic roles for actual compatibility gaps. Retain its tested isolation, scoped writes,
  locking, handoffs and process cleanup; a new SDK alone does not replace those guarantees.
- Remove Luna model-catalog creation/patching. The old configurator is recovery-only:
  inspect or disable the known legacy override while preserving unrelated settings/catalog files.
- Optional bootstrap uses ownership receipts, atomic writes, lifecycle locking, known-asset
  upgrades, and conservative removal. Customized files and symlinks are preserved or rejected.
  Codex project hooks require `--with-hooks`; profile upgrades do not re-enable disabled hooks.
  Claude core profile uninstall does not alter Claude settings/hooks.
- Bounded, stateless hook handlers; exact known duplicate registration migration; no generic
  continuation loops, transcript injection, or tests after every edit.
- Historical audits tolerate missing roles and distinguish asserted current policy from unknown
  historical installations. Structural validation no longer mandates particular policy wording;
  behavior is tested separately.
- Correct Claude documentation that treated the subagent-model environment default as a universal
  force override. Newer FORCE behavior is version-gated and is not enabled by this release.

## Evidence and limitations

Against v2.0.1, the core entrypoint shrank from 13,197 to 8,524 bytes (about 35%); its word count
fell from 1,753 to 1,098. The three orchestration entrypoints also became substantially smaller.
These are file measurements, not measured token billing or end-to-end speed gains.

Three fresh supplied-skill conditions (previous, revised, none) each completed four bounded cases:
one actual small fix and three decision exercises covering architecture/parallelism, changed-model
resumption, hooks/cleanup, and non-activation. All three fixes passed independent deterministic checks
and preserved an unrelated dirty file. The previous skill proposed Astra children for a Terra parent
without a mixed policy; revised and no-skill conditions preserved Terra. This is directional behavioral
evidence, not a statistical benchmark or proof the revised skill beats no skill generally.

The revised condition understood parent/child hook attribution more precisely than the no-supplied-skill
condition. All conditions preserved shared infrastructure and withheld completion on unknown external
results. Full dashboard implementation, live compaction/interruption, all four runtime/model combinations,
and trusted runtime hook invocation were not covered by the bounded model evaluation.

Hook fixtures measured 20 process starts each on macOS/Python 3.11.14: median roughly 16 ms,
maximum roughly 18 ms; context output 529 bytes, guard output 248 bytes. Filesystem was warm.
This includes Python startup and proves only synthetic handler behavior, not runtime invocation or benefit.
Unit/integration tests cover clean install, upgrade, preservation, deduplication, malformed inputs,
routing, isolated candidate guards, disable/uninstall, and journal/cache recovery.

Independent review identified three composition/lifecycle issues; fixes and regression tests were
reviewed again with no remaining release blocker. Effective model, tokens, elapsed time and billing
for fresh model evaluations were unavailable; no values were fabricated.

## Install or update

```bash
bunx skills@1.5.26 add SYMBaiEX/skills --skill gpt-engineer --agent codex claude-code --global --yes
bunx skills@1.5.26 update gpt-engineer --global --yes
```

Use `npx --yes skills@1.5.26` instead of `bunx` without Bun. Add named wrappers only when wanted.
Skills CLI installs portable skills; it does not register agent profiles, hooks, MCP tools, or plugins.
The core works without the Python adapter. See [runtime integrations](runtime-integrations.md) for
optional profile/hook setup, trust, diagnostics, upgrade, disable, and removal.

The new skill is available for subsequent activation. Restart/start a fresh task when the runtime
requires it to reload native agent profiles. New/changed hooks require normal user trust review;
do not bypass trust. Native direct selectors need no custom-profile install.

## Next evaluation

Measure matched task classes and unchanged acceptance contracts before increasing fleets. Record
skill hash, runtime version, requested/effective route provenance, dispatch/attempt/child/call IDs,
phase boundaries, accepted outcomes/rework and owned resource teardown. Separate elapsed time from
summed agent time, cached from uncached usage, and estimates from billing. Compare parent-only with
one or two independent lanes first; expand only when accepted throughput improves.

The [capability matrix](runtime-integrations.md) and [model-routing reference](model-routing.md)
link the official documentation used. Automatic startup/tool/stop hooks and companion plugins are
deferred until their benefit justifies their trust, maintenance, and context cost.
