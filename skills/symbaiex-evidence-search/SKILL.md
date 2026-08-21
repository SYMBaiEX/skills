---
name: symbaiex-evidence-search
description: Search current public SYMBaiEX evidence and editorial records through bounded REST or MCP operations. Use for source discovery, public document lookup, and lexical or feature-gated semantic retrieval.
license: MIT
compatibility: Requires a SYMBaiEX Ed25519 bearer with the evidence scope.
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX evidence search

1. Read `https://www.symbaiex.com/api/agent/openapi.json` before constructing requests.
2. Authenticate with an enrolled Ed25519 identity granted the `evidence` scope.
3. Use `GET /api/agent/v1/universal-search?q=...` for bounded lexical, entity, citation, and editorial federation.
4. Use `GET /api/agent/v1/semantic-search?q=...&limit=...` only with a durable `Idempotency-Key`. Treat lexical-only fallback as a valid response.
5. Preserve canonical URLs, source identifiers, timestamps, visibility, and rank explanations in the result.
6. Never infer private records from missing public results or send the bearer to another origin.

Use source registry metadata to understand collection bounds and terms. Do not represent SYMBaiEX as a general-purpose web search engine.
