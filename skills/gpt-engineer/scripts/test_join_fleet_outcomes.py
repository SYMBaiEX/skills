#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import join_fleet_outcomes as subject
import run_journal


class JoinFleetOutcomesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "run" / "journal.jsonl"
        self.journal.parent.mkdir()
        (self.journal.parent / "manifest.json").write_text(
            json.dumps({"schema": subject.JOURNAL_SCHEMA})
        )
        (self.journal.parent / "latest.json").write_text("{}")
        self.results = self.root / "results"
        self.results.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, events, result, name="a"):
        self.journal.write_text("\n".join(json.dumps(item) for item in events) + "\n")
        path = self.results / name
        path.mkdir(exist_ok=True)
        (path / "result.json").write_text(json.dumps(result))

    def test_join_and_separate_denominators(self):
        ident = {"runId": "r", "stageId": "s", "attempt": 1, "laneId": "l"}
        events = [
            {
                "schema": subject.JOURNAL_SCHEMA,
                "eventId": "d",
                "type": "dispatch.accepted",
                "data": {"model": "gpt-5.6-terra"},
                **ident,
            },
            {
                "schema": subject.JOURNAL_SCHEMA,
                "eventId": "o",
                "type": "finding.updated",
                "data": {"status": "implemented"},
                **ident,
            },
            {
                "schema": subject.JOURNAL_SCHEMA,
                "eventId": "v",
                "type": "verification.completed",
                "data": {"status": "passed"},
                **ident,
            },
        ]
        self.write(
            events,
            {
                **ident,
                "status": "completed",
                "requestedModel": "gpt-5.6-terra",
                "requestedReasoningEffort": "medium",
                "lifecycle": {"durationMs": 10},
            },
        )
        actual = subject.join(
            journals=[str(self.root)], result_dirs=[str(self.results)]
        )
        self.assertEqual(actual["denominators"]["dispatched"], 1)
        self.assertEqual(actual["denominators"]["outcome-eligible"], 1)
        self.assertEqual(actual["denominators"]["verified"], 1)
        self.assertEqual(actual["metrics"][0]["durationMs"]["p50"], 10)
        self.assertEqual(actual["journalLifecycle"]["runs"], 1)
        self.assertEqual(actual["journalLifecycle"]["closedRuns"], 0)
        self.assertEqual(actual["journalLifecycle"]["unclosedRuns"], 1)

    def test_real_run_journal_and_runner_envelope_join(self):
        repo = self.root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / "a").write_text("a")
        subprocess.run(["git", "add", "a"], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=a@b",
                "-c",
                "user.name=a",
                "commit",
                "-qm",
                "init",
            ],
            cwd=repo,
            check=True,
        )
        run = run_journal.start_run(
            repo, state_home=str(self.root / "state"), run_id="integration"
        )
        common = {"stage_id": "build", "attempt": 1}
        run.append(
            "stage.planned", data={"stageId": "build", "dependencies": []}, **common
        )
        run.append(
            "dispatch.accepted",
            data={
                "stageId": "build",
                "dispatchId": "d",
                "status": "running",
                "model": "gpt-5.6-terra",
            },
            **common,
        )
        run.append(
            "handoff.received",
            data={"stageId": "build", "dispatchId": "d", "status": "completed"},
            **common,
        )
        run.append(
            "finding.updated", data={"id": "F1", "status": "implemented"}, **common
        )
        run.append(
            "requirement.updated", data={"id": "R1", "status": "passed"}, **common
        )
        run.append(
            "verification.completed",
            data={"gateId": "Q1", "status": "passed"},
            **common,
        )
        run.append(
            "command.completed",
            data={"commandId": "t", "status": "completed"},
            **common,
        )
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        run.close("completed")
        result_dir = self.results / "real"
        result_dir.mkdir()
        (result_dir / "result.json").write_text(
            json.dumps(
                {
                    "role": "terra_worker",
                    "stageId": "build",
                    "requestedModel": "gpt-5.6-terra",
                    "requestedReasoningEffort": "medium",
                    "status": "completed",
                    "lifecycle": {
                        "attempt": 1,
                        "startedAtUtc": now,
                        "finishedAtUtc": now,
                        "durationMs": 42,
                    },
                }
            )
        )
        actual = subject.join(
            journals=[str(run.run_dir.parent)], result_dirs=[str(self.results)]
        )
        self.assertEqual(actual["denominators"]["dispatched"], 1)
        self.assertEqual(actual["denominators"]["routed"], 1)
        self.assertEqual(actual["denominators"]["projected"], 1)
        self.assertIsNone(actual["denominators"]["otel-covered"])
        self.assertEqual(actual["denominators"]["accepted"], 1)
        self.assertEqual(actual["denominators"]["implemented"], 1)
        self.assertEqual(actual["denominators"]["verified"], 1)
        rendered = json.dumps(actual)
        self.assertNotIn(str(repo), rendered)
        self.assertNotIn(str(run.run_dir), rendered)
        self.assertNotIn(str(result_dir), rendered)

    def test_missing_stores_and_default_redaction(self):
        actual = subject.join(journals=[], result_dirs=[])
        self.assertIsNone(actual["coverage"]["journalResult"])
        self.assertIsNone(actual["denominators"]["dispatched"])
        self.assertIsNone(actual["denominators"]["result-envelope"])
        self.assertEqual(actual["recommendation"], "insufficient-evidence")
        self.assertNotIn(str(self.root), json.dumps(actual))

    def test_optional_identifiers_change_only_identifier_fields(self):
        ident = {"runId": "sensitive-run", "stageId": "s", "attempt": 1, "laneId": "l"}
        self.write(
            [
                {
                    "schema": subject.JOURNAL_SCHEMA,
                    "eventId": "x",
                    "type": "outcome",
                    "outcome": {"accepted": True},
                    **ident,
                }
            ],
            {**ident, "status": "completed", "outcome": {"accepted": False}},
        )
        redacted = subject.join(
            journals=[str(self.root)], result_dirs=[str(self.results)]
        )
        exposed = subject.join(
            journals=[str(self.root)],
            result_dirs=[str(self.results)],
            include_identifiers=True,
        )
        self.assertNotIn("sensitive-run", json.dumps(redacted))
        self.assertIn("sensitive-run", json.dumps(exposed))
        self.assertEqual(redacted["denominators"], exposed["denominators"])

    def test_duplicate_and_conflict_fail_closed(self):
        ident = {"runId": "r", "stageId": "s", "attempt": 1, "laneId": "l"}
        self.write(
            [
                {
                    "schema": subject.JOURNAL_SCHEMA,
                    "eventId": "x",
                    "type": "outcome",
                    "outcome": {"accepted": True},
                    **ident,
                },
                {
                    "schema": subject.JOURNAL_SCHEMA,
                    "eventId": "x",
                    "type": "outcome",
                    "outcome": {"accepted": False},
                    **ident,
                },
            ],
            {**ident, "status": "completed", "outcome": {"accepted": False}},
        )
        actual = subject.join(
            journals=[str(self.root)], result_dirs=[str(self.results)]
        )
        self.assertEqual(actual["sources"]["journalDuplicates"], 1)
        self.assertEqual(actual["identityConflicts"], 1)
        self.assertEqual(actual["recommendation"], "insufficient-evidence")

    def test_malformed_schema_and_time_are_diagnosed(self):
        self.journal.write_text('{"eventId":"a","timestamp":"bad"}\nnot-json\n')
        actual = subject.join(journals=[str(self.root)], result_dirs=[])
        self.assertTrue(
            any(
                item["code"] == "malformed-terminated-journal-line"
                for item in actual["diagnostics"]
            )
        )

    def test_partial_terminated_unknown_schema_and_cli(self):
        self.journal.write_bytes(b"{bad}\n{bad")
        actual = subject.join(journals=[str(self.root)], result_dirs=[])
        codes = {item["code"] for item in actual["diagnostics"]}
        self.assertIn("malformed-terminated-journal-line", codes)
        self.assertIn("partial-journal-tail", codes)
        (self.journal.parent / "manifest.json").write_text('{"schema":"unknown/v1"}')
        actual = subject.join(journals=[str(self.root)], result_dirs=[])
        self.assertTrue(
            any(
                item["code"] == "unknown-or-missing-journal-schema"
                for item in actual["diagnostics"]
            )
        )
        script = Path(subject.__file__)
        self.assertEqual(
            subprocess.run(
                ["python3", str(script), "--help"],
                capture_output=True,
                text=True,
                check=False,
            ).returncode,
            0,
        )
        cli = subprocess.run(
            ["python3", str(script), "--journal", str(self.root), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0)
        self.assertEqual(json.loads(cli.stdout)["schema"], subject.SCHEMA)
        (self.journal.parent / "manifest.json").write_bytes(b"\xff")
        actual = subject.join(journals=[str(self.root)], result_dirs=[])
        self.assertTrue(
            any(item["code"] == "malformed-json" for item in actual["diagnostics"])
        )

    def test_safeguards_shrink_and_team_no_expand(self):
        events = []
        for i in range(5):
            ident = {"runId": f"r{i}", "stageId": "s", "attempt": 1, "laneId": "l"}
            events.append(
                {
                    "schema": subject.JOURNAL_SCHEMA,
                    "eventId": str(i),
                    "type": "outcome",
                    "outcome": {"accepted": True, "verified": True},
                    **ident,
                }
            )
            p = self.results / f"r{i}"
            p.mkdir()
            (p / "result.json").write_text(
                json.dumps(
                    {
                        **ident,
                        "status": "failed" if i else "completed",
                        "mode": "Team",
                        "independentReadyWork": True,
                        "meaningfulWallTimeOrYieldImprovement": True,
                    }
                )
            )
        self.journal.write_text("\n".join(json.dumps(e) for e in events))
        actual = subject.join(
            journals=[str(self.root)],
            result_dirs=[str(self.results)],
            min_comparable_pairs=0,
        )
        self.assertEqual(actual["recommendation"], "shrink")

    def test_expand_requires_pairs_and_never_recommends_team(self):
        events = []
        for i in range(6):
            ident = {"runId": f"r{i}", "stageId": "s", "attempt": 1, "laneId": f"l{i}"}
            events.append(
                {
                    "schema": subject.JOURNAL_SCHEMA,
                    "eventId": str(i),
                    "type": "outcome",
                    "outcome": {"accepted": True, "verified": True},
                    **ident,
                }
            )
            p = self.results / f"r{i}"
            p.mkdir()
            mode = "Broad" if i < 3 else "Standard"
            (p / "result.json").write_text(
                json.dumps(
                    {
                        **ident,
                        "status": "completed",
                        "requestedModel": "gpt-5.6-terra",
                        "requestedReasoningEffort": "medium",
                        "mode": mode,
                        "taskClass": "review",
                        "acceptanceContractHash": "a" * 64,
                        "remainingRouteContext": {"repo": "hashed"},
                        "independentReadyWork": i < 3,
                        "meaningfulWallTimeOrYieldImprovement": i < 3,
                    }
                )
            )
        self.journal.write_text("\n".join(json.dumps(e) for e in events))
        self.assertEqual(
            subject.join(journals=[str(self.root)], result_dirs=[str(self.results)])[
                "recommendation"
            ],
            "expand",
        )
        for result in self.results.rglob("result.json"):
            item = json.loads(result.read_text())
            item["mode"] = "Team"
            result.write_text(json.dumps(item))
        self.assertNotEqual(
            subject.join(
                journals=[str(self.root)],
                result_dirs=[str(self.results)],
                min_comparable_pairs=0,
            )["recommendation"],
            "expand",
        )

    def _comparison_run(self, effort, outcome, duration):
        return {
            "complete": True,
            "outcome": outcome,
            "route": "gpt-5.6-terra",
            "effort": effort,
            "mode": "Fast",
            "taskClass": "test",
            "acceptanceContractHash": "c" * 64,
            "remainingRouteContext": json.dumps({"profile": "worker"}),
            "result": {"status": "completed", "durationMs": duration},
        }

    def test_comparability_and_effort_recommendations(self):
        low = self._comparison_run("low", {"accepted": True, "verified": True}, 80)
        high = self._comparison_run("high", {"accepted": True, "verified": True}, 120)
        self.assertEqual(
            subject.recommendation([low, high], 1.0, 2, 1, 0), "lower-effort"
        )
        low["taskClass"] = None
        self.assertEqual(subject.recommendation([low, high], 1.0, 2, 1, 0), "hold")
        low["taskClass"] = "test"
        low["outcome"] = {"accepted": False, "verified": False}
        self.assertEqual(
            subject.recommendation([low, high], 1.0, 2, 1, 0), "raise-effort"
        )
        low["remainingRouteContext"] = None
        self.assertEqual(subject.recommendation([low, high], 1.0, 2, 1, 0), "hold")
        low = self._comparison_run("low", {"accepted": True, "verified": True}, 80)
        high = self._comparison_run("high", {"accepted": True, "verified": True}, 120)
        unrelated = self._comparison_run(
            "medium", {"accepted": True, "verified": True}, 100
        )
        unrelated["route"] = "gpt-5.6-luna"
        self.assertEqual(
            subject.recommendation([low, high, unrelated], 1.0, 3, 2, 0), "hold"
        )

    def test_audit_denominators_and_threshold_validation(self):
        audit = {
            "schema": "gpt-engineer-fleet-audit/v1",
            "rootThread": "sensitive-root",
            "fleet": {
                "parentCounts": {"sensitive-parent": 2},
                "routeViolations": [{"threadId": "sensitive-child"}],
            },
            "history": {"projectedThreads": 7},
            "otelScope": {"threads": 5},
        }
        with patch.object(subject, "audit_if_requested", return_value=audit):
            actual = subject.join(journals=[], result_dirs=[], codex_home="/hidden")
        self.assertNotIn("sensitive-root", json.dumps(actual["audit"]))
        self.assertNotIn("sensitive-parent", json.dumps(actual["audit"]))
        self.assertNotIn("sensitive-child", json.dumps(actual["audit"]))
        self.assertEqual(actual["denominators"]["projected"], 7)
        self.assertEqual(actual["denominators"]["otel-covered"], 5)
        with self.assertRaisesRegex(ValueError, "positive"):
            subject.join(journals=[], result_dirs=[], min_complete_runs=0)
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            subject.join(journals=[], result_dirs=[], min_comparable_pairs=-1)
        with self.assertRaisesRegex(ValueError, "after --since"):
            subject.join(
                journals=[],
                result_dirs=[],
                since="2026-09-04T20:25:24Z",
                snapshot_end="2026-09-04T20:25:24Z",
            )

    def test_snapshot_end_is_exclusive_for_journal_events(self):
        event = {
            "schema": subject.JOURNAL_SCHEMA,
            "eventId": "edge",
            "runId": "r",
            "type": "run.started",
            "occurredAtUtc": "2026-09-04T20:25:24Z",
            "data": {},
        }
        self.journal.write_text(json.dumps(event) + "\n")
        actual = subject.join(
            journals=[str(self.root)],
            result_dirs=[],
            since="2026-09-04T20:25:23Z",
            snapshot_end="2026-09-04T20:25:24Z",
        )
        self.assertEqual(actual["journalLifecycle"]["runs"], 0)

    def test_bounded_window_rejects_undated_journal_events(self):
        event = {
            "schema": subject.JOURNAL_SCHEMA,
            "eventId": "undated",
            "runId": "r",
            "type": "run.started",
            "data": {},
        }
        self.journal.write_text(json.dumps(event) + "\n")
        actual = subject.join(
            journals=[str(self.root)],
            result_dirs=[],
            snapshot_end="2026-09-04T20:25:24Z",
        )
        self.assertEqual(actual["window"]["sinceUtc"], "2026-08-28T20:25:24Z")
        self.assertEqual(actual["journalLifecycle"]["runs"], 0)
        self.assertTrue(
            any(
                item["code"] == "missing-timestamp-in-bounded-window"
                for item in actual["diagnostics"]
            )
        )


if __name__ == "__main__":
    unittest.main()
