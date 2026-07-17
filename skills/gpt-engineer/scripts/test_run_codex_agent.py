#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_codex_agent


class RunCodexAgentTests(unittest.TestCase):
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
import subprocess
import sys

args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 9.9.9")
    raise SystemExit(0)
output = pathlib.Path(args[args.index("--output-last-message") + 1])
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("delegate complete\\n")
(output.parent / "args.json").write_text(json.dumps(args))
prompt = sys.stdin.read()
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
print(json.dumps({"type": "turn.completed"}))
"""
        )
        self.codex.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

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
        self.assertIn('"sandbox": "read-only"', rendered)
        self.assertNotIn("dangerously-bypass", rendered)

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
        self.assertEqual(result_json["status"], "completed")

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
            (Path(envelope["candidateChangesDirectory"]) / "src" / "generated.txt").read_text(),
            "allowed\n",
        )
        self.assertTrue(Path(envelope["candidatePatch"]).is_file())

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
        self.assertIn("out-of-scope candidate change: outside.txt", envelope["violations"])

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
        self.assertIn("candidate delegate created one or more commits", envelope["violations"])
        self.assertNotEqual(envelope["candidateBaselineCommit"], envelope["candidateHeadCommit"])
        self.assertIn("src/generated.txt", Path(envelope["candidatePatch"]).read_text())

    def test_writer_fails_closed_on_ignored_file_change(self) -> None:
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
        self.assertEqual(result, 1)
        envelope = json.loads((self.output / "result.json").read_text())
        self.assertIn("ignored.txt", envelope["changedPaths"])
        self.assertIn("out-of-scope candidate change: ignored.txt", envelope["violations"])

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


if __name__ == "__main__":
    unittest.main()
