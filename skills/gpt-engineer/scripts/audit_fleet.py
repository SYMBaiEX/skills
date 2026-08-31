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


ALLOWED_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
ALLOWED_ROLES = {
    "sol_engineer",
    "terra_explorer",
    "terra_worker",
    "luna_worker",
    "luna_max_worker",
    "luna_verifier",
    # Historical profile names retained so older exact-model runs remain auditable.
    "gpt-engineer-lead",
    "gpt-engineer-explorer",
    "gpt-engineer-worker",
    "gpt-engineer-verifier",
}


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
    state: sqlite3.Connection, since_epoch: int, root_thread: str | None
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
            WHERE t.created_at >= ?
            ORDER BY t.created_at, t.id
        """
        return list(state.execute(query, (root_thread, since_epoch)))
    return list(
        state.execute(
            """
            SELECT t.id, t.agent_role, t.model, t.reasoning_effort, t.created_at,
                   e.parent_thread_id, e.status AS spawn_status
            FROM threads t
            JOIN thread_spawn_edges e ON e.child_thread_id = t.id
            WHERE t.created_at >= ?
            ORDER BY t.created_at, t.id
            """,
            (since_epoch,),
        )
    )


def load_turns(history: sqlite3.Connection, thread_ids: list[str]) -> list[sqlite3.Row]:
    if not thread_ids or not table_exists(history, "thread_turns"):
        return []
    history.execute("CREATE TEMP TABLE selected_threads(id TEXT PRIMARY KEY)")
    history.executemany("INSERT INTO selected_threads(id) VALUES (?)", ((item,) for item in thread_ids))
    return list(
        history.execute(
            """
            SELECT t.thread_id, t.status, t.started_at, t.completed_at, t.duration_ms
            FROM thread_turns t JOIN selected_threads s ON s.id = t.thread_id
            ORDER BY t.started_at, t.thread_id
            """
        )
    )


def audit(
    *,
    codex_home: Path,
    since: datetime,
    root_thread: str | None = None,
) -> dict[str, object]:
    state_path = codex_home / "state_5.sqlite"
    history_path = codex_home / "thread_history_1.sqlite"
    logs_path = codex_home / "logs_2.sqlite"
    if not state_path.is_file():
        raise FileNotFoundError(f"missing Codex state database: {state_path}")

    state = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    state.row_factory = sqlite3.Row
    try:
        rows = cohort_rows(state, int(since.timestamp()), root_thread)
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
            turns = load_turns(history, thread_ids)
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
                    WHERE l.ts >= ?
                    """,
                    (int(since.timestamp()),),
                ).fetchone()
        finally:
            logs.close()

    model_counts = Counter(str(row["model"] or "(missing)") for row in rows)
    role_counts = Counter(str(row["agent_role"] or "(missing)") for row in rows)
    parent_counts = Counter(str(row["parent_thread_id"]) for row in rows)
    spawn_status_counts = Counter(str(row["spawn_status"]) for row in rows)
    route_violations = []
    for row in rows:
        reasons = []
        if row["model"] not in ALLOWED_MODELS:
            reasons.append("model outside GPT-5.6 latest-only allowlist")
        if row["agent_role"] not in ALLOWED_ROLES:
            reasons.append("generic or unsupported agent role")
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
    statuses = Counter(str(row["status"]) for row in turns)
    completed = [row for row in turns if row["status"] == "completed" and row["duration_ms"] is not None]
    durations = [int(row["duration_ms"]) for row in completed]
    intervals = [
        (int(row["started_at"]), int(row["completed_at"]))
        for row in completed
        if row["started_at"] is not None and row["completed_at"] is not None
    ]
    warnings: list[str] = []
    since_epoch = int(since.timestamp())
    for label, item in (("OTel", logs_coverage), ("turn history", history_coverage)):
        minimum = item.get("minUtc")
        if minimum and datetime.fromisoformat(str(minimum).replace("Z", "+00:00")).timestamp() > since_epoch:
            warnings.append(f"{label} retention starts after the requested window")
    if route_violations:
        warnings.append("one or more spawned children violated the latest-only role/model allowlist")

    return {
        "schema": "gpt-engineer-fleet-audit/v1",
        "requestedSinceUtc": since.isoformat().replace("+00:00", "Z"),
        "rootThread": root_thread,
        "coverage": {
            "state": state_coverage,
            "otel": logs_coverage,
            "history": history_coverage,
        },
        "fleet": {
            "spawnedChildren": len(rows),
            "latestOnlyChildren": len(rows) - len(route_violations),
            "modelCounts": dict(model_counts.most_common()),
            "roleCounts": dict(role_counts.most_common()),
            "parentCounts": dict(parent_counts.most_common()),
            "spawnEdgeStatusCounts": dict(spawn_status_counts.most_common()),
            "routeViolations": route_violations,
        },
        "history": {
            "projectedTurns": len(turns),
            "projectedThreads": len({str(row["thread_id"]) for row in turns}),
            "statusCounts": dict(statuses.most_common()),
            "completedDurationMs": {
                "p50": percentile(durations, 0.50),
                "p90": percentile(durations, 0.90),
                "p95": percentile(durations, 0.95),
                "max": max(durations) if durations else None,
            },
            "peakCompletedTurnConcurrency": peak_concurrency(intervals),
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
    parser.add_argument("--root-thread", help="Limit the cohort to descendants of one root thread")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(
            codex_home=Path(args.codex_home).expanduser().resolve(),
            since=parse_since(args.since),
            root_thread=args.root_thread,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        fleet = result["fleet"]
        history = result["history"]
        print(
            f"{fleet['spawnedChildren']} children; {len(fleet['routeViolations'])} route violations; "
            f"{history['projectedTurns']} projected turns; "
            f"peak concurrency {history['peakCompletedTurnConcurrency']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
