#!/usr/bin/env python3
"""Summarize Codex fleet routing, turn latency, concurrency, and retained OTel coverage."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


from routes import ROLES, LEGACY, LEGACY_RETIREMENT, historical_policy, ASTRA, ECONOMY
ALLOWED_MODELS = {value["model"] for value in ROLES.values()}
CURRENT_ROLES = {name.replace("-", "_") for name in ROLES}
HISTORICAL_ROLES = set(LEGACY) | {"sol_engineer"}
CATALOG_ROLES = CURRENT_ROLES | HISTORICAL_ROLES
# The native-first profile names shipped in this commit. Historical names stay
# queryable for baselines but are not valid dispatch targets after this point.
HISTORICAL_ROLE_RETIREMENT = LEGACY_RETIREMENT


def parse_since(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc) - timedelta(days=7)
    rendered = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(rendered)
    except ValueError as exc:
        raise ValueError("--since must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("--since must include a timezone, such as Z or -05:00")
    return parsed.astimezone(timezone.utc)


def parse_until(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return parse_since(value)


def utc_timestamp(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.5)))
    return ordered[index]


def peak_concurrency(intervals: list[tuple[int, int]]) -> int:
    events: list[tuple[int, int]] = []
    for started, completed in intervals:
        events.extend(((started, 1), (completed, -1)))
    active = 0
    peak = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def coverage(connection: sqlite3.Connection, table: str, timestamp: str) -> dict[str, object]:
    if not table_exists(connection, table):
        return {"available": False, "rows": 0, "minUtc": None, "maxUtc": None}
    rows, minimum, maximum = connection.execute(
        f"SELECT count(*), min({timestamp}), max({timestamp}) FROM {table}"
    ).fetchone()
    return {
        "available": True,
        "rows": rows,
        "minUtc": utc_timestamp(minimum),
        "maxUtc": utc_timestamp(maximum),
    }


def cohort_rows(
    state: sqlite3.Connection, since_epoch: int, until_epoch: int, root_thread: str | None
) -> list[sqlite3.Row]:
    if root_thread:
        query = """
            WITH RECURSIVE descendants(id) AS (
                SELECT child_thread_id FROM thread_spawn_edges WHERE parent_thread_id = ?
                UNION
                SELECT e.child_thread_id
                FROM thread_spawn_edges e JOIN descendants d ON e.parent_thread_id = d.id
            )
            SELECT t.id, t.agent_role, t.model, t.reasoning_effort, t.created_at,
                   e.parent_thread_id, e.status AS spawn_status
            FROM descendants d
            JOIN threads t ON t.id = d.id
            JOIN thread_spawn_edges e ON e.child_thread_id = t.id
            WHERE t.created_at >= ? AND t.created_at < ?
            ORDER BY t.created_at, t.id
        """
        return list(state.execute(query, (root_thread, since_epoch, until_epoch)))
    return list(
        state.execute(
            """
            SELECT t.id, t.agent_role, t.model, t.reasoning_effort, t.created_at,
                   e.parent_thread_id, e.status AS spawn_status
            FROM threads t
            JOIN thread_spawn_edges e ON e.child_thread_id = t.id
            WHERE t.created_at >= ? AND t.created_at < ?
            ORDER BY t.created_at, t.id
            """,
            (since_epoch, until_epoch),
        )
    )


def load_turns(
    history: sqlite3.Connection,
    thread_ids: list[str],
    since_epoch: int,
    until_epoch: int,
) -> list[sqlite3.Row]:
    if not thread_ids or not table_exists(history, "thread_turns"):
        return []
    history.execute("CREATE TEMP TABLE selected_threads(id TEXT PRIMARY KEY)")
    history.executemany("INSERT INTO selected_threads(id) VALUES (?)", ((item,) for item in thread_ids))
    return list(
        history.execute(
            """
            SELECT t.thread_id, t.status, t.started_at, t.completed_at, t.duration_ms
            FROM thread_turns t JOIN selected_threads s ON s.id = t.thread_id
            WHERE t.started_at >= ? AND t.started_at < ?
            ORDER BY t.started_at, t.thread_id
            """,
            (since_epoch, until_epoch),
        )
    )


def summarize_turns(
    turns: list[sqlite3.Row], thread_ids: set[str] | None = None
) -> dict[str, object]:
    selected = (
        turns
        if thread_ids is None
        else [row for row in turns if str(row["thread_id"]) in thread_ids]
    )
    statuses = Counter(str(row["status"]) for row in selected)
    completed = [
        row
        for row in selected
        if row["status"] == "completed" and row["duration_ms"] is not None
    ]
    durations = [int(row["duration_ms"]) for row in completed]
    intervals = [
        (int(row["started_at"]), int(row["completed_at"]))
        for row in completed
        if row["started_at"] is not None and row["completed_at"] is not None
    ]
    return {
        "projectedTurns": len(selected),
        "projectedThreads": len({str(row["thread_id"]) for row in selected}),
        "statusCounts": dict(statuses.most_common()),
        "completedDurationMs": {
            "p50": percentile(durations, 0.50),
            "p90": percentile(durations, 0.90),
            "p95": percentile(durations, 0.95),
            "max": max(durations) if durations else None,
        },
        "peakCompletedTurnConcurrency": peak_concurrency(intervals),
    }


def audit(
    *,
    codex_home: Path,
    since: datetime,
    until: datetime | None = None,
    root_thread: str | None = None,
    dispatch_suite: str | None = None,
) -> dict[str, object]:
    if dispatch_suite not in (None, "astra", "economy"):
        raise ValueError("Unknown dispatch suite")
    state_path = codex_home / "state_5.sqlite"
    history_path = codex_home / "thread_history_1.sqlite"
    logs_path = codex_home / "logs_2.sqlite"
    if not state_path.is_file():
        raise FileNotFoundError(f"missing Codex state database: {state_path}")

    until = until or datetime.now(timezone.utc)
    if until <= since:
        raise ValueError("--until must be after --since")
    state = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    state.row_factory = sqlite3.Row
    try:
        rows = cohort_rows(
            state, int(since.timestamp()), int(until.timestamp()), root_thread
        )
        state_coverage = coverage(state, "threads", "created_at")
    finally:
        state.close()

    thread_ids = [str(row["id"]) for row in rows]
    history_coverage = {"available": False, "rows": 0, "minUtc": None, "maxUtc": None}
    turns: list[sqlite3.Row] = []
    if history_path.is_file():
        history = sqlite3.connect(f"file:{history_path}?mode=ro", uri=True)
        history.row_factory = sqlite3.Row
        try:
            history_coverage = coverage(history, "thread_turns", "started_at")
            turns = load_turns(
                history,
                thread_ids,
                int(since.timestamp()),
                int(until.timestamp()),
            )
        finally:
            history.close()

    logs_coverage = {"available": False, "rows": 0, "minUtc": None, "maxUtc": None}
    scoped_log_rows = 0
    scoped_log_threads = 0
    if logs_path.is_file():
        logs = sqlite3.connect(f"file:{logs_path}?mode=ro", uri=True)
        try:
            logs_coverage = coverage(logs, "logs", "ts")
            if thread_ids and table_exists(logs, "logs"):
                logs.execute("CREATE TEMP TABLE selected_threads(id TEXT PRIMARY KEY)")
                logs.executemany(
                    "INSERT INTO selected_threads(id) VALUES (?)", ((item,) for item in thread_ids)
                )
                scoped_log_rows, scoped_log_threads = logs.execute(
                    """
                    SELECT count(*), count(DISTINCT l.thread_id)
                    FROM logs l JOIN selected_threads s ON s.id = l.thread_id
                    WHERE l.ts >= ? AND l.ts < ?
                    """,
                    (int(since.timestamp()), int(until.timestamp())),
                ).fetchone()
        finally:
            logs.close()

    model_counts = Counter(str(row["model"] or "(missing)") for row in rows)
    role_counts = Counter(str(row["agent_role"] or "(missing)") for row in rows)
    parent_counts = Counter(str(row["parent_thread_id"]) for row in rows)
    spawn_status_counts = Counter(str(row["spawn_status"]) for row in rows)
    current_rows = [row for row in rows if row["agent_role"] in CURRENT_ROLES]
    historical_rows = [row for row in rows if row["agent_role"] in HISTORICAL_ROLES]
    unattributed_rows = [row for row in rows if row["agent_role"] not in CATALOG_ROLES]
    catalog_rows = current_rows + historical_rows
    route_violations = []
    stale_profiles = []
    for row in rows:
        reasons = []
        expected_model, retired = historical_policy(row["agent_role"], int(row["created_at"]))
        if expected_model is not None and row["model"] != expected_model:
            reasons.append(f"model does not match profile policy: expected {expected_model}")
        if retired and row["agent_role"] == "sol_engineer" and dispatch_suite is None:
            stale_profiles.append({"threadId": row["id"], "agentRole": row["agent_role"], "reason": "Sol profile after release cutover; installed workflow version and dispatch policy are unknown"})
        elif retired:
            reasons.append(retired)
        if dispatch_suite and row["agent_role"] == "sol_engineer" and not retired:
            reasons.append("Sol is outside the explicitly asserted v2 dispatch suite")
        if dispatch_suite == "astra" and row["agent_role"] in {name.replace("-", "_") for name in ECONOMY}:
            reasons.append("economy profile is outside the explicitly asserted Astra dispatch suite")
        if reasons:
            route_violations.append(
                {
                    "threadId": row["id"],
                    "agentRole": row["agent_role"],
                    "model": row["model"],
                    "reasoningEffort": row["reasoning_effort"],
                    "reasons": reasons,
                }
            )
    all_history = summarize_turns(turns)
    history_by_cohort = {
        "currentProfiles": summarize_turns(
            turns, {str(row["id"]) for row in current_rows}
        ),
        "historicalProfiles": summarize_turns(
            turns, {str(row["id"]) for row in historical_rows}
        ),
        "unattributed": summarize_turns(
            turns, {str(row["id"]) for row in unattributed_rows}
        ),
    }
    warnings: list[str] = []
    since_epoch = int(since.timestamp())
    for label, item in (("OTel", logs_coverage), ("turn history", history_coverage)):
        minimum = item.get("minUtc")
        if minimum and datetime.fromisoformat(str(minimum).replace("Z", "+00:00")).timestamp() > since_epoch:
            warnings.append(f"{label} retention starts after the requested window")
    if route_violations:
        warnings.append("one or more GPT Engineer catalog children violated the active role/model contract")
    if unattributed_rows:
        warnings.append(
            "spawned children outside the GPT Engineer catalog are unattributed; do not classify them as route violations without dispatch-source evidence"
        )

    return {
        "schema": "gpt-engineer-fleet-audit/v1",
        "requestedSinceUtc": since.isoformat().replace("+00:00", "Z"),
        "requestedUntilUtc": until.isoformat().replace("+00:00", "Z"),
        "rootThread": root_thread,
        "coverage": {
            "state": state_coverage,
            "otel": logs_coverage,
            "history": history_coverage,
        },
        "fleet": {
            "spawnedChildren": len(rows),
            "catalogChildren": len(catalog_rows),
            "currentProfileChildren": len(current_rows),
            "historicalProfileChildren": len(historical_rows),
            "unattributedChildren": len(unattributed_rows),
            "latestOnlyChildren": sum(
                row["agent_role"] in CURRENT_ROLES and row["model"] == historical_policy(row["agent_role"], int(row["created_at"]))[0]
                for row in rows
            ),
            "modelCounts": dict(model_counts.most_common()),
            "roleCounts": dict(role_counts.most_common()),
            "parentCounts": dict(parent_counts.most_common()),
            "spawnEdgeStatusCounts": dict(spawn_status_counts.most_common()),
            "routeViolations": route_violations,
            "staleProfileDiagnostics": stale_profiles,
            "assertedDispatchSuite": dispatch_suite,
        },
        "history": all_history,
        "historyByProfileCohort": history_by_cohort,
        "routeCohorts": {
            "astra": sum(row["agent_role"].replace("_", "-") in ASTRA for row in rows if row["agent_role"]),
            "economy": sum(row["agent_role"].replace("_", "-") in ECONOMY for row in rows if row["agent_role"]),
            "historical": len(historical_rows),
            "economyAuthorization": "not observable from thread model metadata; requires dispatch evidence",
        },
        "otelScope": {
            "rows": scoped_log_rows,
            "threads": scoped_log_threads,
            "usageDeduplicated": False,
        },
        "warnings": warnings,
        "limitations": [
            "spawn-edge status is registry metadata, not operating-system process liveness",
            "OTel token attributes are not deduplicated by this summary",
            "command, retry, compaction, and finding metrics require runner envelopes or rollout analysis",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    parser.add_argument("--since", help="ISO-8601 start time; defaults to seven days ago")
    parser.add_argument("--until", help="Exclusive ISO-8601 snapshot end; defaults to now")
    parser.add_argument("--root-thread", help="Limit the cohort to descendants of one root thread")
    parser.add_argument("--dispatch-suite", choices=("astra", "economy"), help="Assert a known v2 dispatch policy; omit for version-unknown historical data")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(
            codex_home=Path(args.codex_home).expanduser().resolve(),
            since=parse_since(args.since),
            until=parse_until(args.until),
            root_thread=args.root_thread,
            dispatch_suite=args.dispatch_suite,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        fleet = result["fleet"]
        history = result["history"]
        print(
            f"{fleet['spawnedChildren']} children; {fleet['catalogChildren']} GPT Engineer catalog children; "
            f"{len(fleet['routeViolations'])} catalog route violations; "
            f"{history['projectedTurns']} projected turns; "
            f"peak concurrency {history['peakCompletedTurnConcurrency']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
