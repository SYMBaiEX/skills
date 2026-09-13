import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import configure_luna_v2 as recovery


class CatalogRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.config = self.home / "config.toml"

    def test_stock_is_readonly(self):
        self.config.write_text('model = "gpt-5.6-luna"\n')
        before = self.config.read_bytes()
        self.assertEqual(recovery.recover(self.home)["status"], "stock")
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(len(list(self.home.iterdir())), 1)

    def test_disable_preserves_all_other_values_and_catalog(self):
        target = self.home / recovery.MANAGED_CATALOG
        target.parent.mkdir()
        target.write_text('{"custom":true}')
        self.config.write_text('model_catalog_json = ' + json.dumps(str(target)) + '\nmodel = "gpt-5.6-sol"\n[features]\nfast_mode = true\n')
        self.assertEqual(recovery.recover(self.home)["status"], "legacy-override-active")
        self.assertEqual(recovery.recover(self.home, True)["status"], "disabled")
        self.assertEqual(recovery.configuration(self.config)[1], {"model": "gpt-5.6-sol", "features": {"fast_mode": True}})
        self.assertTrue(target.is_file())
        backup = next(self.home.glob("*.bak"))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(recovery.recover(self.home, True)["status"], "stock")

    def test_custom_override_preserved(self):
        self.config.write_text('model_catalog_json = "/custom/catalog.json"\n')
        before = self.config.read_bytes()
        self.assertEqual(recovery.recover(self.home, True)["status"], "custom-preserved")
        self.assertEqual(self.config.read_bytes(), before)

    def test_symlink_and_duplicate_fail_closed(self):
        self.config.symlink_to(self.home / "missing")
        with self.assertRaises(ValueError):
            recovery.recover(self.home, True)
        self.config.unlink()
        self.config.write_text('model_catalog_json="a"\nmodel_catalog_json="b"\n')
        with self.assertRaises(ValueError):
            recovery.recover(self.home, True)

    def test_apply_removed(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            recovery.main(["--apply", "--codex-home", str(self.home)])


if __name__ == "__main__":
    unittest.main()
