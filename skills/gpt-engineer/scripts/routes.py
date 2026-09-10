"""Single source of truth for current requested routes and historical policies."""
from datetime import datetime, timezone

ASTRA_MODEL = "gpt-6-astra"
# Policy cutover is an explicit instant, not the beginning of the release day.
MIGRATION = datetime(2026, 9, 10, 23, 23, 48, tzinfo=timezone.utc)
LEGACY_RETIREMENT = datetime(2026, 8, 31, 7, 15, 45, tzinfo=timezone.utc)

def route(model, effort, writable, tier=None):
    value = {"model": model, "effort": effort, "write_capable": writable}
    if tier:
        value["service_tier"] = tier
    return value

ASTRA = {
    "astra-engineer": route(ASTRA_MODEL, "high", True),
    "astra-explorer": route(ASTRA_MODEL, "medium", False),
    "astra-worker": route(ASTRA_MODEL, "medium", True),
    "astra-verifier": route(ASTRA_MODEL, "medium", True),
}
ECONOMY = {
    "terra-explorer": route("gpt-5.6-terra", "medium", False),
    "terra-worker": route("gpt-5.6-terra", "medium", True),
    "luna-worker": route("gpt-5.6-luna", "low", True),
    "luna-max-worker": route("gpt-5.6-luna", "max", True, "fast"),
    "luna-verifier": route("gpt-5.6-luna", "medium", True),
}
ROLES = {name: {**value, "profile": name + ".toml"} for name, value in {**ASTRA, **ECONOMY}.items()}
LEGACY = {"gpt-engineer-lead": "gpt-5.6-sol", "gpt-engineer-explorer": "gpt-5.6-terra", "gpt-engineer-worker": "gpt-5.6-terra", "gpt-engineer-verifier": "gpt-5.6-luna"}

def suite_routes(suite="astra"):
    if suite not in ("astra", "economy"):
        raise ValueError("Unknown routing suite: " + suite)
    return {name: value for name, value in ROLES.items() if suite == "economy" or name in ASTRA}

def expected_profiles(suite="astra"):
    return {name.replace("-", "_"): (value["model"], value["effort"], value.get("service_tier")) for name, value in suite_routes(suite).items()}

def historical_policy(role, created_at):
    """Return exact model and retirement reason; never infer economy authorization."""
    if role in LEGACY:
        return LEGACY[role], "retired GPT Engineer profile used after native-first migration" if created_at >= LEGACY_RETIREMENT.timestamp() else None
    if role == "sol_engineer":
        return "gpt-5.6-sol", "retired Sol profile used after Astra migration" if created_at >= MIGRATION.timestamp() else None
    current = ROLES.get(role.replace("_", "-"))
    return (current["model"], None) if current else (None, None)
