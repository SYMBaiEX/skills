---
name: symbaiex-claim-verification
description: Verify stored public claims against version-bound citations and inspect claim timelines. Use when checking support, contradiction, provenance, or supersession history.
license: MIT
compatibility: Requires a SYMBaiEX Ed25519 bearer with the evidence scope.
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX claim verification

1. Resolve the claim by its stable claim key through the published REST or MCP contract.
2. Call stored-claim verification to obtain the current public claim and its bounded citations.
3. Call the claim timeline endpoint when the user needs revision or supersession history.
4. Report the stored status exactly: supported, contradicted, unresolved, or outdated. Do not upgrade evidence strength in prose.
5. Cite the canonical public document and version identifiers returned by the API.
6. If the API omits a private, retired, or no-longer-public source, fail closed instead of reconstructing it from stale context.

This skill verifies records stored by SYMBaiEX; it does not prove that every possible external source has been considered.
