#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "bootstrap.py"


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_project_installs_and_checks_both_providers(self) -> None:
        installed = self.run_script(str(self.root))
        self.assertEqual(installed.returncode, 0, installed.stderr)
        checked = self.run_script("--check", str(self.root))
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(len(list((self.root / ".codex" / "agents").glob("*.toml"))), 4)
        self.assertEqual(len(list((self.root / ".claude" / "agents").glob("*.md"))), 4)
        self.assertTrue((self.root / ".codex" / "hooks.json").exists())

    def test_global_install_uses_provider_homes_without_hooks(self) -> None:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(Path(self.temp.name) / "codex-home")
        env["CLAUDE_CONFIG_DIR"] = str(Path(self.temp.name) / "claude-home")
        installed = self.run_script("--global", env=env)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        checked = self.run_script("--check", "--global", env=env)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(len(list((Path(env["CODEX_HOME"]) / "agents").glob("*.toml"))), 4)
        self.assertEqual(len(list((Path(env["CLAUDE_CONFIG_DIR"]) / "agents").glob("*.md"))), 4)
        self.assertFalse((Path(env["CODEX_HOME"]) / "hooks.json").exists())

    def test_refuses_conflicting_agent_file(self) -> None:
        conflict = self.root / ".codex" / "agents" / "sol-engineer.toml"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("user-owned\n")
        result = self.run_script("--provider", "codex", str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to overwrite conflicting file", result.stderr)
        self.assertEqual(conflict.read_text(), "user-owned\n")

    def test_warns_when_claude_forces_one_subagent_model(self) -> None:
        env = os.environ.copy()
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = "opus"
        result = self.run_script("--provider", "claude", str(self.root), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("overrides every Claude agent profile", result.stderr)


if __name__ == "__main__":
    unittest.main()
