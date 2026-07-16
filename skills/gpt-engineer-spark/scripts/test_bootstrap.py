#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_project_install_and_check(self) -> None:
        self.assertEqual(bootstrap.main([str(self.root)]), 0)
        installed = sorted(path.name for path in (self.root / ".codex" / "agents").glob("spark-*.toml"))
        self.assertEqual(installed, ["spark-explorer.toml", "spark-verifier.toml", "spark-worker.toml"])
        self.assertEqual(bootstrap.main(["--check", str(self.root)]), 0)

    def test_global_install_uses_codex_home(self) -> None:
        codex_home = Path(self.temp.name) / "codex-home"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}, clear=False):
            self.assertEqual(bootstrap.main(["--global"]), 0)
            self.assertEqual(bootstrap.main(["--check", "--global"]), 0)
        self.assertTrue((codex_home / "agents" / "spark-worker.toml").exists())

    def test_conflicting_profile_is_refused(self) -> None:
        target = self.root / ".codex" / "agents" / "spark-explorer.toml"
        target.parent.mkdir(parents=True)
        target.write_text("conflict\n")
        with self.assertRaisesRegex(SystemExit, "Refusing to overwrite conflicting file"):
            bootstrap.main([str(self.root)])

    def test_every_profile_pins_exact_spark_model(self) -> None:
        profiles = sorted(bootstrap.AGENT_ASSETS.glob("*.toml"))
        self.assertEqual(len(profiles), 3)
        for profile in profiles:
            self.assertIn('model = "gpt-5.3-codex-spark"', profile.read_text())


if __name__ == "__main__":
    unittest.main()
