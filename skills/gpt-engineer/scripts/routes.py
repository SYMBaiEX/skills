"""Single source of truth for parent-only Astra and Sol/Luna child routes."""

from datetime import datetime, timezone

ASTRA_MODEL = "gpt-6-astra"
SOL61_MODEL = "gpt-6.1-sol"
SOL_MODEL = "gpt-6-sol"
LUNA_MODEL = "gpt-6-luna"

# GPT-5.6 parents can remain active during the GPT-6 rollout. The skill never
# changes the selected parent and never selects Astra for a spawned child.
PARENT_MODELS = (
    ASTRA_MODEL,
    SOL61_MODEL,
    SOL_MODEL,
    LUNA_MODEL,
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)
CHILD_MODELS = (SOL61_MODEL, LUNA_MODEL)
MODEL_FAMILIES = {SOL61_MODEL: "sol61", LUNA_MODEL: "luna"}
PROFILE_PREFIXES = {SOL61_MODEL: "gpt61-sol", LUNA_MODEL: "gpt6-luna"}
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


SOL61 = {
    "gpt61-sol-engineer": route(SOL61_MODEL, "medium", True),
    "gpt61-sol-explorer": route(SOL61_MODEL, "medium", False),
    "gpt61-sol-worker": route(SOL61_MODEL, "medium", True),
    "gpt61-sol-verifier": route(SOL61_MODEL, "high", False),
}
LUNA = {
    "gpt6-luna-explorer": route(LUNA_MODEL, "high", False),
    "gpt6-luna-worker": route(LUNA_MODEL, "high", True),
    "gpt6-luna-verifier": route(LUNA_MODEL, "high", False),
}
CURRENT = {**SOL61, **LUNA}
ROLES = {name: {**value, "profile": name + ".toml"} for name, value in CURRENT.items()}

# Read-only history map. These names and models must never become new routes.
LEGACY = {
    **{f"gpt6-sol-{role}": SOL_MODEL for role in ("engineer", "explorer", "worker", "verifier")},
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
    if suite == "sol61":
        return {name: ROLES[name] for name in SOL61}
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
        retired = dispatch_policy in ("gpt6", "gpt61")
        if normalized.startswith("gpt6-sol-") and dispatch_policy == "gpt6":
            retired = False
        if normalized.startswith("gpt-engineer-") and created_at >= LEGACY_RETIREMENT.timestamp():
            retired = True
        reason = f"retired child profile under the asserted {dispatch_policy} routing policy" if retired else None
        return LEGACY[normalized], reason
    if normalized == "sol-engineer":
        if dispatch_policy in ("same-model", "mixed-model"):
            return "gpt-5.6-sol", None
        retired = dispatch_policy in ("gpt6", "gpt61") or (
            isinstance(created_at, (int, float)) and created_at >= MIGRATION.timestamp()
        )
        return "gpt-5.6-sol", "retired legacy Sol profile; use a GPT-6.1 Sol/Luna role" if retired else None
    current = ROLES.get(normalized)
    if current:
        if dispatch_policy == "gpt6" and normalized in SOL61:
            return current["model"], "child profile is outside the asserted historical gpt6 routing policy"
        return current["model"], None
    return None, None
