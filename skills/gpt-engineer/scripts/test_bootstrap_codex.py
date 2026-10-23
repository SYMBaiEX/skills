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
            ["python3", str(SCRIPT), "--with-hooks", *args, str(self.root)],
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
            [
                "gpt6-luna-explorer.toml",
                "gpt6-luna-verifier.toml",
                "gpt6-luna-worker.toml",
                "gpt61-sol-engineer.toml",
                "gpt61-sol-explorer.toml",
                "gpt61-sol-verifier.toml",
                "gpt61-sol-worker.toml",
            ],
        )

    def test_sol61_hooks_cover_every_registered_profile(self) -> None:
        import re
        import routes
        self.assertEqual(self.run_bootstrap().returncode, 0)
        hooks = json.loads((self.root / ".codex" / "hooks.json").read_text())
        matcher = hooks["hooks"]["SubagentStart"][0]["matcher"]
        script = self.root / ".codex" / "hooks" / "gpt_engineer_subagent_context.py"
        for role in routes.ROLES:
            name = role.replace("-", "_")
            self.assertIsNotNone(re.fullmatch(matcher, name))
            result = subprocess.run(["python3", str(script)],
                                    input=json.dumps({"hook_event_name": "SubagentStart", "agent_type": name}),
                                    capture_output=True, text=True, check=True)
            self.assertIn(name, json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])

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
