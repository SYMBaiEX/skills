#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import configure_luna_v2


def catalog(luna_version: str = "v1") -> dict[str, object]:
    return {
        "fetched_at": "2026-07-31T00:00:00Z",
        "etag": "test",
        "client_version": "0.144.6",
        "models": [
            {"slug": "gpt-5.6-sol", "multi_agent_version": "v2", "marker": "sol"},
            {"slug": "gpt-5.6-terra", "multi_agent_version": "v2", "marker": "terra"},
            {"slug": "gpt-5.6-luna", "multi_agent_version": luna_version, "marker": "luna"},
        ],
    }


class ConfigureLunaV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / ".codex"
        self.home.mkdir()
        (self.home / "models_cache.json").write_text(json.dumps(catalog()))
        (self.home / "config.toml").write_text(
            'model = "gpt-5.6-sol"\nsecret_setting = "preserve-me"\n\n[features]\nmulti_agent = true\n'
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_apply_changes_only_luna_route_and_preserves_config(self) -> None:
        self.assertEqual(configure_luna_v2.apply(self.home, True, validate_runtime=False), 0)
        target = self.home / configure_luna_v2.MANAGED_CATALOG
        patched = json.loads(target.read_text())
        expected = catalog()
        self.assertEqual(configure_luna_v2.model(patched, "gpt-5.6-luna")["multi_agent_version"], "v2")
        configure_luna_v2.model(patched, "gpt-5.6-luna")["multi_agent_version"] = "v1"
        for item in patched["models"]:
            item.pop("supports_reasoning_summaries")
        self.assertEqual(patched, expected)
        config = (self.home / "config.toml").read_text()
        self.assertIn('secret_setting = "preserve-me"', config)
        self.assertIn(f'model_catalog_json = "{target}"', config)
        self.assertIn("fast_mode = true", config)
        self.assertEqual(configure_luna_v2.check(self.home, True, validate_runtime=False), 0)

    def test_refresh_detects_stale_source(self) -> None:
        self.assertEqual(configure_luna_v2.apply(self.home, False, validate_runtime=False), 0)
        changed = catalog()
        changed["etag"] = "new"
        (self.home / "models_cache.json").write_text(json.dumps(changed))
        self.assertEqual(configure_luna_v2.check(self.home, False, validate_runtime=False), 1)
        self.assertEqual(configure_luna_v2.apply(self.home, False, validate_runtime=False), 0)
        self.assertEqual(configure_luna_v2.check(self.home, False, validate_runtime=False), 0)

    def test_disable_removes_only_managed_override(self) -> None:
        self.assertEqual(configure_luna_v2.apply(self.home, True, validate_runtime=False), 0)
        self.assertEqual(configure_luna_v2.disable(self.home), 0)
        config = (self.home / "config.toml").read_text()
        self.assertNotIn("model_catalog_json", config)
        self.assertIn('secret_setting = "preserve-me"', config)
        self.assertIn("fast_mode = true", config)
        self.assertFalse((self.home / configure_luna_v2.MANAGED_CATALOG).exists())

    def test_stock_v2_needs_no_shim(self) -> None:
        (self.home / "models_cache.json").write_text(json.dumps(catalog("v2")))
        self.assertEqual(configure_luna_v2.apply(self.home, True, validate_runtime=False), 0)
        self.assertFalse((self.home / configure_luna_v2.MANAGED_CATALOG).exists())

    def test_runtime_validation_fails_closed_when_codex_rejects_catalog(self) -> None:
        rejected = subprocess.CompletedProcess([], 1, stdout="", stderr="invalid catalog")
        with mock.patch("configure_luna_v2.resolve_codex", return_value="codex"):
            with mock.patch("configure_luna_v2.subprocess.run", return_value=rejected):
                with self.assertRaisesRegex(SystemExit, "Codex rejected.*invalid catalog"):
                    configure_luna_v2.validate_catalog_with_codex(catalog(), self.home)


if __name__ == "__main__":
    unittest.main()
