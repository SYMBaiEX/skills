#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import audit_routing


ASSETS = Path(__file__).resolve().parent.parent / "assets" / "codex" / "agents"


class AuditRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.home = Path(self.temp.name) / "codex-home"
        (self.root / ".codex" / "agents").mkdir(parents=True)
        (self.home / "agents").mkdir(parents=True)
        for source in ASSETS.glob("*.toml"):
            shutil.copy2(source, self.home / "agents" / source.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_profiles_and_parent_pass(self) -> None:
        result = audit_routing.audit(self.root, self.home, "gpt-5.6-sol")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["violations"], [])

    def test_project_shadow_with_old_model_fails(self) -> None:
        shadow = self.root / ".codex" / "agents" / "shadow.toml"
        shadow.write_text(
            'name = "terra_explorer"\n'
            'description = "bad shadow"\n'
            'model = "gpt-5.4"\n'
            'model_reasoning_effort = "high"\n'
            'developer_instructions = "read"\n'
        )
        result = audit_routing.audit(self.root, self.home, "gpt-5.6-sol")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("expected gpt-5.6-terra/medium" in item for item in result["violations"])
        )

    def test_old_parent_model_fails(self) -> None:
        result = audit_routing.audit(self.root, self.home, "gpt-5.4")
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "parent model is outside latest-only routing: gpt-5.4",
            result["violations"],
        )

    def test_missing_profile_fails(self) -> None:
        (self.home / "agents" / "luna-worker.toml").unlink()
        result = audit_routing.audit(self.root, self.home, None)
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "missing installed custom agent profile: luna_worker",
            result["violations"],
        )


if __name__ == "__main__":
    unittest.main()
