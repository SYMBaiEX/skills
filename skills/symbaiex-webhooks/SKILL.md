---
name: symbaiex-webhooks
description: Configure owner-scoped, allowlisted, HMAC-signed SYMBaiEX evidence webhooks. Use when an operator needs durable change, job, benchmark, quota, or entitlement notifications.
license: MIT
compatibility: Requires a SYMBaiEX Ed25519 bearer with the evidence scope and an operator-approved HTTPS destination.
metadata:
  author: SYMBaiEX
  version: "1.0.0"
---

# SYMBaiEX webhooks

1. Read the AsyncAPI contract and check the webhook availability endpoint before creating a subscription.
2. Use an exact HTTPS destination already permitted by the platform allowlist.
3. Store the one-time signing secret outside chat, logs, URLs, browser storage, and source control.
4. Verify the HMAC over the exact timestamp and raw request body before parsing JSON. Enforce the documented timestamp window and deduplicate by event ID.
5. Use owner-scoped status, health, and bounded history operations. Pause or revoke a destination that fails validation.
6. Rotate secrets deliberately and update the receiver immediately. Replay only terminal deliveries that the operator has reviewed.

Never accept an event solely because its JSON shape looks valid. Signature verification and owner isolation are required.
