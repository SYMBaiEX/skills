# Legacy GPT-5.6 compatibility

Current routing and installation live in [codex-astra.md](codex-astra.md). GPT Engineer 2 defaults
to Astra. Terra/Luna remain explicit economy options; historical Sol and old Codex role records are
retained for audit comparisons, not default dispatch.

Some older runtimes cached Luna as Multi-Agent V1 while using V2 for other models. First use a
supported current runtime and the upstream catalog. Never copy or patch a catalog to enable Astra.

`scripts/configure_luna_v2.py` remains a compatibility/recovery tool. Disable a stale managed override
with `--disable` and restart Codex. Its `--apply --acknowledge-unsupported-catalog-override` path
requires explicit owner acceptance and a verified old Luna mismatch; it freezes upstream metadata
and is not routine setup. Prefer a supported native/SDK path or a recorded compatibility-adapter
attempt while an economy route is blocked. Do not rewrite models_cache.json in place or claim
effective execution from configuration alone.
