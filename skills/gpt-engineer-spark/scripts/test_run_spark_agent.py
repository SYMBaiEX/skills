#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_spark_agent


class RunSparkAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.output = Path(self.temp.name) / "output"
        self.codex = Path(self.temp.name) / "fake-codex"
        self.codex.write_text(
            """#!/usr/bin/env python3
import json
import pathlib
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
cwd = pathlib.Path(args[args.index("--cd") + 1])
if "MODEL_REJECT" in prompt:
    print(json.dumps({"type": "error", "message": "model unavailable"}))
    raise SystemExit(9)
if "TIMEOUT" in prompt:
    time.sleep(30)
if "LOCK_MARKER=" in prompt:
    marker = pathlib.Path(prompt.split("LOCK_MARKER=", 1)[1].splitlines()[0].strip())
    collision = marker.with_suffix(".collision")
    if marker.exists():
        collision.write_text("overlap")
    marker.write_text("active")
    time.sleep(0.4)
    marker.unlink(missing_ok=True)
if "WRITE_ALLOWED" in prompt:
    target = cwd / "src" / "generated.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("allowed\\n")
if "WRITE_OUTSIDE" in prompt:
    (cwd / "outside.txt").write_text("outside\\n")
if "WRITE_IGNORED" in prompt:
    (cwd / "ignored.txt").write_text("changed\\n")
if "READ_MUTATION" in prompt:
    (cwd / "read-mutation.txt").write_text("changed\\n")
if "TURN_FAILED" in prompt:
    output.write_text("partial\\n")
    print(json.dumps({"type": "turn.failed"}))
    raise SystemExit(0)
if "MISSING_FINAL" in prompt:
    print(json.dumps({"type": "turn.completed"}))
    raise SystemExit(0)
output.write_text("delegate complete\\n")
print(json.dumps({"type": "turn.completed"}))
"""
        )
        self.codex.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_pins_spark_and_read_only_sandbox(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Verify the repository.")):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                result = run_spark_agent.main(
                    [
                        "--role",
                        "spark-verifier",
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
        self.assertIn('"model": "gpt-5.3-codex-spark"', rendered)
        self.assertIn('"sandbox": "read-only"', rendered)
        self.assertNotIn("dangerously-bypass", rendered)

    def test_spark_worker_requires_explicit_write_authority(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Implement the bounded fix.")):
            with self.assertRaisesRegex(SystemExit, "requires --allow-writes"):
                run_spark_agent.main(
                    [
                        "--role",
                        "spark-worker",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                        "--dry-run",
                    ]
                )

    def test_captures_delegate_outputs(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-explorer",
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
        self.assertIn("gpt-5.3-codex-spark", command)
        self.assertIn("--ephemeral", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        result_json = json.loads((self.output / "result.json").read_text())
        self.assertEqual(result_json["status"], "completed")

    def test_writer_accepts_only_explicit_path_scope(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("WRITE_ALLOWED")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-worker",
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
        self.assertFalse((self.root / "src" / "generated.txt").exists())
        self.assertFalse(envelope["appliedToRepository"])
        changes = Path(envelope["candidateChangesDirectory"])
        self.assertEqual((changes / "src" / "generated.txt").read_text(), "allowed\n")

    def test_writer_fails_closed_on_out_of_scope_change(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("WRITE_OUTSIDE")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-worker",
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
        self.assertIn("out-of-scope candidate change: outside.txt", envelope["violations"])
        self.assertFalse((self.root / "outside.txt").exists())

    def test_writer_fails_closed_on_ignored_file_change(self) -> None:
        (self.root / ".gitignore").write_text("ignored.txt\n")
        (self.root / "ignored.txt").write_text("baseline\n")
        with mock.patch("sys.stdin", io.StringIO("WRITE_IGNORED")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-worker",
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
        self.assertIn("ignored.txt", envelope["changedPaths"])
        self.assertIn("out-of-scope candidate change: ignored.txt", envelope["violations"])
        self.assertEqual((self.root / "ignored.txt").read_text(), "baseline\n")

    def test_writer_refuses_external_symlink_targets(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("protected\n")
        (self.root / "external-link").symlink_to(outside)
        with mock.patch("sys.stdin", io.StringIO("Implement the bounded fix.")):
            with self.assertRaisesRegex(SystemExit, "symlinks that resolve outside"):
                run_spark_agent.main(
                    [
                        "--role",
                        "spark-worker",
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
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-explorer",
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

    def test_nonempty_output_directory_is_refused(self) -> None:
        self.output.mkdir()
        (self.output / "stale-result.json").write_text("{}")
        with mock.patch("sys.stdin", io.StringIO("Map the architecture.")):
            with self.assertRaisesRegex(SystemExit, "new or empty"):
                run_spark_agent.main(
                    [
                        "--role",
                        "spark-explorer",
                        "--cwd",
                        str(self.root),
                        "--output-dir",
                        str(self.output),
                        "--codex",
                        str(self.codex),
                    ]
                )

    def test_read_only_mutation_fails_closed(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("READ_MUTATION")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-explorer",
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
        self.assertIn("read-only delegate changed repository state", envelope["violations"])

    def test_model_rejection_does_not_fallback(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("MODEL_REJECT")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-explorer",
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
        self.assertEqual(envelope["requestedModel"], "gpt-5.3-codex-spark")
        command = json.loads((self.output / "args.json").read_text())
        self.assertEqual(command.count("gpt-5.3-codex-spark"), 1)

    def test_missing_final_message_fails_closed(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("MISSING_FINAL")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-verifier",
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
        self.assertEqual(envelope["status"], "failed")
        self.assertEqual(envelope["finalMessage"], "")

    def test_turn_failed_event_fails_closed(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("TURN_FAILED")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-verifier",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                ]
            )
        self.assertEqual(result, 1)
        self.assertEqual(json.loads((self.output / "result.json").read_text())["status"], "failed")

    def test_timeout_fails_closed(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("TIMEOUT")):
            result = run_spark_agent.main(
                [
                    "--role",
                    "spark-explorer",
                    "--cwd",
                    str(self.root),
                    "--output-dir",
                    str(self.output),
                    "--codex",
                    str(self.codex),
                    "--timeout",
                    "1",
                ]
            )
        self.assertEqual(result, 124)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertEqual(envelope["status"], "failed")

    def test_concurrent_writers_are_serialized_through_postflight(self) -> None:
        marker = Path(self.temp.name) / "writer-active"

        def invoke(name: str) -> int:
            prompt_file = Path(self.temp.name) / f"{name}.prompt"
            prompt_file.write_text(f"LOCK_MARKER={marker}\n")
            return run_spark_agent.main(
                [
                    "--role",
                    "spark-worker",
                    "--cwd",
                    str(self.root),
                    "--prompt-file",
                    str(prompt_file),
                    "--output-dir",
                    str(Path(self.temp.name) / name),
                    "--codex",
                    str(self.codex),
                    "--allow-writes",
                    "--allow-path",
                    "src",
                ]
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(invoke, ("writer-a", "writer-b")))
        self.assertEqual(results, [0, 0])
        self.assertFalse(marker.with_suffix(".collision").exists())


if __name__ == "__main__":
    unittest.main()
