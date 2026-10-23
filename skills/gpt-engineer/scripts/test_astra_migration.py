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

    def test_astra_parent_uses_only_explicit_sol_or_luna_children(self):
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL)["status"], "passed")
        legacy = ["terra_worker=gpt-5.6-terra:medium"]
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, legacy)["status"], "failed")
        astra_child = ["gpt61_sol_worker=gpt-6-astra:medium"]
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, astra_child)["status"], "failed")
        current = ["gpt6_luna_worker=gpt-6-luna:high"]
        self.assertEqual(audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL, current)["status"], "passed")
        self.assertEqual(audit_routing.audit(self.root, self.home, "gpt-5.6-sol", suite="sol61")["status"], "passed")

    def test_registry_and_assets_agree(self):
        for name, route in routes.ROLES.items():
            profile = audit_routing.read_profile(self.home / "agents" / route["profile"])
            self.assertEqual(profile["name"], name.replace("-", "_"))
            self.assertEqual(profile["model"], route["model"])
            self.assertEqual(profile["model_reasoning_effort"], route["effort"])
            with (self.home / "agents" / route["profile"]).open("rb") as stream:
                self.assertNotIn("sandbox_mode", audit_routing.tomllib.load(stream))
        self.assertFalse(routes.ROLES["gpt61-sol-verifier"]["write_capable"])
        self.assertNotIn("astra-verifier", routes.ROLES)

    def test_original_luna_profiles_upgrade_without_receipt_and_preserve_customizations(self):
        for role in ("explorer", "worker", "verifier"):
            name = f"gpt6-luna-{role}.toml"
            source = bootstrap.ASSET_ROOT / "codex" / "agents" / name
            sandbox = "workspace-write" if role == "worker" else "read-only"
            original = source.read_text().replace('developer_instructions =', f'sandbox_mode = "{sandbox}"\ndeveloper_instructions =').encode()
            path = self.home / "agents" / name
            path.write_bytes(original)
            (self.home / bootstrap.RECEIPT_NAME).unlink(missing_ok=True)
            with self.assertRaises(SystemExit):
                bootstrap.install_codex(self.home, False, False, False)
            bootstrap.install_codex(self.home, False, False, True)
            self.assertEqual(path.read_bytes(), source.read_bytes())
            custom = original + b"# customized\n"
            path.write_bytes(custom)
            (self.home / bootstrap.RECEIPT_NAME).unlink(missing_ok=True)
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                bootstrap.install_codex(self.home, False, False, True)
            self.assertIn("Preserving customized", stderr.getvalue())
            self.assertEqual(path.read_bytes(), custom)
            path.write_bytes(source.read_bytes())
        for role in ("gpt6-luna-explorer", "gpt6-luna-verifier"):
            self.assertIn("Do not edit", run_codex_agent.role_instructions(role))

    def test_verifier_artifact_authority_is_explicit_and_scoped(self):
        instructions = run_codex_agent.role_instructions("gpt61-sol-verifier")
        self.assertIn("Do not edit source", instructions)
        self.assertIn("or spawn children", instructions)
        read_command = run_codex_agent.build_command("codex", "gpt61-sol-verifier", self.root, self.root / "final.txt", False)
        write_command = run_codex_agent.build_command("codex", "gpt61-sol-verifier", self.root, self.root / "final.txt", True)
        self.assertEqual(read_command[read_command.index("--sandbox") + 1], "read-only")
        self.assertEqual(write_command[write_command.index("--sandbox") + 1], "read-only")

    def test_retired_sol_profiles_require_safe_upgrade_and_keep_customizations(self):
        for role in ("engineer", "explorer", "worker", "verifier"):
            name = f"gpt6-sol-{role}.toml"
            current = (bootstrap.ASSET_ROOT / "codex" / "agents" / f"gpt61-sol-{role}.toml").read_text()
            sandbox = "read-only" if role in ("explorer", "verifier") else "workspace-write"
            original = current.replace("gpt61_sol", "gpt6_sol").replace("gpt-6.1-sol", "gpt-6-sol")
            original = original.replace('developer_instructions =', f'sandbox_mode = "{sandbox}"\ndeveloper_instructions =').encode()
            path = self.home / "agents" / name
            path.write_bytes(original)
            with self.assertRaises(SystemExit):
                bootstrap.install_codex(self.home, False, False, False)
            bootstrap.install_codex(self.home, False, False, True)
            self.assertFalse(path.exists())
            self.assertTrue(list((self.home / "retired-agent-backups").glob(name + ".*")))
            path.write_bytes(original + b"# customized\n")
            bootstrap.install_codex(self.home, False, False, True)
            self.assertTrue(path.exists())
            result = audit_routing.audit(self.root, self.home, routes.SOL61_MODEL)
            self.assertTrue(any("retired GPT Engineer child route" in message for message in result["violations"]))
            path.unlink()

    def test_retired_profile_fails_even_when_unused_and_selected(self):
        path = self.home / "agents" / "custom-sol.toml"
        path.write_text('name = "sol_engineer"\nmodel = "gpt-5.6-sol"\nmodel_reasoning_effort = "high"\n')
        result = audit_routing.audit(self.root, self.home, routes.ASTRA_MODEL)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("retired GPT Engineer child route" in item for item in result["violations"]))
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
        self.assertEqual(hook.read_text(), "# previously installed hook\n")
        self.assertEqual(unrelated.read_text(), "# user hook\n")
        with self.assertRaisesRegex(SystemExit, "differs"):
            bootstrap.install_codex(destination, True, True, True)

    def test_retirement_backup_and_modified_preservation(self):
        path = self.home / "agents" / "sol-engineer.toml"
        content = b"known retired profile\n"
        digest = hashlib.sha256(content).hexdigest()
        path.write_bytes(content)
        with (
            mock.patch.dict(bootstrap.RETIRED, {path.name: "test retirement"}, clear=True),
            mock.patch.dict(
                bootstrap.KNOWN_BUNDLED_HASHES,
                {"agents/" + path.name: {digest}},
            ),
        ):
            with self.assertRaises(SystemExit):
                bootstrap.retire_profiles(self.home, True, True)
            bootstrap.retire_profiles(self.home, False, True)
            self.assertFalse(path.exists())
            self.assertEqual((self.home / "retired-agent-backups" / (path.name + "." + digest)).read_bytes(), content)
            bootstrap.retire_profiles(self.home, False, True)
            path.write_text("customized")
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                bootstrap.retire_profiles(self.home, False, True)
            self.assertIn("Preserving customized", stderr.getvalue())
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
        self.assertEqual(installed[0]["matcher"], "^sol_engineer$")
        self.assertEqual(installed[1], custom)
        self.assertIn("gpt61_sol_engineer", installed[2]["matcher"])
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

    def test_versioned_dispatch_policies_preserve_old_sol_history(self):
        cutoff = routes.MIGRATION.timestamp()
        for role in ("engineer", "explorer", "worker", "verifier"):
            old_role = f"gpt6-sol-{role}"
            self.assertEqual(routes.historical_policy(old_role, cutoff, "gpt6"), ("gpt-6-sol", None))
            self.assertIn("retired", routes.historical_policy(old_role, cutoff, "gpt61")[1])
            self.assertNotIn(old_role, routes.ROLES)
        for policy in ("gpt6", "gpt61"):
            self.assertEqual(routes.historical_policy("gpt6_luna_worker", cutoff, policy), ("gpt-6-luna", None))
            self.assertIn("retired", routes.historical_policy("astra_worker", cutoff, policy)[1])
        self.assertEqual(routes.historical_policy("gpt61_sol_worker", cutoff, "gpt61"), ("gpt-6.1-sol", None))
        self.assertIn("historical gpt6", routes.historical_policy("gpt61_sol_worker", cutoff, "gpt6")[1])

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
        self.assertEqual(len(groups[0]["hooks"]), 2)
        self.assertIn({"type": "command", "command": "echo custom"}, groups[0]["hooks"])
        self.assertIn("gpt61_sol_engineer", groups[1]["matcher"])
        bootstrap.merge_codex_hooks(destination, True)

    def test_astra_parent_requires_explicit_mixed_model_policy(self):
        with mock.patch("sys.stdin", io.StringIO("Read only")), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit):
                run_codex_agent.main(["--role", "gpt6-luna-explorer", "--parent-model", "gpt-6-astra", "--compatibility-reason", "headless-isolation-required", "--cwd", str(self.root), "--output-dir", str(self.root / "result"), "--dry-run"])
        # No subprocess/model execution is needed to prove the routing boundary.
        self.assertIn("explicit mixed-model policy", err.getvalue())
        self.assertNotIn("gpt6-luna-explorer", routes.suite_routes("sol61"))


if __name__ == "__main__":
    unittest.main()
