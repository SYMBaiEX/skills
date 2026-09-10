import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import audit_routing
import bootstrap
import routes
import run_codex_agent


class AstraMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        bootstrap.install_codex(self.home, False, False, False)

    def test_default_astra_and_explicit_economy(self):
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL)["status"], "passed")
        declaration = ["terra_worker=gpt-5.6-terra:medium"]
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, declaration)["status"], "failed")
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, declaration, suite="economy")["status"], "passed")
        self.assertEqual(audit_routing.audit(self.root, self.home, "gpt-5.6-sol", suite="economy")["status"], "failed")

    def test_registry_and_assets_agree(self):
        for name, route in routes.ROLES.items():
            profile = audit_routing.read_profile(self.home / "agents" / route["profile"])
            self.assertEqual(profile["name"], name.replace("-", "_"))
            self.assertEqual(profile["model"], route["model"])
            self.assertEqual(profile["model_reasoning_effort"], route["effort"])
        self.assertTrue(routes.ROLES["astra-verifier"]["write_capable"])
        self.assertNotIn("sol-engineer", routes.ROLES)

    def test_verifier_artifact_authority_is_explicit_and_scoped(self):
        instructions = run_codex_agent.role_instructions("astra-verifier")
        self.assertIn("Never edit product source", instructions)
        self.assertIn("Test-generated artifacts, caches, and build outputs", instructions)
        self.assertIn("only within assigned paths", instructions)
        self.assertIn("including prior authorization", instructions)
        read_command = run_codex_agent.build_command("codex", "astra-verifier", self.root, self.root / "final.txt", False)
        write_command = run_codex_agent.build_command("codex", "astra-verifier", self.root, self.root / "final.txt", True)
        self.assertEqual(read_command[read_command.index("--sandbox") + 1], "read-only")
        self.assertEqual(write_command[write_command.index("--sandbox") + 1], "workspace-write")

    def test_unused_retired_profile_warns_but_selected_role_fails(self):
        path = self.home / "agents" / "custom-sol.toml"
        path.write_text('name = "sol_engineer"\nmodel = "gpt-5.6-sol"\nmodel_reasoning_effort = "high"\n')
        result = audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(any("retired Sol" in item for item in result["warnings"]))
        selected = audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, ["sol_engineer=gpt-5.6-sol:high"])
        self.assertEqual(selected["status"], "failed")
        self.assertEqual(path.read_text(), 'name = "sol_engineer"\nmodel = "gpt-5.6-sol"\nmodel_reasoning_effort = "high"\n')

    def test_project_hook_scripts_require_and_honor_explicit_upgrade(self):
        destination = self.root / "project-codex"
        bootstrap.install_codex(destination, False, True, False)
        hook = destination / "hooks" / "gpt_engineer_guard.py"
        hook.write_text("# previously installed hook\n")
        with self.assertRaisesRegex(SystemExit, "differs"):
            bootstrap.install_codex(destination, True, True, True)
        with self.assertRaisesRegex(SystemExit, "Refusing to overwrite"):
            bootstrap.install_codex(destination, False, True, False)
        self.assertEqual(hook.read_text(), "# previously installed hook\n")
        unrelated = destination / "hooks" / "custom.py"
        unrelated.write_text("# user hook\n")
        bootstrap.install_codex(destination, False, True, True)
        self.assertEqual(hook.read_bytes(), (bootstrap.ASSET_ROOT / "codex" / "hooks" / hook.name).read_bytes())
        self.assertEqual(unrelated.read_text(), "# user hook\n")
        bootstrap.install_codex(destination, True, True, True)

    def test_retirement_backup_and_modified_preservation(self):
        path = self.home / "agents" / "sol-engineer.toml"
        content = b"known retired profile\n"
        digest = hashlib.sha256(content).hexdigest()
        path.write_bytes(content)
        with mock.patch.dict(bootstrap.RETIRED, {path.name: digest}, clear=True):
            with self.assertRaises(SystemExit):
                bootstrap.retire_profiles(self.home, True, True)
            bootstrap.retire_profiles(self.home, False, True)
            self.assertFalse(path.exists())
            self.assertEqual((self.home / "retired-agent-backups" / (path.name + "." + digest)).read_bytes(), content)
            bootstrap.retire_profiles(self.home, False, True)
            path.write_text("customized")
            with self.assertRaisesRegex(SystemExit, "modified"):
                bootstrap.retire_profiles(self.home, False, True)
            self.assertEqual(path.read_text(), "customized")

    def test_existing_matcher_migrates_and_unrelated_hooks_survive(self):
        supplied = json.loads((bootstrap.ASSET_ROOT / "codex" / "hooks.json").read_text())
        supplied["hooks"]["SubagentStart"][0]["matcher"] = "^sol_engineer$"
        custom = {"matcher": "custom", "hooks": [{"type": "command", "command": "echo custom"}]}
        supplied["hooks"]["SubagentStart"].append(custom)
        destination = self.root / "hooks.json"
        destination.write_text(json.dumps(supplied))
        before = destination.read_bytes()
        with self.assertRaises(SystemExit):
            bootstrap.merge_codex_hooks(destination, True)
        self.assertEqual(destination.read_bytes(), before)
        bootstrap.merge_codex_hooks(destination, False)
        installed = json.loads(destination.read_text())["hooks"]["SubagentStart"]
        self.assertIn("astra_engineer", installed[0]["matcher"])
        self.assertEqual(installed[1], custom)
        bootstrap.merge_codex_hooks(destination, True)

    def test_temporal_exact_model_policies(self):
        cutoff = routes.MIGRATION.timestamp()
        self.assertEqual(routes.historical_policy("sol_engineer", cutoff - 1), ("gpt-5.6-sol", None))
        self.assertIn("retired", routes.historical_policy("sol_engineer", cutoff)[1])
        self.assertEqual(routes.historical_policy("terra_worker", cutoff), ("gpt-5.6-terra", None))
        self.assertEqual(routes.historical_policy("astra_worker", cutoff), ("gpt-6-astra", None))
        old = routes.LEGACY_RETIREMENT.timestamp()
        self.assertIsNone(routes.historical_policy("gpt-engineer-worker", old - 1)[1])
        self.assertIn("retired", routes.historical_policy("gpt-engineer-worker", old)[1])

    def test_mixed_hook_group_keeps_unrelated_matcher(self):
        supplied = json.loads((bootstrap.ASSET_ROOT / "codex" / "hooks.json").read_text())
        group = supplied["hooks"]["SubagentStart"][0]
        group["matcher"] = "^sol_engineer$"
        group["hooks"].append({"type": "command", "command": "echo custom"})
        destination = self.root / "mixed.json"
        destination.write_text(json.dumps(supplied))
        bootstrap.merge_codex_hooks(destination, False)
        groups = json.loads(destination.read_text())["hooks"]["SubagentStart"]
        self.assertEqual(groups[0]["matcher"], "^sol_engineer$")
        self.assertEqual(groups[0]["hooks"], [{"type": "command", "command": "echo custom"}])
        self.assertIn("astra_engineer", groups[1]["matcher"])
        bootstrap.merge_codex_hooks(destination, True)

    def test_default_runner_refuses_economy_before_launch(self):
        with mock.patch("sys.stdin", io.StringIO("Read only")), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit):
                run_codex_agent.main(["--role", "terra-explorer", "--compatibility-reason", "headless-isolation-required", "--cwd", str(self.root), "--output-dir", str(self.root / "result"), "--dry-run"])
        # No subprocess/model execution is needed to prove suite membership.
        self.assertIn("requires explicit --suite economy", err.getvalue())
        self.assertNotIn("terra-explorer", routes.suite_routes())


if __name__ == "__main__":
    unittest.main()
