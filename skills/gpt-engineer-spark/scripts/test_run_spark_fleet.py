#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import run_spark_fleet


class RunSparkFleetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.output = self.base / "output"
        self.manifest = self.base / "manifest.json"
        self.codex = self.base / "fake-codex"
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
prompt = sys.stdin.read()
if "FORCE_FAIL" in prompt:
    print(json.dumps({"type": "turn.failed"}))
    raise SystemExit(7)
fleet_root = output.parent.parent
if "BARRIER_A" in prompt or "BARRIER_B" in prompt:
    mine = "a.ready" if "BARRIER_A" in prompt else "b.ready"
    other = "b.ready" if "BARRIER_A" in prompt else "a.ready"
    (fleet_root / mine).write_text("ready")
    deadline = time.monotonic() + 3
    while not (fleet_root / other).exists():
        if time.monotonic() >= deadline:
            print(json.dumps({"type": "turn.failed"}))
            raise SystemExit(8)
        time.sleep(0.02)
output.write_text("delegate complete\\n")
print(json.dumps({"type": "turn.completed"}))
"""
        )
        self.codex.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self, tasks: list[dict[str, object]]) -> None:
        self.manifest.write_text(json.dumps({"tasks": tasks}))

    def run_fleet(self, *extra: str) -> int:
        return run_spark_fleet.main(
            [
                "--manifest",
                str(self.manifest),
                "--cwd",
                str(self.root),
                "--output-dir",
                str(self.output),
                "--codex",
                str(self.codex),
                *extra,
            ]
        )

    def test_read_only_children_overlap_and_pin_spark(self) -> None:
        self.write_manifest(
            [
                {"id": "a", "role": "spark-explorer", "wave": 0, "prompt": "BARRIER_A"},
                {"id": "b", "role": "spark-verifier", "wave": 0, "prompt": "BARRIER_B"},
            ]
        )
        result = self.run_fleet("--max-parallel", "2")
        self.assertEqual(result, 0, (self.output / "fleet-result.json").read_text())
        envelope = json.loads((self.output / "fleet-result.json").read_text())
        self.assertEqual(envelope["status"], "completed")
        self.assertEqual(envelope["requiredModel"], "gpt-5.3-codex-spark")
        self.assertEqual(len(envelope["delegates"]), 2)
        self.assertTrue(all(item["serverAcceptedRequest"] for item in envelope["delegates"]))

    def test_required_failure_stops_later_waves(self) -> None:
        self.write_manifest(
            [
                {"id": "fail", "role": "spark-explorer", "wave": 0, "prompt": "FORCE_FAIL"},
                {"id": "later", "role": "spark-verifier", "wave": 1, "prompt": "SHOULD_NOT_RUN"},
            ]
        )
        self.assertEqual(self.run_fleet(), 1)
        envelope = json.loads((self.output / "fleet-result.json").read_text())
        self.assertEqual(envelope["status"], "incomplete")
        self.assertEqual(envelope["stoppedAfterWave"], 0)
        self.assertEqual(envelope["skippedTaskIds"], ["later"])

    def test_worker_requires_fleet_write_authority(self) -> None:
        self.write_manifest(
            [
                {
                    "id": "worker",
                    "role": "spark-worker",
                    "wave": 0,
                    "prompt": "IMPLEMENT",
                    "allowPaths": ["src"],
                }
            ]
        )
        with self.assertRaisesRegex(SystemExit, "fleet-level --allow-writes"):
            self.run_fleet()

    def test_mixed_reader_writer_wave_is_refused(self) -> None:
        self.write_manifest(
            [
                {"id": "read", "role": "spark-explorer", "wave": 0, "prompt": "READ"},
                {
                    "id": "write",
                    "role": "spark-worker",
                    "wave": 0,
                    "prompt": "WRITE",
                    "allowPaths": ["src"],
                },
            ]
        )
        with self.assertRaisesRegex(SystemExit, "Do not mix readers and writers"):
            self.run_fleet("--allow-writes")

    def test_nonempty_output_directory_is_refused(self) -> None:
        self.write_manifest(
            [{"id": "read", "role": "spark-explorer", "wave": 0, "prompt": "READ"}]
        )
        self.output.mkdir()
        (self.output / "stale-result.json").write_text("{}")
        with self.assertRaisesRegex(SystemExit, "new or empty"):
            self.run_fleet()

    def test_candidate_writer_must_be_terminal_wave(self) -> None:
        self.write_manifest(
            [
                {
                    "id": "write",
                    "role": "spark-worker",
                    "wave": 0,
                    "prompt": "WRITE",
                    "allowPaths": ["src"],
                },
                {"id": "verify", "role": "spark-verifier", "wave": 1, "prompt": "VERIFY"},
            ]
        )
        with self.assertRaisesRegex(SystemExit, "terminal fleet wave"):
            self.run_fleet("--allow-writes")


if __name__ == "__main__":
    unittest.main()
