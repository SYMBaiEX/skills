---
name: symbaiex-research-jobs
description: Create and monitor bounded asynchronous research or JSONL export jobs. Use when a request needs a cited digest or downloadable public-data artifact rather than one synchronous lookup.
license: MIT
compatibility: Requires a SYMBaiEX Ed25519 bearer with the evidence scope and durable idempotency keys.
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX research jobs

1. Confirm that a synchronous evidence or universal search is insufficient.
2. Create a research or export job with a unique, durable `Idempotency-Key` and bounded input from the OpenAPI schema.
3. Persist the returned job identifier and poll the owner-scoped status endpoint at a restrained cadence.
4. Treat deterministic extractive fallback as a valid, explicitly labeled outcome when model routing is unavailable.
5. Download completed artifacts only through the first-party authenticated stream and resend the bearer for that request.
6. Verify artifact metadata, keep the 24-hour retention window in mind, and do not expose storage identifiers or tokens.

Exports are JSONL and bounded to public records. Payment and premium access are not enabled.
