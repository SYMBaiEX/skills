#!/usr/bin/env python3
"""Safety and lifecycle coverage for the portable Codex runtime hooks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "bootstrap.py"
HOOK_ROOT = SCRIPT.parent.parent / "assets" / "codex" / "hooks"
CONTEXT_HOOK = HOOK_ROOT / "gpt_engineer_subagent_context.py"
GUARD_HOOK = HOOK_ROOT / "gpt_engineer_guard.py"


class RuntimeHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_bootstrap(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def install(self) -> None:
        result = self.run_bootstrap("--provider", "codex", "--with-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clean_install_records_receipt_and_repeat_is_idempotent(self) -> None:
        self.install()
        receipt = self.root / ".codex" / ".gpt-engineer-install.json"
        self.assertTrue(receipt.is_file())
        first = json.loads(receipt.read_text())
        hooks_path = self.root / ".codex" / "hooks.json"
        second = self.run_bootstrap("--provider", "codex", "--with-hooks")
        self.assertEqual(second.returncode, 0, second.stderr)
        diagnosed = self.run_bootstrap("--provider", "codex", "--diagnose", "--with-hooks")
        self.assertEqual(diagnosed.returncode, 0, diagnosed.stderr)
        self.assertEqual(first, json.loads(receipt.read_text()))
        hooks = json.loads(hooks_path.read_text())["hooks"]
        for groups in hooks.values():
            commands = [h["command"] for g in groups for h in g.get("hooks", [])]
            self.assertEqual(len(commands), len(set(commands)))

    def test_upgrade_replaces_file_matching_prior_receipt(self) -> None:
        self.install()
        path = self.root / ".codex" / "hooks" / CONTEXT_HOOK.name
        path.write_text("customized\n")
        blocked = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertEqual(path.read_text(), "customized\n")
        receipt = json.loads((self.root / ".codex" / ".gpt-engineer-install.json").read_text())
        baseline = subprocess.check_output(
            ["git", "show", f"HEAD:{CONTEXT_HOOK.relative_to(SCRIPT.parents[3])}"],
            cwd=SCRIPT.parents[3],
        )
        path.write_bytes(baseline)
        import hashlib

        receipt["files"][f"hooks/{CONTEXT_HOOK.name}"] = hashlib.sha256(baseline).hexdigest()
        (self.root / ".codex" / ".gpt-engineer-install.json").write_text(json.dumps(receipt))
        upgraded = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertEqual(path.read_bytes(), CONTEXT_HOOK.read_bytes())

    def test_known_baseline_hook_is_upgradeable_without_receipt(self) -> None:
        self.install()
        codex = self.root / ".codex"
        (codex / ".gpt-engineer-install.json").unlink()
        path = codex / "hooks" / GUARD_HOOK.name
        baseline = subprocess.check_output(
            ["git", "show", f"HEAD:{GUARD_HOOK.relative_to(SCRIPT.parents[3])}"],
            cwd=SCRIPT.parents[3],
        )
        path.write_bytes(baseline)
        result = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), GUARD_HOOK.read_bytes())

    def test_symlink_and_dangling_symlink_are_preserved(self) -> None:
        self.install()
        codex = self.root / ".codex"
        for name, target in (("gpt_engineer_guard.py", Path(self.temp.name) / "owner.py"),
                             ("gpt_engineer_subagent_context.py", Path(self.temp.name) / "missing.py")):
            path = codex / "hooks" / name
            path.unlink()
            path.symlink_to(target)
        result = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((codex / "hooks" / "gpt_engineer_guard.py").is_symlink())
        self.assertTrue((codex / "hooks" / "gpt_engineer_subagent_context.py").is_symlink())
        removed = self.run_bootstrap("--provider", "codex", "--uninstall")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertTrue((codex / "hooks" / "gpt_engineer_guard.py").is_symlink())

    def test_symlink_managed_parent_is_rejected_without_following(self) -> None:
        self.install()
        codex = self.root / ".codex"
        owner = Path(self.temp.name) / "owner-agents"
        owner.mkdir()
        (codex / "agents").rename(codex / "agents-original")
        (codex / "agents").symlink_to(owner, target_is_directory=True)
        result = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink path", result.stderr)
        self.assertTrue((codex / "agents").is_symlink())
        self.assertFalse((owner / "astra-engineer.toml").exists())

    def test_disable_removes_only_exact_managed_handlers(self) -> None:
        self.install()
        path = self.root / ".codex" / "hooks.json"
        config = json.loads(path.read_text())
        managed_handler = dict(config["hooks"]["SubagentStart"][0]["hooks"][0])
        managed_handler["statusMessage"] = "owner custom"
        config["hooks"]["SubagentStart"].append(
            {"matcher": "^custom$", "hooks": [{"type": "command", "command": "echo custom"}]}
        )
        config["hooks"]["SubagentStart"].append(
            {"matcher": "^owner$", "hooks": [managed_handler]}
        )
        path.write_text(json.dumps(config))
        result = self.run_bootstrap("--provider", "codex", "--disable")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = path.read_text()
        self.assertIn("gpt_engineer_subagent_context.py", text)
        self.assertIn("echo custom", text)
        self.assertIn("owner custom", text)
        self.assertNotIn('"statusMessage": "Loading GPT Engineer context"', text)

    def test_invalid_or_symlink_hook_config_is_preserved(self) -> None:
        self.install()
        path = self.root / ".codex" / "hooks.json"
        path.write_text("not-json\n")
        invalid = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(invalid.returncode, 0, invalid.stderr)
        self.assertEqual(path.read_text(), "not-json\n")
        diagnosed = self.run_bootstrap("--provider", "codex", "--diagnose", "--with-hooks")
        self.assertNotEqual(diagnosed.returncode, 0)
        self.assertEqual(path.read_text(), "not-json\n")
        target = Path(self.temp.name) / "owner-hooks.json"
        target.write_text(json.dumps({"hooks": {"SessionStart": []}}))
        path.unlink()
        path.symlink_to(target)
        linked = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(linked.returncode, 0, linked.stderr)
        self.assertTrue(path.is_symlink())
        self.assertEqual(os.readlink(path), str(target))

    def test_uninstall_removes_managed_files_and_keeps_custom_file(self) -> None:
        self.install()
        codex = self.root / ".codex"
        custom = codex / "agents" / "astra-engineer.toml"
        custom.write_text("name = 'owner-owned'\n")
        result = self.run_bootstrap("--provider", "codex", "--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(custom.read_text(), "name = 'owner-owned'\n")
        self.assertFalse((codex / "agents" / "astra-explorer.toml").exists())
        self.assertFalse((codex / ".gpt-engineer-install.json").exists())

    def test_uninstall_keeps_script_referenced_by_preserved_custom_handler(self) -> None:
        self.install()
        codex = self.root / ".codex"
        hooks_path = codex / "hooks.json"
        config = json.loads(hooks_path.read_text())
        config["hooks"]["PreToolUse"].append(
            {
                "matcher": "^owner$",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /owner/gpt_engineer_guard.py --extra",
                    }
                ],
            }
        )
        hooks_path.write_text(json.dumps(config))
        result = self.run_bootstrap("--provider", "codex", "--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((codex / "hooks" / "gpt_engineer_guard.py").exists())

    def test_hooks_are_opt_in_and_profiles_upgrade_does_not_reenable(self) -> None:
        result = self.run_bootstrap("--provider", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / ".codex" / "hooks.json"
        self.assertFalse(path.exists())
        self.install()
        self.assertEqual(self.run_bootstrap("--provider", "codex", "--disable").returncode, 0)
        before = path.read_bytes()
        self.assertEqual(self.run_bootstrap("--provider", "codex", "--upgrade").returncode, 0)
        self.assertEqual(path.read_bytes(), before)
        # Re-enabling is explicit; scripts remain managed for later uninstall.
        receipt = json.loads((path.parent / ".gpt-engineer-install.json").read_text())
        self.assertIn("hooks/gpt_engineer_guard.py", receipt["files"])
        self.assertEqual(receipt["hooks"], [])

    def test_uninstall_refuses_unknown_registration_state_before_deleting(self) -> None:
        self.install()
        codex = self.root / ".codex"
        for content in ("not-json", '{"hooks":{"PreToolUse":[{"hooks":[4]}]}}'):
            (codex / "hooks.json").write_text(content)
            result = self.run_bootstrap("--provider", "codex", "--uninstall")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((codex / "hooks" / GUARD_HOOK.name).exists())
            self.assertTrue((codex / "agents" / "astra-engineer.toml").exists())

    def test_current_and_historical_managed_registration_collapse(self) -> None:
        self.install()
        path = self.root / ".codex" / "hooks.json"
        config = json.loads(path.read_text())
        historical = json.loads(json.dumps(config["hooks"]["SubagentStart"][0]))
        historical["matcher"] = "^(sol_engineer|terra_explorer|terra_worker|luna_verifier)$"
        config["hooks"]["SubagentStart"].append(historical)
        path.write_text(json.dumps(config))
        result = self.run_bootstrap("--provider", "codex", "--upgrade", "--with-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(path.read_text())["hooks"]["SubagentStart"]), 1)

    def test_diagnose_missing_install_does_not_write_a_lock(self) -> None:
        result = self.run_bootstrap("--provider", "codex", "--diagnose")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "..codex.gpt-engineer.lock").exists())


class HookProcessTests(unittest.TestCase):
    @staticmethod
    def run_hook(path: Path, payload: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(path)], input=payload, capture_output=True, text=True, check=False
        )

    def test_context_hook_accepts_only_valid_allowlisted_event(self) -> None:
        accepted = self.run_hook(
            CONTEXT_HOOK,
            json.dumps({"hook_event_name": "SubagentStart", "agent_type": "astra_engineer", "model": "secret"}),
        )
        self.assertEqual(accepted.returncode, 0)
        self.assertLessEqual(len(accepted.stdout.encode()), 1200)
        self.assertNotIn("secret", accepted.stdout)
        for payload in ("not-json", "[]", json.dumps({"hook_event_name": "Other", "agent_type": "astra_engineer"}),
                        json.dumps({"hook_event_name": "SubagentStart", "agent_type": "arbitrary"})):
            result = self.run_hook(CONTEXT_HOOK, payload)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
        oversized = self.run_hook(
            CONTEXT_HOOK,
            json.dumps({"hook_event_name": "SubagentStart", "agent_type": "astra_engineer", "padding": "x" * 20_000}),
        )
        self.assertEqual(oversized.returncode, 0)
        self.assertEqual(oversized.stdout, "")

    def test_guard_malformed_input_is_fail_open_and_block_output_is_bounded(self) -> None:
        malformed = self.run_hook(GUARD_HOOK, "not-json")
        self.assertEqual(malformed.returncode, 0)
        self.assertEqual(malformed.stdout, "")
        denied = self.run_hook(GUARD_HOOK, json.dumps({"tool_input": {"command": "git reset --hard"}}))
        self.assertEqual(denied.returncode, 0)
        self.assertLessEqual(len(denied.stdout.encode()), 1200)
        self.assertIn('"permissionDecision": "deny"', denied.stdout)

    def test_cold_context_hook_latency_is_bounded(self) -> None:
        payload = json.dumps({"hook_event_name": "SubagentStart", "agent_type": "luna_worker"})
        elapsed = []
        for _ in range(10):
            started = time.perf_counter()
            result = self.run_hook(CONTEXT_HOOK, payload)
            elapsed.append(time.perf_counter() - started)
            self.assertEqual(result.returncode, 0)
            self.assertLessEqual(len(result.stdout.encode()), 1200)
        # Smoke ceiling only; record distributions outside CI, not a speed claim.
        self.assertLess(max(elapsed), 5)


if __name__ == "__main__":
    unittest.main()
