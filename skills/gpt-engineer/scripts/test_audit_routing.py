#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from unittest import mock
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

    def fake_codex(self, name: str, version: str, features_ok: bool = True) -> Path:
        executable = Path(self.temp.name) / name
        feature_body = (
            'print("multi_agent stable true")\nprint("fast_mode stable true")'
            if features_ok
            else 'print("invalid config", file=sys.stderr)\nraise SystemExit(1)'
        )
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            f"VERSION = {version!r}\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print(VERSION)\n"
            "elif sys.argv[1:] == ['features', 'list']:\n"
            + "\n".join(f"    {line}" for line in feature_body.splitlines())
            + "\nelse:\n    raise SystemExit(2)\n"
        )
        executable.chmod(0o755)
        return executable

    def test_valid_profiles_and_parent_pass(self) -> None:
        result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["violations"], [])

    def test_single_quoted_commented_shadow_cannot_bypass_audit(self) -> None:
        shadow = self.root / ".codex" / "agents" / "shadow.toml"
        shadow.write_text("name = 'astra_worker' # valid TOML\nmodel = 'gpt-5.4' # wrong route\nmodel_reasoning_effort = 'medium'\n")
        result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(str(shadow) in item and "expected gpt-6-astra" in item for item in result["violations"]))

    def test_multiline_toml_string_and_nested_fields(self) -> None:
        path = self.root / ".codex" / "agents" / "multiline.toml"
        path.write_text('name = """astra_worker"""\nmodel = """gpt-6-astra"""\nmodel_reasoning_effort = "medium" # comment\n[metadata]\nname = "astra_worker"\nmodel = "gpt-5.4"\n')
        self.assertEqual(audit_routing.read_profile(path)["model"], "gpt-6-astra")
        self.assertEqual(audit_routing.audit(self.root, self.home, "gpt-6-astra")["status"], "passed")
        path.write_text('[metadata]\nname = "astra_worker"\nmodel = "gpt-5.4"\n')
        self.assertEqual(audit_routing.read_profile(path), {})
        (self.home / "agents" / "astra-worker.toml").unlink()
        result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
        self.assertIn("missing installed custom agent profile: astra_worker", result["violations"])

    def test_malformed_and_duplicate_keys_fail_with_source(self) -> None:
        path = self.root / ".codex" / "agents" / "malformed.toml"
        for content in ('name = "astra_worker\n', 'name = "astra_worker"\nname = "other"\n'):
            with self.subTest(content=content):
                path.write_text(content)
                result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
                self.assertEqual(result["status"], "failed")
                self.assertTrue(any(str(path) in item and "Cannot parse" in item for item in result["violations"]))

    def test_routing_fields_require_top_level_strings(self) -> None:
        path = self.root / ".codex" / "agents" / "typed.toml"
        for field in ("name", "model", "model_reasoning_effort", "service_tier"):
            with self.subTest(field=field):
                path.write_text(f'{field} = ["invalid"]\n')
                result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
                self.assertEqual(result["status"], "failed")
                self.assertTrue(any(str(path) in item and f"{field} must be a string" in item for item in result["violations"]))

    def test_missing_supported_parser_fails_closed(self) -> None:
        with mock.patch.object(audit_routing, "tomllib", None):
            result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("Python 3.11+" in item and "tomli" in item for item in result["violations"]))

    def test_project_shadow_with_old_model_fails(self) -> None:
        shadow = self.root / ".codex" / "agents" / "shadow.toml"
        shadow.write_text(
            'name = "astra_explorer"\n'
            'description = "bad shadow"\n'
            'model = "gpt-5.4"\n'
            'model_reasoning_effort = "high"\n'
            'developer_instructions = "read"\n'
        )
        result = audit_routing.audit(self.root, self.home, "gpt-6-astra")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("expected gpt-6-astra/medium" in item for item in result["violations"])
        )

    def test_old_parent_model_fails(self) -> None:
        result = audit_routing.audit(self.root, self.home, "gpt-5.4")
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "parent model is outside pinned-suite routing: gpt-5.4",
            result["violations"],
        )

    def test_missing_profile_fails(self) -> None:
        (self.home / "agents" / "astra-worker.toml").unlink()
        result = audit_routing.audit(self.root, self.home, None)
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "missing installed custom agent profile: astra_worker",
            result["violations"],
        )

    def test_matching_observed_route_passes(self) -> None:
        result = audit_routing.audit(
            self.root,
            self.home,
            "gpt-6-astra",
            ["astra_explorer=gpt-6-astra:medium"],
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["observedRoutes"][0]["valid"])

    def test_generic_or_old_observed_route_fails(self) -> None:
        result = audit_routing.audit(
            self.root,
            self.home,
            "gpt-6-astra",
            [
                "security-auditor=gpt-5.4:high",
                "astra_worker=gpt-5.4:high",
            ],
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("unsupported agent type" in item for item in result["violations"])
        )
        self.assertTrue(
            any("expected gpt-6-astra" in item for item in result["violations"])
        )

    def test_malformed_observed_route_fails(self) -> None:
        result = audit_routing.audit(
            self.root, self.home, "gpt-6-astra", ["astra_explorer"]
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("invalid observed route" in item for item in result["violations"]))

    def test_runtime_selects_newest_valid_codex_and_reports_path_skew(self) -> None:
        old = self.fake_codex("old-codex", "codex-cli 0.144.6", features_ok=False)
        new = self.fake_codex("new-codex", "codex-cli 0.151.0")
        result = audit_routing.audit_runtime(
            self.home,
            candidates=[("path", str(old)), ("chatgpt-app", str(new))],
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["selected"]["path"], str(new.resolve()))
        self.assertTrue(any("PATH Codex" in item for item in result["warnings"]))
        self.assertTrue(any("rejects the active config" in item for item in result["warnings"]))

    def test_runtime_rejects_stale_managed_catalog(self) -> None:
        current = self.fake_codex("current-codex", "codex-cli 0.151.0")
        source = {
            "client_version": "0.151.0",
            "models": [
                {"slug": "gpt-6-astra", "multi_agent_version": "v2"},
                {"slug": "gpt-5.6-terra", "multi_agent_version": "v2"},
                {"slug": "gpt-5.6-luna", "multi_agent_version": "v1"},
            ],
        }
        target = json.loads(json.dumps(source))
        target["client_version"] = "0.146.0"
        target["models"][2]["multi_agent_version"] = "v2"
        managed = self.home / audit_routing.MANAGED_CATALOG
        managed.parent.mkdir(parents=True)
        (self.home / "models_cache.json").write_text(json.dumps(source))
        managed.write_text(json.dumps(target))
        (self.home / "config.toml").write_text(
            f'model_catalog_json = "{managed}"\n'
        )
        result = audit_routing.audit_runtime(
            self.home,
            candidates=[("path", str(current))],
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["catalog"]["status"], "stale")
        self.assertTrue(any("stale" in item for item in result["violations"]))


if __name__ == "__main__":
    unittest.main()
