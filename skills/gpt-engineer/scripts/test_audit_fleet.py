#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import audit_fleet


class AuditFleetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        state = sqlite3.connect(self.home / "state_5.sqlite")
        state.executescript(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY, agent_role TEXT, model TEXT, reasoning_effort TEXT,
                created_at INTEGER
            );
            CREATE TABLE thread_spawn_edges (
                parent_thread_id TEXT, child_thread_id TEXT PRIMARY KEY, status TEXT
            );
            """
        )
        rows = [
            ("root", None, "gpt-5.6-sol", "high", 90),
            ("a", "terra_explorer", "gpt-5.6-terra", "medium", 110),
            ("b", "security-auditor", "gpt-5.4", "high", 120),
            ("c", "luna_verifier", "gpt-5.6-luna", "medium", 130),
            ("d", "worker", "gpt-5.6-sol", "high", 140),
        ]
        state.executemany("INSERT INTO threads VALUES (?,?,?,?,?)", rows)
        state.executemany(
            "INSERT INTO thread_spawn_edges VALUES (?,?,?)",
            (
                ("root", "a", "open"),
                ("root", "b", "open"),
                ("a", "c", "open"),
                ("root", "d", "open"),
            ),
        )
        state.commit()
        state.close()

        history = sqlite3.connect(self.home / "thread_history_1.sqlite")
        history.execute(
            """
            CREATE TABLE thread_turns (
                thread_id TEXT, status TEXT, started_at INTEGER, completed_at INTEGER,
                duration_ms INTEGER
            )
            """
        )
        history.executemany(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?)",
            (("a", "completed", 111, 121, 10000), ("b", "completed", 115, 125, 10000)),
        )
        history.commit()
        history.close()

        logs = sqlite3.connect(self.home / "logs_2.sqlite")
        logs.execute("CREATE TABLE logs (ts INTEGER, thread_id TEXT)")
        logs.executemany("INSERT INTO logs VALUES (?,?)", ((112, "a"), (116, "b"), (140, None)))
        logs.commit()
        logs.close()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_audits_recursive_root_and_route_leakage(self) -> None:
        result = audit_fleet.audit(
            codex_home=self.home,
            since=datetime.fromtimestamp(100, timezone.utc),
            root_thread="root",
        )
        self.assertEqual(result["fleet"]["spawnedChildren"], 4)
        self.assertEqual(result["fleet"]["latestOnlyChildren"], 2)
        self.assertEqual(result["fleet"]["routeViolations"][0]["model"], "gpt-5.4")
        self.assertEqual(result["fleet"]["routeViolations"][1]["agentRole"], "worker")
        self.assertEqual(result["history"]["projectedTurns"], 2)
        self.assertEqual(result["history"]["peakCompletedTurnConcurrency"], 2)
        self.assertEqual(result["otelScope"], {"rows": 2, "threads": 2, "usageDeduplicated": False})
        self.assertEqual(result["fleet"]["spawnEdgeStatusCounts"], {"open": 4})
        self.assertTrue(any("not deduplicated" in item for item in result["limitations"]))

    def test_global_cohort_respects_since(self) -> None:
        result = audit_fleet.audit(
            codex_home=self.home,
            since=datetime.fromtimestamp(125, timezone.utc),
        )
        self.assertEqual(result["fleet"]["spawnedChildren"], 2)
        self.assertEqual(
            result["fleet"]["modelCounts"], {"gpt-5.6-luna": 1, "gpt-5.6-sol": 1}
        )

    def test_since_requires_timezone(self) -> None:
        with self.assertRaisesRegex(ValueError, "include a timezone"):
            audit_fleet.parse_since("2026-08-30T12:00:00")


if __name__ == "__main__":
    unittest.main()
