"""Single source of truth for parent-only Astra and GPT-6 Sol/Luna child routes."""

from datetime import datetime, timezone

ASTRA_MODEL = "gpt-6-astra"
SOL_MODEL = "gpt-6-sol"
LUNA_MODEL = "gpt-6-luna"

# GPT-5.6 parents can remain active during the GPT-6 rollout. The skill never
# changes the selected parent and never selects Astra for a spawned child.
PARENT_MODELS = (
    ASTRA_MODEL,
    SOL_MODEL,
    LUNA_MODEL,
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)
CHILD_MODELS = (SOL_MODEL, LUNA_MODEL)
# Parent-event metadata may contain any supported selected parent. Child model
# validation always uses CHILD_MODELS, never this parent allowlist.
SUPPORTED_MODELS = PARENT_MODELS

# Historical cutovers remain for classifying stored OTel cohorts. They do not
# infer what an old running task loaded from timestamps alone.
MIGRATION = datetime(2026, 9, 10, 23, 23, 48, tzinfo=timezone.utc)
LEGACY_RETIREMENT = datetime(2026, 8, 31, 7, 15, 45, tzinfo=timezone.utc)
def route(model, effort, writable, tier=None):
    value = {"model": model, "effort": effort, "write_capable": writable}
    if tier:
        value["service_tier"] = tier
    return value


SOL = {
    "gpt6-sol-engineer": route(SOL_MODEL, "medium", True),
    "gpt6-sol-explorer": route(SOL_MODEL, "medium", False),
    "gpt6-sol-worker": route(SOL_MODEL, "medium", True),
    "gpt6-sol-verifier": route(SOL_MODEL, "high", False),
}
LUNA = {
    "gpt6-luna-explorer": route(LUNA_MODEL, "high", False),
    "gpt6-luna-worker": route(LUNA_MODEL, "high", True),
    "gpt6-luna-verifier": route(LUNA_MODEL, "high", False),
}
CURRENT = {**SOL, **LUNA}
ROLES = {name: {**value, "profile": name + ".toml"} for name, value in CURRENT.items()}

# Read-only history map. These names and models must never become new routes.
LEGACY = {
    "astra-engineer": ASTRA_MODEL,
    "astra-explorer": ASTRA_MODEL,
    "astra-worker": ASTRA_MODEL,
    "astra-verifier": ASTRA_MODEL,
    "terra-explorer": "gpt-5.6-terra",
    "terra-worker": "gpt-5.6-terra",
    "luna-worker": "gpt-5.6-luna",
    "luna-verifier": "gpt-5.6-luna",
    "luna-max-worker": "gpt-5.6-luna",
    "gpt-engineer-lead": "gpt-5.6-sol",
    "gpt-engineer-explorer": "gpt-5.6-terra",
    "gpt-engineer-worker": "gpt-5.6-terra",
    "gpt-engineer-verifier": "gpt-5.6-luna",
    "sol_engineer": "gpt-5.6-sol",
}
LEGACY_ASTRA_CHILD_NAMES = frozenset(
    {"astra-engineer", "astra-explorer", "astra-worker", "astra-verifier"}
)


def suite_routes(suite="all"):
    if suite == "all":
        return dict(ROLES)
    if suite == "sol":
        return {name: ROLES[name] for name in SOL}
    if suite == "luna":
        return {name: ROLES[name] for name in LUNA}
    if suite == "astra":
        raise ValueError("Astra is orchestrator-only; no Astra child suite exists")
    raise ValueError("Unknown routing suite: " + str(suite))


def expected_profiles(suite="all"):
    return {
        name.replace("-", "_"): (value["model"], value["effort"], value.get("service_tier"))
        for name, value in suite_routes(suite).items()
    }


def historical_policy(role, created_at, dispatch_policy=None):
    """Return recorded policy for an old route without inventing loaded-version evidence."""
    if not isinstance(role, str):
        return None, None
    normalized = role.replace("_", "-")
    if normalized in LEGACY:
        retired = dispatch_policy == "gpt6"
        if normalized.startswith("gpt-engineer-") and created_at >= LEGACY_RETIREMENT.timestamp():
            retired = True
        reason = "retired child profile under the asserted GPT-6 routing policy" if retired else None
        return LEGACY[normalized], reason
    if normalized == "sol-engineer":
        if dispatch_policy in ("same-model", "mixed-model"):
            return "gpt-5.6-sol", None
        retired = dispatch_policy == "gpt6" or (
            isinstance(created_at, (int, float)) and created_at >= MIGRATION.timestamp()
        )
        return "gpt-5.6-sol", "retired legacy Sol profile; use a GPT-6 Sol/Luna role" if retired else None
    current = ROLES.get(normalized)
    if current:
        return current["model"], None
    return None, None
