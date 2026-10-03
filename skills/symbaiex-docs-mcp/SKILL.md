---
name: symbaiex-docs-mcp
description: Find and read public SYMBaiEX developer and agent documentation through the dedicated read-only MCP server. Use for API, authentication, MCP, and integration questions; not for authenticated evidence or account operations.
license: MIT
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX documentation MCP

Use the public, read-only documentation server at `https://www.symbaiex.com/api/docs/mcp`. It requires no token and exposes only bounded documentation tools; it is separate from the authenticated evidence product API.

## Workflow

1. Use `docs_search` for a focused question. Its `query` is 1–200 characters and `limit` is 1–4 (default 4).
2. Use `docs_list` when you need the canonical documentation inventory. Pass a URI returned by `docs_list` or `docs_search` to `docs_get` to read that resource.
3. Ground integration guidance in the returned canonical document and link its URI. For implementation or authentication details, re-read the current published contract instead of inferring behavior from a search snippet.
4. If the docs server is unavailable, use the public developer portal at `https://www.symbaiex.com/developers` or `https://www.symbaiex.com/llms.txt` as read-only fallbacks.

## Keep product operations separate

Do not send credentials to this docs server or use it to search private evidence, create research jobs, manage agents, or change webhooks. Those operations belong to `https://www.symbaiex.com/api/agent/mcp` and require an owner-approved evidence credential. Before any authentication workflow, read `https://www.symbaiex.com/auth.md` and the current OpenAPI contract at `https://www.symbaiex.com/api/agent/openapi.json`; Ed25519 enrollment, WorkOS OAuth, and first-party `service_auth` are distinct methods. Never request or expose private keys, access tokens, refresh tokens, or owner login credentials, and never enroll or perform a consequential product operation without the user's explicit direction.
