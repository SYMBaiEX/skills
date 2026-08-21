---
name: symbaiex-agent-enrollment
description: Connect a user-directed agent to SYMBaiEX with a locally held Ed25519 key. Use when a user asks to enroll, authenticate, refresh, rotate, or revoke an agent identity.
license: MIT
compatibility: Requires HTTPS access to www.symbaiex.com and local Ed25519 signing support.
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX agent enrollment

1. Read `https://www.symbaiex.com/agent/instructions` and the API manifest.
2. Ask the human owner to create or open the account at `https://www.symbaiex.com/signin?mode=signUp&redirectTo=/agent/signup`, then enroll at `https://www.symbaiex.com/agent/signup`.
3. Generate and retain the Ed25519 private key locally. Send only the public key to the enrollment UI.
4. Request a one-time challenge from `/api/agent/auth/challenge`, sign the exact challenge locally, and exchange it at `/api/agent/auth/sign-in`.
5. Keep access and refresh tokens in an OS keychain or approved secret manager. Never print, upload, or place them in model context.
6. Reuse the stable agent ID and refresh flow. Ask the owner to rotate or revoke the key if it may be compromised.

Do not request passwords, private keys, backend deployment URLs, or broader scopes than the task needs.
