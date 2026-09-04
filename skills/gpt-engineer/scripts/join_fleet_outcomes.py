#!/usr/bin/env python3
"""Fail-closed outcome joins for GPT Engineer runner journals.

This deliberately does *not* manufacture outcomes from spawn edges, projected
turns, or OTel rows.  Those sources are useful coverage denominators only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "gpt-engineer-fleet-outcomes/v1"
JOURNAL_SCHEMA = "gpt-engineer-run-journal/v1"
IDENTITY = ("runId", "stageId", "attempt", "laneId")


def utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def parse_time(value: str | None, label: str) -> datetime | None:
    if value is None:
        return None
    parsed = utc(value)
    if parsed is None:
        raise ValueError(f"--{label} must be an ISO-8601 timestamp with timezone")
    return parsed


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def safe_id(value: Any, include: bool) -> str | None:
    if value is None:
        return None
    rendered = str(value)
    return rendered if include else digest(rendered)


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def discover(paths: list[str], name: str) -> list[Path]:
    found: set[Path] = set()
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file() and path.name == name:
            found.add(path.resolve())
        elif path.is_dir():
            found.update(item.resolve() for item in path.rglob(name) if item.is_file())
    return sorted(found)


def read_json(
    path: Path, diagnostics: list[dict[str, Any]], kind: str
) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        diagnostics.append(
            {"code": "malformed-json", "source": kind, "id": digest(str(path))}
        )
        return None
    if not isinstance(loaded, dict):
        diagnostics.append(
            {"code": "invalid-envelope", "source": kind, "id": digest(str(path))}
        )
        return None
    return loaded


def event_kind(event: dict[str, Any]) -> str:
    return str(
        event.get("type") or event.get("event") or event.get("kind") or ""
    ).lower()


def get_value(item: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in item:
            return item[name]
    lifecycle = item.get("lifecycle")
    if isinstance(lifecycle, dict):
        for name in names:
            if name in lifecycle:
                return lifecycle[name]
    data = item.get("data")
    if isinstance(data, dict):
        for name in names:
            if name in data:
                return data[name]
    return None


def identity(item: dict[str, Any]) -> tuple[str, str, str, str] | None:
    values = []
    # Journal v1 makes laneId optional.  stage + attempt is the durable lane
    # key in that case; it is more conservative than inventing a lane number.
    for key in IDENTITY[:3]:
        value = get_value(item, key, key[0].lower() + key[1:])
        if value is None or value == "":
            return None
        values.append(str(value))
    lane = get_value(item, "laneId", "lane_id")
    values.append(
        str(lane)
        if lane not in (None, "")
        else f"stage-attempt:{values[1]}:{values[2]}"
    )
    return tuple(values)  # type: ignore[return-value]


def result_identity(item: dict[str, Any]) -> tuple[str, str, str, str] | None:
    """Prefer stable identity; limited stage/attempt/time fallback for runner files."""
    direct = identity(item)
    if direct:
        return direct
    stage, attempt = get_value(item, "stageId"), get_value(item, "attempt")
    started = get_value(item, "startedAtUtc", "finishedAtUtc")
    if (
        stage is None
        or attempt is None
        or not isinstance(started, str)
        or utc(started) is None
    ):
        return None
    return ("result-time", str(stage), str(attempt), started)


def explicit_outcome(item: dict[str, Any]) -> dict[str, bool] | None:
    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    source = (
        item.get("outcome")
        if isinstance(item.get("outcome"), dict)
        else data.get("outcome")
        if isinstance(data.get("outcome"), dict)
        else item
    )
    values: dict[str, bool] = {}
    aliases = {
        "accepted": ("accepted", "acceptance"),
        "implemented": ("implemented", "implementation"),
        "verified": ("verified", "verification"),
    }
    for key, names in aliases.items():
        value = get_value(source, *names)
        if isinstance(value, bool):
            values[key] = value
    return values or None


def journal_outcome(events: list[dict[str, Any]]) -> dict[str, bool] | None:
    """Read explicit producer lifecycle states, never spawn/OTel guesses."""
    outcome: dict[str, bool] = {}
    for event in events:
        kind, status = event_kind(event), get_value(event, "status")
        if kind == "finding.updated" and status in {
            "implemented",
            "already_satisfied",
            "invalid",
            "duplicate",
            "deferred",
            "blocked",
        }:
            outcome["accepted"] = status in {"implemented", "already_satisfied"}
            outcome["implemented"] = status == "implemented"
        elif kind == "requirement.updated" and status in {
            "passed",
            "failed",
            "skipped",
            "not_run",
            "not_applicable",
            "blocked",
        }:
            outcome["implemented"] = status == "passed"
        elif kind == "verification.completed" and status in {
            "passed",
            "failed",
            "skipped",
            "not_run",
            "not_applicable",
            "blocked",
        }:
            outcome["verified"] = status == "passed"
    return outcome or None


def result_events(
    result: dict[str, Any],
    exact: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    by_stage: dict[tuple[str, str], list[dict[str, Any]]],
    diagnostics: list[dict[str, Any]],
    include_identifiers: bool,
) -> list[dict[str, Any]]:
    ident = identity(result)
    if ident and ident in exact:
        return exact[ident]
    stage, attempt = get_value(result, "stageId"), get_value(result, "attempt")
    if stage is None or attempt is None:
        return []
    candidates = by_stage.get((str(stage), str(attempt)), [])
    run_ids = {str(event.get("runId")) for event in candidates}
    if len(run_ids) > 1:
        diagnostics.append(
            {
                "code": "ambiguous-stage-attempt",
                "source": "join",
                "id": safe_id(f"{stage}:{attempt}", include_identifiers),
            }
        )
        return []
    return candidates


def event_timestamp(item: dict[str, Any]) -> datetime | None:
    return utc(
        str(
            get_value(
                item, "timestamp", "timestampUtc", "occurredAtUtc", "finishedAtUtc"
            )
            or ""
        )
    )


def route_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(get_value(item, "route", "model", "requestedModel") or "(unavailable)"),
        str(
            get_value(item, "effort", "reasoningEffort", "requestedReasoningEffort")
            or "(unavailable)"
        ),
        str(get_value(item, "mode", "lockMode") or "(unavailable)"),
    )


def load_journals(
    paths: list[Path],
    since: datetime | None,
    end: datetime | None,
    *,
    require_timestamp: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    counts = Counter(files=0, manifests=0, malformed=0, duplicates=0)
    seen: dict[str, str] = {}
    conflicted: set[str] = set()
    for journal in paths:
        manifest_path = journal.parent / "manifest.json"
        latest_path = journal.parent / "latest.json"
        manifest = (
            read_json(manifest_path, diagnostics, "manifest")
            if manifest_path.exists()
            else None
        )
        if manifest is None or manifest.get("schema") != JOURNAL_SCHEMA:
            diagnostics.append(
                {
                    "code": "unknown-or-missing-journal-schema",
                    "source": "journal",
                    "id": digest(str(journal.parent)),
                }
            )
            continue
        counts["manifests"] += 1
        if (
            latest_path.exists()
            and read_json(latest_path, diagnostics, "latest") is None
        ):
            counts["malformed"] += 1
        counts["files"] += 1
        try:
            lines = journal.read_bytes().splitlines(keepends=True)
        except OSError:
            diagnostics.append(
                {
                    "code": "unreadable-journal",
                    "source": "journal",
                    "id": digest(str(journal)),
                }
            )
            continue
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                code = (
                    "malformed-terminated-journal-line"
                    if line.endswith(b"\n")
                    else "partial-journal-tail"
                )
                diagnostics.append(
                    {
                        "code": code,
                        "source": "journal",
                        "line": number,
                        "id": digest(str(journal)),
                    }
                )
                counts["malformed"] += 1
                continue
            if (
                not isinstance(event, dict)
                or event.get("schema", JOURNAL_SCHEMA) != JOURNAL_SCHEMA
            ):
                diagnostics.append(
                    {
                        "code": "unknown-event-schema",
                        "source": "journal",
                        "line": number,
                        "id": digest(str(journal)),
                    }
                )
                counts["malformed"] += 1
                continue
            stamp = event_timestamp(event)
            if stamp is None and require_timestamp and not any(
                k in event for k in ("timestamp", "timestampUtc", "occurredAtUtc")
            ):
                diagnostics.append(
                    {
                        "code": "missing-timestamp-in-bounded-window",
                        "source": "journal",
                        "line": number,
                        "id": digest(str(journal)),
                    }
                )
                counts["malformed"] += 1
                continue
            if event_timestamp(event) is None and any(
                k in event for k in ("timestamp", "timestampUtc", "occurredAtUtc")
            ):
                diagnostics.append(
                    {
                        "code": "malformed-timestamp",
                        "source": "journal",
                        "line": number,
                        "id": digest(str(journal)),
                    }
                )
                counts["malformed"] += 1
                continue
            if stamp and ((since and stamp < since) or (end and stamp >= end)):
                continue
            event_id = event.get("eventId")
            if not isinstance(event_id, str) or not event_id:
                diagnostics.append(
                    {
                        "code": "missing-event-id",
                        "source": "journal",
                        "line": number,
                        "id": digest(str(journal)),
                    }
                )
                counts["malformed"] += 1
                continue
            rendered = json.dumps(event, sort_keys=True, separators=(",", ":"))
            if event_id in seen:
                counts["duplicates"] += 1
                if seen[event_id] != rendered:
                    conflicted.add(event_id)
                    diagnostics.append(
                        {
                            "code": "duplicate-event-conflict",
                            "source": "journal",
                            "line": number,
                            "id": digest(event_id),
                        }
                    )
                continue
            seen[event_id] = rendered
            event["_manifest"] = manifest
            events.append(event)
    if conflicted:
        events = [event for event in events if event.get("eventId") not in conflicted]
    return events, dict(counts), diagnostics


def load_results(
    paths: list[Path], diagnostics: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    results, seen, duplicates = [], set(), 0
    for path in paths:
        try:
            marker = f"{path.resolve()}:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        except OSError:
            diagnostics.append(
                {
                    "code": "unreadable-result",
                    "source": "result",
                    "id": digest(str(path)),
                }
            )
            continue
        if marker in seen:
            duplicates += 1
            continue
        seen.add(marker)
        result = read_json(path, diagnostics, "result")
        if result is not None:
            result["_path"] = str(path.resolve())
            results.append(result)
    return results, duplicates


def comparable_pairs(
    runs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs = []
    for number, left in enumerate(runs):
        for right in runs[number + 1 :]:
            if (
                not left["taskClass"]
                or not left["acceptanceContractHash"]
                or left["remainingRouteContext"] is None
                or any(
                    left[key] == "(unavailable)" for key in ("route", "effort", "mode")
                )
            ):
                continue
            if (
                left["taskClass"],
                left["acceptanceContractHash"],
                left["remainingRouteContext"],
            ) != (
                right["taskClass"],
                right["acceptanceContractHash"],
                right["remainingRouteContext"],
            ):
                continue
            differing = sum(
                left[key] != right[key] for key in ("route", "effort", "mode")
            )
            if differing == 1:
                pairs.append((left, right))
    return pairs


EFFORT_ORDER = {
    "none": 0,
    "minimal": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "xhigh": 5,
    "max": 6,
    "ultra": 7,
}
MODE_ORDER = {"fast": 1, "standard": 2, "broad": 3, "team": 4}


def material_improvement(lower: dict[str, Any], higher: dict[str, Any]) -> bool:
    if bool(get_value(lower["result"], "meaningfulLatencyOrUsageImprovement")):
        return True
    for field in ("durationMs", "finalDeduplicatedTokens", "tokenUsage"):
        low, high = (
            get_value(lower["result"], field),
            get_value(higher["result"], field),
        )
        if (
            isinstance(low, (int, float))
            and isinstance(high, (int, float))
            and high > 0
            and low <= high * 0.8
        ):
            return True
    return False


def recommendation(
    runs: list[dict[str, Any]],
    coverage: float | None,
    min_runs: int,
    min_pairs: int,
    conflicts: int,
) -> str:
    complete = [run for run in runs if run["complete"] and run["outcome"] is not None]
    if len(complete) < min_runs or coverage is None or coverage < 0.8 or conflicts:
        return "insufficient-evidence"
    failures = sum(
        1 for run in complete if run["result"].get("status") != "completed"
    ) / len(complete)
    pressure = any(
        bool(get_value(run["result"], "resourcePressure")) for run in complete
    )
    if pressure or failures >= 0.2:
        return "shrink"
    pairs = comparable_pairs(complete)
    if len(pairs) < min_pairs:
        return "hold"
    lower_support = raise_support = 0
    effort_pairs = 0
    for left, right in pairs:
        if (
            left["route"] != right["route"]
            or left["mode"] != right["mode"]
            or left["effort"] == right["effort"]
        ):
            continue
        if (
            left["effort"].lower() not in EFFORT_ORDER
            or right["effort"].lower() not in EFFORT_ORDER
        ):
            continue
        effort_pairs += 1
        if EFFORT_ORDER.get(left["effort"].lower(), -1) <= EFFORT_ORDER.get(
            right["effort"].lower(), -1
        ):
            lower, higher = left, right
        else:
            lower, higher = right, left
        low_outcome, high_outcome = lower["outcome"] or {}, higher["outcome"] or {}
        low_passes = bool(low_outcome.get("accepted")) and bool(
            low_outcome.get("verified")
        )
        high_passes = bool(high_outcome.get("accepted")) and bool(
            high_outcome.get("verified")
        )
        if low_passes and high_passes and material_improvement(lower, higher):
            lower_support += 1
        elif not low_passes and high_passes:
            raise_support += 1
    required_pairs = max(1, min_pairs)
    if effort_pairs >= required_pairs:
        if raise_support >= required_pairs and lower_support == 0:
            return "raise-effort"
        if lower_support >= required_pairs and raise_support == 0:
            return "lower-effort"
    # Expansion is intentionally conservative: only repeated, paired evidence
    # for a strictly wider non-Team mode with verified outcomes earns it.
    mode_pairs = expand_support = 0
    for left, right in pairs:
        if left["route"] != right["route"] or left["effort"] != right["effort"]:
            continue
        left_order, right_order = (
            MODE_ORDER.get(left["mode"].lower()),
            MODE_ORDER.get(right["mode"].lower()),
        )
        if left_order is None or right_order is None or left_order == right_order:
            continue
        candidate, control = (
            (left, right) if left_order > right_order else (right, left)
        )
        if candidate["mode"].lower() == "team":
            continue
        mode_pairs += 1
        candidate_outcome, control_outcome = (
            candidate["outcome"] or {},
            control["outcome"] or {},
        )
        candidate_passes = bool(candidate_outcome.get("accepted")) and bool(
            candidate_outcome.get("verified")
        )
        control_passes = bool(control_outcome.get("accepted")) and bool(
            control_outcome.get("verified")
        )
        if (
            candidate_passes
            and candidate_passes >= control_passes
            and bool(get_value(candidate["result"], "independentReadyWork"))
            and bool(
                get_value(candidate["result"], "meaningfulWallTimeOrYieldImprovement")
            )
        ):
            expand_support += 1
    if mode_pairs >= required_pairs and expand_support >= required_pairs:
        return "expand"
    return "hold"


def audit_if_requested(
    codex_home: str | None,
    since: datetime | None,
    snapshot_end: datetime | None,
    root_thread: str | None,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not codex_home:
        return None
    try:
        import audit_fleet

        audit_until = snapshot_end or datetime.now(timezone.utc)
        audit_since = since or (audit_until - timedelta(days=7))
        return audit_fleet.audit(
            codex_home=Path(codex_home).expanduser().resolve(),
            since=audit_since,
            until=audit_until,
            root_thread=root_thread,
        )
    except (ImportError, FileNotFoundError, ValueError):
        # Error text can contain the caller's home path.  The missing retained
        # store is coverage evidence, not an excuse to leak it in the report.
        diagnostics.append({"code": "audit-coverage-gap", "source": "audit"})
        return None


def redact_audit_identifiers(
    audit: dict[str, Any], include_identifiers: bool
) -> dict[str, Any]:
    """Copy the bounded audit summary while hashing thread identity fields by default."""
    rendered = json.loads(json.dumps(audit))
    if include_identifiers:
        return rendered
    if rendered.get("rootThread") is not None:
        rendered["rootThread"] = safe_id(rendered["rootThread"], False)
    fleet = rendered.get("fleet")
    if isinstance(fleet, dict):
        parents = fleet.get("parentCounts")
        if isinstance(parents, dict):
            fleet["parentCounts"] = {
                str(safe_id(key, False)): value for key, value in parents.items()
            }
        violations = fleet.get("routeViolations")
        if isinstance(violations, list):
            for violation in violations:
                if (
                    isinstance(violation, dict)
                    and violation.get("threadId") is not None
                ):
                    violation["threadId"] = safe_id(violation["threadId"], False)
    return rendered


def join(
    *,
    journals: list[str],
    result_dirs: list[str],
    codex_home: str | None = None,
    since: str | None = None,
    root_thread: str | None = None,
    snapshot_end: str | None = None,
    min_complete_runs: int = 5,
    min_comparable_pairs: int = 3,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    explicit_window = since is not None or snapshot_end is not None
    since_dt, end_dt = (
        parse_time(since, "since"),
        parse_time(snapshot_end, "snapshot-end"),
    )
    if end_dt is not None and since_dt is None:
        since_dt = end_dt - timedelta(days=7)
    if since_dt and end_dt and since_dt >= end_dt:
        raise ValueError("--snapshot-end must be after --since")
    if min_complete_runs <= 0:
        raise ValueError("--min-complete-runs must be positive")
    if min_comparable_pairs < 0:
        raise ValueError("--min-comparable-pairs must be nonnegative")
    diagnostics: list[dict[str, Any]] = []
    journal_paths = discover(journals, "journal.jsonl")
    result_paths = discover(result_dirs, "result.json")
    events, journal_counts, journal_diags = load_journals(
        journal_paths,
        since_dt,
        end_dt,
        require_timestamp=explicit_window,
    )
    diagnostics.extend(journal_diags)
    lifecycle_by_run: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "closed": None,
            "dispatches": set(),
            "handoffs": set(),
            "barriersStarted": set(),
            "barriersCompleted": set(),
        }
    )
    for event in events:
        run_id = get_value(event, "runId", "run_id")
        if run_id in (None, ""):
            continue
        item = lifecycle_by_run[str(run_id)]
        kind = event_kind(event)
        data_id = get_value(event, "dispatchId", "dispatch_id")
        stage_id = get_value(event, "stageId", "stage_id")
        if kind == "dispatch.accepted" and data_id not in (None, ""):
            item["dispatches"].add(str(data_id))
        elif kind == "handoff.received" and data_id not in (None, ""):
            item["handoffs"].add(str(data_id))
        elif kind == "barrier.started" and stage_id not in (None, ""):
            item["barriersStarted"].add(str(stage_id))
        elif kind == "barrier.completed" and stage_id not in (None, ""):
            item["barriersCompleted"].add(str(stage_id))
        elif kind == "run.closed":
            item["closed"] = str(get_value(event, "status") or "unknown")
    close_status_counts = Counter(
        str(item["closed"] or "missing") for item in lifecycle_by_run.values()
    )
    unclosed_run_ids = [
        safe_id(run_id, include_identifiers)
        for run_id, item in lifecycle_by_run.items()
        if item["closed"] is None
    ]
    journal_lifecycle = {
        "runs": len(lifecycle_by_run),
        "closedRuns": sum(item["closed"] is not None for item in lifecycle_by_run.values()),
        "closeStatusCounts": dict(close_status_counts.most_common()),
        "unclosedRuns": len(unclosed_run_ids),
        "unclosedRunIds": sorted(item for item in unclosed_run_ids if item is not None),
        "dispatchesWithoutHandoff": sum(
            len(item["dispatches"] - item["handoffs"])
            for item in lifecycle_by_run.values()
        ),
        "openBarriers": sum(
            len(item["barriersStarted"] - item["barriersCompleted"])
            for item in lifecycle_by_run.values()
        ),
    }
    results, result_duplicates = load_results(result_paths, diagnostics)
    journal_by_id: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    journal_by_stage: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    denominators = Counter(
        dispatched=0,
        routed=0,
        **{
            "result-envelope": len(results),
            "projected": 0,
            "otel-covered": 0,
            "outcome-eligible": 0,
            "accepted": 0,
            "implemented": 0,
            "verified": 0,
        },
    )
    dispatched, routed, projected, otel = set(), set(), set(), set()
    for event in events:
        ident = identity(event)
        if ident:
            journal_by_id[ident].append(event)
            journal_by_stage[(ident[1], ident[2])].append(event)
        kind = event_kind(event)
        token = ident or (str(event.get("eventId")),)
        if kind == "dispatch.accepted":
            dispatched.add(token)
            if (
                get_value(event, "route", "model", "requestedModel", "agentRole")
                is not None
            ):
                routed.add(token)
        if kind == "handoff.received":
            projected.add(token)
        if kind.startswith("otel."):
            otel.add(token)
    denominators.update(
        {
            "dispatched": len(dispatched),
            "routed": len(routed),
            "projected": len(projected),
            "otel-covered": len(otel),
        }
    )
    runs, conflicts, joined_results = (
        [],
        sum(item["code"] == "duplicate-event-conflict" for item in diagnostics),
        0,
    )
    duplicate_rate = (journal_counts.get("duplicates", 0) + result_duplicates) / max(
        1,
        len(events)
        + len(results)
        + journal_counts.get("duplicates", 0)
        + result_duplicates,
    )
    for result in results:
        ident = result_identity(result)
        matching = result_events(
            result, journal_by_id, journal_by_stage, diagnostics, include_identifiers
        )
        finished = utc(str(get_value(result, "finishedAtUtc") or ""))
        if finished and any(
            (stamp := event_timestamp(event)) is not None and stamp > finished
            for event in matching
        ):
            diagnostics.append(
                {
                    "code": "timestamp-mismatch",
                    "source": "join",
                    "id": safe_id(ident, include_identifiers),
                }
            )
            matching = []
        outcomes = [
            explicit_outcome(item) for item in matching if explicit_outcome(item)
        ]
        event_outcome = journal_outcome(matching)
        if event_outcome:
            outcomes.append(event_outcome)
        result_outcome = explicit_outcome(result)
        if result_outcome:
            outcomes.append(result_outcome)
        merged: dict[str, bool] | None = None
        if outcomes:
            merged = {}
            for key in ("accepted", "implemented", "verified"):
                values = {outcome[key] for outcome in outcomes if key in outcome}
                if len(values) > 1:
                    conflicts += 1
                    diagnostics.append(
                        {
                            "code": "identity-conflict",
                            "source": "join",
                            "id": safe_id(ident, include_identifiers),
                        }
                    )
                    merged = None
                    break
                if values:
                    merged[key] = values.pop()
        complete = str(result.get("status")) in {"completed", "failed"} and bool(ident)
        route, effort, mode = route_key(result)
        context = get_value(
            result, "remainingRouteContext", "routeContext", "comparisonContext"
        )
        if not isinstance(context, dict):
            context = None
        elif "routeContext" in result:
            context = {
                key: value
                for key, value in context.items()
                if key not in {"route", "effort", "mode"}
            }
        run = {
            "id": ident,
            "result": result,
            "events": matching,
            "outcome": merged,
            "complete": complete,
            "route": route,
            "effort": effort,
            "mode": mode,
            "taskClass": get_value(result, "taskClass"),
            "acceptanceContractHash": get_value(result, "acceptanceContractHash"),
            "remainingRouteContext": json.dumps(context, sort_keys=True)
            if context is not None
            else None,
        }
        runs.append(run)
        joined_results += int(bool(matching))
        if complete and merged is not None:
            denominators["outcome-eligible"] += 1
            for key in ("accepted", "implemented", "verified"):
                denominators[key] += int(bool(merged.get(key)))
    # A run directory can contain many lane result envelopes.  Count joinable
    # envelopes rather than comparing unrelated file counts.
    coverage = (joined_results / len(results)) if results else None
    metric_buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        metric_buckets[(run["route"], run["effort"], run["mode"])].append(run)
    metrics = []
    for (route, effort, mode), bucket in sorted(metric_buckets.items()):
        durations = [get_value(item["result"], "durationMs") for item in bucket]
        durations = [
            int(value) for value in durations if isinstance(value, (int, float))
        ]
        eligible = [item for item in bucket if item["outcome"] is not None]
        event_list = [event for item in bucket for event in item["events"]]
        retries = [event for event in event_list if "retry" in event_kind(event)]
        commands = [event for event in event_list if "command" in event_kind(event)]
        failed_commands = [
            event
            for event in commands
            if str(get_value(event, "status", "result")) in {"failed", "failure"}
            or get_value(event, "exitCode") not in (None, 0)
        ]
        accepted_findings = [
            get_value(event, "acceptedFindings") for event in event_list
        ]
        accepted_findings = [
            int(value) for value in accepted_findings if isinstance(value, (int, float))
        ]
        # A final usage marker is required.  Earlier OTel-like cumulative values
        # are intentionally ignored because they cannot safely be summed.
        token_values = [
            get_value(event, "tokens", "tokenUsage")
            for event in event_list
            if bool(get_value(event, "finalUsage", "usageFinal", "deduplicated"))
        ]
        final_tokens = None
        if token_values and all(
            isinstance(value, (int, float)) for value in token_values
        ):
            final_tokens = sum(int(value) for value in token_values)
        metrics.append(
            {
                "route": route,
                "effort": effort,
                "mode": mode,
                "runs": len(bucket),
                "durationMs": {
                    "p50": percentile(durations, 0.5),
                    "p90": percentile(durations, 0.9),
                },
                "retryRate": (len(retries) / len(bucket)) if event_list else None,
                "commandFailureRate": (len(failed_commands) / len(commands))
                if commands
                else None,
                "acceptanceRate": (
                    sum(bool(item["outcome"].get("accepted")) for item in eligible)
                    / len(eligible)
                )
                if eligible
                else None,
                "implementationRate": (
                    sum(bool(item["outcome"].get("implemented")) for item in eligible)
                    / len(eligible)
                )
                if eligible
                else None,
                "verificationRate": (
                    sum(bool(item["outcome"].get("verified")) for item in eligible)
                    / len(eligible)
                )
                if eligible
                else None,
                "duplicateRate": duplicate_rate,
                "acceptedFindingsPerLane": (sum(accepted_findings) / len(bucket))
                if accepted_findings
                else None,
                "finalDeduplicatedTokens": final_tokens,
            }
        )
    audit = audit_if_requested(
        codex_home, since_dt, end_dt, root_thread, diagnostics
    )
    audit_projected = audit_otel = False
    if isinstance(audit, dict):
        history, otel_scope = audit.get("history"), audit.get("otelScope")
        if isinstance(history, dict) and isinstance(
            history.get("projectedThreads"), int
        ):
            denominators["projected"] = history["projectedThreads"]
            audit_projected = True
        if isinstance(otel_scope, dict) and isinstance(otel_scope.get("threads"), int):
            denominators["otel-covered"] = otel_scope["threads"]
            audit_otel = True
    journal_available, result_available = bool(journal_paths), bool(result_paths)
    # Journal v1 has no OTel event producer.  Do not turn that unavailable
    # store into an observed zero merely because a journal exists.
    unavailable_without_result = {
        "result-envelope",
        "outcome-eligible",
        "accepted",
        "implemented",
        "verified",
    }
    rendered_denominators = {
        key: None
        if (
            (key in {"dispatched", "routed"} and not journal_available)
            or (key == "projected" and not journal_available and not audit_projected)
            or (key == "otel-covered" and not otel and not audit_otel)
            or (key in unavailable_without_result and not result_available)
        )
        else value
        for key, value in denominators.items()
    }
    rendered_audit = (
        redact_audit_identifiers(audit, include_identifiers)
        if isinstance(audit, dict)
        else audit
    )
    return {
        "schema": SCHEMA,
        "window": {
            "sinceUtc": since_dt.isoformat().replace("+00:00", "Z")
            if since_dt
            else None,
            "snapshotEndUtc": end_dt.isoformat().replace("+00:00", "Z")
            if end_dt
            else None,
        },
        "sources": {
            "journals": len(journal_paths),
            "results": len(results),
            "journalDuplicates": journal_counts.get("duplicates", 0),
            "resultDuplicates": result_duplicates,
        },
        "journalLifecycle": journal_lifecycle if journal_available else None,
        "denominators": rendered_denominators,
        "coverage": {
            "journalResult": coverage,
            "sufficient": coverage is not None and coverage >= 0.8,
        },
        "identityConflicts": conflicts,
        "metrics": metrics,
        "recommendation": recommendation(
            runs, coverage, min_complete_runs, min_comparable_pairs, conflicts
        ),
        "diagnostics": diagnostics,
        "audit": rendered_audit,
        "limitations": [
            "outcomes require explicit journal or result-envelope fields",
            "identifiers, prompts, final messages, commands, and home paths are redacted by default",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", action="append", default=[])
    parser.add_argument("--result-dir", action="append", default=[])
    parser.add_argument("--codex-home")
    parser.add_argument("--since")
    parser.add_argument("--root-thread")
    parser.add_argument("--snapshot-end")
    parser.add_argument("--min-complete-runs", type=int, default=5)
    parser.add_argument("--min-comparable-pairs", type=int, default=3)
    parser.add_argument("--include-identifiers", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = join(
            journals=args.journal,
            result_dirs=args.result_dir,
            codex_home=args.codex_home,
            since=args.since,
            root_thread=args.root_thread,
            snapshot_end=args.snapshot_end,
            min_complete_runs=args.min_complete_runs,
            min_comparable_pairs=args.min_comparable_pairs,
            include_identifiers=args.include_identifiers,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(
        json.dumps(output, indent=2)
        if args.json
        else f"{output['recommendation']}; {output['denominators']['outcome-eligible']} outcome-eligible runs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
