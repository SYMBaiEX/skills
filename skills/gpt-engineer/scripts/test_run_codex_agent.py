#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import join_fleet_outcomes
import run_codex_agent


class RunCodexAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.output = Path(self.temp.name) / "output"
        self.state_home = Path(self.temp.name) / "state"
        self.environment = mock.patch.dict(
            os.environ,
            {
                "XDG_STATE_HOME": str(self.state_home),
                "GPT_ENGINEER_CLI_ADAPTER_REASON": "native-routing-unavailable",
            },
        )
        self.environment.start()
        self.codex = Path(self.temp.name) / "fake-codex"
        self.codex.write_text(
            """#!/usr/bin/env python3
import json
import pathlib
import re
import subprocess
import sys
import time

args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 9.9.9")
    raise SystemExit(0)
output = pathlib.Path(args[args.index("--output-last-message") + 1])
output.parent.mkdir(parents=True, exist_ok=True)
(output.parent / "args.json").write_text(json.dumps(args))
prompt = sys.stdin.read()
if "HANG" in prompt:
    time.sleep(5)
stage_match = re.search(r"Set stage_id to '([^']+)'", prompt)
stage_id = stage_match.group(1) if stage_match else "unknown"
handoff = {
    "stage_id": stage_id,
    "status": "completed",
    "summary": "delegate complete",
    "requirement_ids": [],
    "gate_results": [],
    "docs_disposition": {
        "status": "not_applicable",
        "detail": "No documentation gate was assigned."
    },
    "evidence": [],
    "changed_paths": [],
    "checks": [],
    "blockers": [],
    "next_action": "Return to the parent.",
}
if "INCOMPLETE_HANDOFF" in prompt:
    handoff.pop("gate_results")
output.write_text(json.dumps(handoff) + "\\n")
cwd = pathlib.Path(args[args.index("--cd") + 1])
if "WRITE_ALLOWED" in prompt:
    target = cwd / "src" / "generated.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("allowed\\n")
if "WRITE_OUTSIDE" in prompt:
    (cwd / "outside.txt").write_text("outside\\n")
if "WRITE_IGNORED" in prompt:
    (cwd / "ignored.txt").write_text("changed\\n")
if "COMMIT_CHANGE" in prompt:
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(["git", "-c", "user.name=Delegate", "-c", "user.email=delegate@example.com", "commit", "-qm", "delegate commit"], cwd=cwd, check=True)
if "SPAM_STDOUT" in prompt:
    print("x" * 4096)
print(json.dumps({"type": "turn.completed"}))
"""
        )
        self.codex.chmod(0o755)

    def tearDown(self) -> None:
        self.environment.stop()
        self.temp.cleanup()

    def test_handoff_schema_requires_engineering_evidence_fields(self) -> None:
        schema = json.loads(run_codex_agent.HANDOFF_SCHEMA.read_text())
        required = set(schema["required"])
        self.assertTrue(
            {"requirement_ids", "gate_results", "docs_disposition"}.issubset(required)
        )
        statuses = set(
            schema["properties"]["gate_results"]["items"]["properties"]["status"][
                "enum"
            ]
        )
        self.assertIn("skipped", statuses)

    def test_requires_explicit_compatibility_reason(self) -> None:
        with mock.patch.dict(
            os.environ, {"GPT_ENGINEER_CLI_ADAPTER_REASON": ""}, clear=False
        ):
            with self.assertRaisesRegex(SystemExit, "2"):
                run_codex_agent.main(
                    [
                        "--role",
                        "terra-explorer",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )

    def test_local_schema_validation_rejects_provider_omission(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("INCOMPLETE_HANDOFF")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                ]
            )
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertTrue(
            any(
                "missing required property 'gate_results'" in violation
                for violation in envelope["violations"]
            )
        )

    def test_dry_run_pins_luna_and_read_only_sandbox(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Verify the repository.")):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                result = run_codex_agent.main(
                    [
                        "--role",
                        "luna-verifier",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )
        self.assertEqual(result, 0)
        rendered = stdout.getvalue()
        self.assertIn('"model": "gpt-5.6-luna"', rendered)
        self.assertIn('"reasoningEffort": "medium"', rendered)
        self.assertIn('"sandbox": "read-only"', rendered)
        self.assertNotIn("dangerously-bypass", rendered)
        self.assertIn("--output-schema", rendered)

    def test_terra_worker_requires_explicit_write_authority(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Implement the bounded fix.")):
            with self.assertRaisesRegex(SystemExit, "requires --allow-writes"):
                run_codex_agent.main(
                    [
                        "--role",
                        "terra-worker",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )

    def test_luna_worker_is_low_effort_and_requires_write_authority(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Implement the mechanical fix.")):
            with self.assertRaisesRegex(
                SystemExit, "luna-worker requires --allow-writes"
            ):
                run_codex_agent.main(
                    [
                        "--role",
                        "luna-worker",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )

    def test_luna_max_worker_pins_fast_tier_and_requires_write_authority(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Implement the dense bounded fix.")):
            with self.assertRaisesRegex(
                SystemExit, "luna-max-worker requires --allow-writes"
            ):
                run_codex_agent.main(
                    [
                        "--role",
                        "luna-max-worker",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )
        with mock.patch("sys.stdin", io.StringIO("Implement the dense bounded fix.")):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                result = run_codex_agent.main(
                    [
                        "--role",
                        "luna-max-worker",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--allow-writes",
                        "--allow-path",
                        "src",
                        "--dry-run",
                    ]
                )
        self.assertEqual(result, 0)
        rendered = stdout.getvalue()
        self.assertIn('"reasoningEffort": "max"', rendered)
        self.assertIn('"serviceTier": "fast"', rendered)
        self.assertIn('service_tier=\\"fast\\"', rendered)
        self.assertIn("features.fast_mode=true", rendered)

    def test_captures_delegate_outputs(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("turn.completed", (self.output / "events.jsonl").read_text())
        command = json.loads((self.output / "args.json").read_text())
        self.assertIn("gpt-5.6-terra", command)
        self.assertIn("--ephemeral", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        result_json = json.loads((self.output / "result.json").read_text())
        self.assertEqual(
            result_json["executionSurface"], "codex-cli-compatibility-adapter"
        )
        self.assertEqual(
            result_json["compatibilityReason"], "native-routing-unavailable"
        )
        self.assertEqual(result_json["status"], "completed")
        self.assertEqual(result_json["handoff"]["stage_id"], "terra-explorer")
        self.assertEqual(result_json["requestedReasoningEffort"], "medium")
        self.assertIsNone(result_json["effectiveModel"])
        self.assertEqual(result_json["routeAttestation"], "requested-only")
        self.assertTrue(result_json["routeEvidence"]["ignoredUserConfig"])
        self.assertFalse(
            result_json["routeEvidence"]["providerEffectiveModelAttested"]
        )
        self.assertEqual(result_json["lifecycle"]["attempt"], 1)
        self.assertEqual(result_json["lifecycle"]["terminalState"], "completed")
        self.assertTrue(result_json["lifecycle"]["cleanupVerified"])
        self.assertTrue(result_json["lifecycle"]["completionEventObserved"])
        self.assertGreaterEqual(result_json["lifecycle"]["durationMs"], 0)
        self.assertRegex(result_json["lifecycle"]["startedAtUtc"], r"Z$")
        self.assertRegex(result_json["lifecycle"]["finishedAtUtc"], r"Z$")
        self.assertIsNotNone(result_json["runId"])
        self.assertEqual(result_json["journal"]["status"], "closed")
        self.assertFalse((self.root / ".engineer").exists())
        journal = run_codex_agent.run_journal.open_run(
            self.root, result_json["runId"], state_home=str(self.state_home)
        )
        event_types = [
            event["type"] for event in journal._journal._events(journal.run_dir)
        ]
        self.assertEqual(
            event_types,
            [
                "run.started",
                "stage.planned",
                "dispatch.accepted",
                "handoff.received",
                "run.closed",
            ],
        )
        handoff_event = next(
            event
            for event in journal._journal._events(journal.run_dir)
            if event["type"] == "handoff.received"
        )
        self.assertLessEqual(
            datetime.fromisoformat(
                handoff_event["occurredAtUtc"].replace("Z", "+00:00")
            ),
            datetime.fromisoformat(
                result_json["lifecycle"]["finishedAtUtc"].replace("Z", "+00:00")
            ),
        )
        joined = join_fleet_outcomes.join(
            journals=[str(journal.run_dir.parent)],
            result_dirs=[str(self.output)],
        )
        self.assertEqual(joined["coverage"]["journalResult"], 1.0)
        self.assertEqual(joined["denominators"]["projected"], 1)
        self.assertFalse(any(self.output.glob(".result-*")))

    def test_attaches_to_shared_run_without_closing_it(self) -> None:
        shared = run_codex_agent.run_journal.start_run(
            self.root,
            state_home=str(self.state_home),
            objective_summary="Shared fleet",
        )
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--stage-id",
                    "map-api",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--journal-run-id",
                    shared.run_id,
                    "--journal-lane-id",
                    "lane-2",
                    "--journal-attempt",
                    "2",
                    "--task-class",
                    "architecture-map",
                    "--acceptance-contract-hash",
                    "contract-v1",
                    "--route-context-json",
                    '{"scope":"api"}',
                ]
            )
        self.assertEqual(result, 0)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["runId"], shared.run_id)
        self.assertEqual(envelope["laneId"], "lane-2")
        self.assertEqual(envelope["attempt"], 2)
        self.assertFalse(envelope["journal"]["ownedRun"])
        self.assertFalse(shared.status()["closed"])
        self.assertEqual(shared.status()["stages"]["map-api"]["status"], "completed")

    def test_shared_run_refuses_duplicate_stage_attempt(self) -> None:
        shared = run_codex_agent.run_journal.start_run(
            self.root, state_home=str(self.state_home), objective_summary="Shared fleet"
        )
        shared.append(
            "stage.planned",
            stage_id="map-api",
            attempt=1,
            data={"stageId": "map-api", "dependencies": []},
        )
        shared.append(
            "dispatch.accepted",
            stage_id="map-api",
            attempt=1,
            data={
                "stageId": "map-api",
                "dispatchId": f"{shared.run_id}:map-api:1",
                "status": "completed",
            },
        )
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            with self.assertRaisesRegex(
                SystemExit, "already contains this stage attempt"
            ):
                run_codex_agent.main(
                    [
                        "--role",
                        "terra-explorer",
                        "--stage-id",
                        "map-api",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--journal-run-id",
                        shared.run_id,
                    ]
                )
        self.assertFalse(self.output.joinpath("events.jsonl").exists())

    def test_journal_failure_is_explicit_without_discarding_valid_handoff(self) -> None:
        target = Path(self.temp.name) / "unsafe-target"
        target.mkdir()
        unsafe = Path(self.temp.name) / "unsafe-state"
        unsafe.symlink_to(target)
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--journal-state-home",
                    str(unsafe),
                ]
            )
        self.assertEqual(result, 0)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["status"], "completed")
        self.assertIsNone(envelope["runId"])
        self.assertEqual(envelope["journal"]["status"], "error")
        self.assertIn("JournalError", envelope["journalError"])

    def test_journal_can_be_disabled_explicitly(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--journal-backend",
                    "off",
                ]
            )
        self.assertEqual(result, 0)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertIsNone(envelope["runId"])
        self.assertEqual(envelope["journal"]["status"], "off")

    def test_writer_accepts_only_explicit_path_scope(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("WRITE_ALLOWED")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-worker",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--allow-writes",
                    "--allow-path",
                    "src",
                ]
            )
        self.assertEqual(result, 0)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["changedPaths"], ["src/generated.txt"])
        self.assertFalse(envelope["appliedToRepository"])
        self.assertFalse((self.root / "src" / "generated.txt").exists())
        self.assertEqual(
            (
                Path(envelope["candidateChangesDirectory"]) / "src" / "generated.txt"
            ).read_text(),
            "allowed\n",
        )
        self.assertTrue(Path(envelope["candidatePatch"]).is_file())
        self.assertFalse((self.output / "candidate-worktree").exists())

    def test_writer_fails_closed_on_out_of_scope_change(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("WRITE_OUTSIDE")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "sol-engineer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--allow-writes",
                    "--allow-path",
                    "src",
                ]
            )
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertIn(
            "out-of-scope candidate change: outside.txt", envelope["violations"]
        )

    def test_writer_commit_fails_closed_but_preserves_candidate_patch(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("WRITE_ALLOWED COMMIT_CHANGE")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-worker",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--allow-writes",
                    "--allow-path",
                    "src",
                ]
            )
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertIn(
            "candidate delegate created one or more commits", envelope["violations"]
        )
        self.assertNotEqual(
            envelope["candidateBaselineCommit"], envelope["candidateHeadCommit"]
        )
        self.assertIn("src/generated.txt", Path(envelope["candidatePatch"]).read_text())

    def test_writer_excludes_ignored_files_from_candidate_tracking(self) -> None:
        (self.root / ".gitignore").write_text("ignored.txt\n")
        (self.root / "ignored.txt").write_text("baseline\n")
        with mock.patch("sys.stdin", io.StringIO("WRITE_IGNORED")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "sol-engineer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--allow-writes",
                    "--allow-path",
                    "src",
                ]
            )
        self.assertEqual(result, 0)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertNotIn("ignored.txt", envelope["changedPaths"])
        self.assertEqual((self.root / "ignored.txt").read_text(), "baseline\n")

    def test_writer_refuses_external_symlink_targets(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("protected\n")
        (self.root / "external-link").symlink_to(outside)
        with mock.patch("sys.stdin", io.StringIO("Implement the bounded fix.")):
            with self.assertRaisesRegex(SystemExit, "symlinks that resolve outside"):
                run_codex_agent.main(
                    [
                        "--role",
                        "sol-engineer",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--allow-writes",
                        "--allow-path",
                        "src",
                    ]
                )

    def test_launch_failure_writes_result_envelope(self) -> None:
        missing = Path(self.temp.name) / "missing-codex"
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(missing),
                ]
            )
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["status"], "failed")
        self.assertIsNone(envelope["exitCode"])
        self.assertIn("Failed to launch Codex delegate", envelope["launchError"])
        self.assertEqual(envelope["lifecycle"]["terminalState"], "launch_failed")
        self.assertTrue(envelope["lifecycle"]["cleanupVerified"])

    def test_timeout_reaps_process_group_and_records_lifecycle(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("HANG")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--timeout",
                    "0",
                ]
            )
        self.assertEqual(result, 124)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["lifecycle"]["terminalState"], "timed_out")
        self.assertTrue(envelope["lifecycle"]["timedOut"])
        self.assertTrue(envelope["lifecycle"]["cleanupVerified"])
        self.assertFalse(envelope["lifecycle"]["completionEventObserved"])

    def test_rejects_oversized_prompt_before_launch(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("01234567890")):
            with self.assertRaisesRegex(SystemExit, "limit is 10"):
                run_codex_agent.main(
                    [
                        "--role",
                        "terra-explorer",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--max-prompt-chars",
                        "10",
                    ]
                )

    def test_fails_closed_when_event_capture_is_truncated(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("SPAM_STDOUT")):
            result = run_codex_agent.main(
                [
                    "--role",
                    "terra-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--max-events-bytes",
                    "128",
                ]
            )
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertTrue(envelope["lifecycle"]["eventsTruncated"])
        self.assertGreater(envelope["lifecycle"]["eventsBytes"], 128)
        self.assertTrue(
            any("events exceeded" in item for item in envelope["violations"])
        )


if __name__ == "__main__":
    unittest.main()
