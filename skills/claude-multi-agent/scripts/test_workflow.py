#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
WORKFLOW = SKILL_ROOT / "assets" / "workflows" / "gpt-engineer-dynamic.js"


class ClaudeWorkflowTests(unittest.TestCase):
    def test_saved_workflow_has_deterministic_runtime_contract(self) -> None:
        source = WORKFLOW.read_text()
        self.assertTrue(source.startswith("export const meta = {"))
        self.assertIn('name: "gpt-engineer-dynamic"', source)
        self.assertIn('model: "opus"', source)
        self.assertIn('model: "sonnet"', source)
        self.assertIn("await parallel([", source)
        self.assertIn("phase(\"Build\")", source)
        self.assertIn("discoveries.length !== 3", source)
        self.assertIn("verification.length !== 3", source)
        self.assertIn('gaps: ["The required build writer did not return a valid result."]', source)
        self.assertIn("result.passed === true && (result.gaps?.length ?? 0) === 0", source)
        self.assertIn('["blocked", "failed"].includes(closure.status)', source)
        self.assertIn('closure.status !== "complete"', source)
        self.assertIn("const cycleNumber = cycle + 1", source)
        self.assertIn("cycles: cycle,", source)
        self.assertNotIn("cycles: cycle + 1", source)
        for forbidden in ("Date.now(", "Math.random(", "require(", "child_process", "node:fs"):
            self.assertNotIn(forbidden, source)
        settings = json.loads((SKILL_ROOT / "assets" / "settings.json").read_text())
        hooks = settings["hooks"]
        self.assertIn("SubagentStart", hooks)
        self.assertIn("SubagentStop", hooks)
        self.assertIn("TaskCompleted", hooks)
        workflow_groups = [group for group in hooks["PostToolUse"] if group.get("matcher") == "Workflow"]
        self.assertEqual(len(workflow_groups), 1)

    def test_bootstrap_is_idempotent_and_refuses_workflow_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            bootstrap = SCRIPT_DIR / "bootstrap.sh"
            first = subprocess.run([str(bootstrap), str(target)], check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run([str(bootstrap), str(target)], check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            installed = target / ".claude" / "workflows" / WORKFLOW.name
            self.assertEqual(installed.read_bytes(), WORKFLOW.read_bytes())
            installed.write_text("conflict\n")
            conflict = subprocess.run([str(bootstrap), str(target)], check=False, capture_output=True, text=True)
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("refusing to overwrite conflicting file", conflict.stderr)

    def test_global_bootstrap_installs_workflow_without_replacing_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            claude_home = Path(temporary) / "claude"
            claude_home.mkdir()
            settings = claude_home / "settings.json"
            settings.write_text('{"model":"custom"}\n')
            env = os.environ.copy()
            env["CLAUDE_CONFIG_DIR"] = str(claude_home)
            result = subprocess.run(
                [str(SCRIPT_DIR / "bootstrap.sh"), "--global"],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_text(), '{"model":"custom"}\n')
            self.assertEqual(
                (claude_home / "workflows" / WORKFLOW.name).read_bytes(),
                WORKFLOW.read_bytes(),
            )
            self.assertFalse((claude_home / "hooks").exists())

    def test_headless_wrapper_invokes_saved_command_and_unsets_global_model_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run([str(SCRIPT_DIR / "bootstrap.sh"), str(root)], check=True)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            record = root / "record.json"
            fake = fake_bin / "claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json
import os
import sys
if sys.argv[1:] == [\"--version\"]:
    print(\"2.1.211 (Claude Code)\")
    raise SystemExit(0)
with open(os.environ[\"FAKE_RECORD\"], \"w\") as handle:
    json.dump({\"args\": sys.argv[1:], \"subagentModel\": os.environ.get(\"CLAUDE_CODE_SUBAGENT_MODEL\")}, handle)
print(json.dumps({\"type\": \"result\", \"is_error\": False, \"structured_output\": {\"status\": \"complete\", \"complete\": True, \"cycles\": 1, \"gaps\": [], \"evidence\": [\"tests passed\"]}}))
"""
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "FAKE_RECORD": str(record),
                    "CLAUDE_CODE_SUBAGENT_MODEL": "fable",
                    "IN_PLACE": "1",
                    "STATE_DIR": str(root / "state"),
                }
            )
            result = subprocess.run(
                [str(SCRIPT_DIR / "run-workflow.sh"), "Audit every route"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            invocation = json.loads(record.read_text())
            self.assertEqual(invocation["subagentModel"], None)
            prompt = invocation["args"][invocation["args"].index("-p") + 1]
            self.assertTrue(prompt.startswith("/gpt-engineer-dynamic "))
            payload = json.loads(prompt.removeprefix("/gpt-engineer-dynamic "))
            self.assertEqual(payload["goal"], "Audit every route")
            self.assertEqual(payload["maxCycles"], 2)
            self.assertIn('"complete": true', result.stdout)

    def test_headless_wrapper_returns_nonzero_for_partial_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run([str(SCRIPT_DIR / "bootstrap.sh"), str(root)], check=True)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json
import sys
if sys.argv[1:] == ["--version"]:
    print("2.1.211 (Claude Code)")
    raise SystemExit(0)
print(json.dumps({"type":"result","is_error":False,"structured_output":{"status":"partial","complete":False,"cycles":2,"gaps":["tests fail"],"evidence":[]}}))
"""
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update({"PATH": f"{fake_bin}:{env['PATH']}", "IN_PLACE": "1"})
            result = subprocess.run(
                [str(SCRIPT_DIR / "run-workflow.sh"), "Audit every route"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("semantic completion barrier", result.stderr)

    def test_isolated_wrapper_returns_candidate_patch_for_main_agent_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "README.md").write_text("baseline\n")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "baseline",
                ],
                cwd=root,
                check=True,
            )
            claude_home = Path(temporary) / "claude"
            env = os.environ.copy()
            env["CLAUDE_CONFIG_DIR"] = str(claude_home)
            bootstrap = subprocess.run(
                [str(SCRIPT_DIR / "bootstrap.sh"), "--global"],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            fake_bin = Path(temporary) / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
if sys.argv[1:] == ["--version"]:
    print("2.1.211 (Claude Code)")
    raise SystemExit(0)
pathlib.Path("built.txt").write_text("candidate\\n")
hook_state = pathlib.Path(os.environ.get("CLAUDE_TEAM_STATE_DIR", ".claude-team"))
hook_state.mkdir(parents=True, exist_ok=True)
(hook_state / "workflow-events.jsonl").write_text("{}\\n")
if os.environ.get("FAKE_COMMIT") == "1":
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "-c", "user.name=Delegate", "-c", "user.email=delegate@example.com", "commit", "-qm", "delegate commit"], check=True)
print(json.dumps({"type":"result","is_error":False,"structured_output":{"status":"complete","complete":True,"cycles":1,"gaps":[],"evidence":["tests passed"]}}))
"""
            )
            fake.chmod(0o755)
            state = Path(temporary) / "state"
            env.update({"PATH": f"{fake_bin}:{env['PATH']}", "STATE_DIR": str(state)})
            result = subprocess.run(
                [str(SCRIPT_DIR / "run-workflow.sh"), "Build the feature", "candidate-test"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertFalse((root / "built.txt").exists())
            envelope = json.loads((state / "result-envelope.json").read_text())
            self.assertTrue(envelope["workflowComplete"])
            self.assertFalse(envelope["complete"])
            self.assertTrue(envelope["requiresMainAgentIntegration"])
            self.assertEqual(envelope["changedPaths"], ["built.txt"])
            self.assertIn("built.txt", (state / "candidate.patch").read_text())
            self.assertNotIn(".claude-team", (state / "candidate.patch").read_text())
            self.assertTrue((state / "workflow-events.jsonl").is_file())

            committed_state = Path(temporary) / "committed-state"
            env.update({"STATE_DIR": str(committed_state), "FAKE_COMMIT": "1"})
            committed = subprocess.run(
                [str(SCRIPT_DIR / "run-workflow.sh"), "Build the feature", "commit-test"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(committed.returncode, 2, committed.stderr)
            committed_envelope = json.loads(
                (committed_state / "result-envelope.json").read_text()
            )
            self.assertTrue(committed_envelope["candidateCommitViolation"])
            self.assertEqual(committed_envelope["status"], "failed")
            self.assertIn("built.txt", (committed_state / "candidate.patch").read_text())

    def test_headless_wrapper_refuses_unsupported_claude_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run([str(SCRIPT_DIR / "bootstrap.sh"), str(root)], check=True)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "claude"
            fake.write_text('#!/usr/bin/env bash\necho "2.1.153 (Claude Code)"\n')
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            env["IN_PLACE"] = "1"
            result = subprocess.run(
                [str(SCRIPT_DIR / "run-workflow.sh"), "Audit every route"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("2.1.154 or later is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
