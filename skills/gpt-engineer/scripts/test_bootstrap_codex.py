#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "bootstrap_codex.py"


class BootstrapCodexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_bootstrap(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args, str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_installs_and_verifies_profiles_and_hooks(self) -> None:
        installed = self.run_bootstrap()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        checked = self.run_bootstrap("--check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        agents = sorted(path.name for path in (self.root / ".codex" / "agents").glob("*.toml"))
        self.assertEqual(
            agents,
            ["luna-verifier.toml", "sol-engineer.toml", "terra-explorer.toml", "terra-worker.toml"],
        )

    def test_merges_existing_hooks_without_losing_them(self) -> None:
        hooks_path = self.root / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        hooks_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "startup",
                                "hooks": [{"type": "command", "command": "echo existing"}],
                            }
                        ]
                    }
                }
            )
        )
        installed = self.run_bootstrap()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        hooks = json.loads(hooks_path.read_text())["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("SubagentStart", hooks)
        self.assertIn("PreToolUse", hooks)

    def test_guard_blocks_destructive_git_and_allows_read_only_git(self) -> None:
        self.assertEqual(self.run_bootstrap().returncode, 0)
        guard = self.root / ".codex" / "hooks" / "gpt_engineer_guard.py"

        blocked = subprocess.run(
            ["python3", str(guard)],
            input=json.dumps({"tool_input": {"command": "git reset --hard HEAD"}}),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(blocked.returncode, 0)
        self.assertEqual(
            json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

        allowed = subprocess.run(
            ["python3", str(guard)],
            input=json.dumps({"tool_input": {"command": "git status --short"}}),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(allowed.returncode, 0)
        self.assertEqual(allowed.stdout, "")


if __name__ == "__main__":
    unittest.main()
