#!/usr/bin/env python3
"""Contract tests for the read-only Claude Mem preflight."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("memory_preflight.py")
SPEC = importlib.util.spec_from_file_location("memory_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        payloads = {
            "/api/health": {"version": "13.15.0", "initialized": True},
            "/api/readiness": {"status": "ready"},
            "/api/processing-status": {"queueDepth": 0},
            "/api/settings/dependency-health": {"status": "ok"},
            "/api/mcp/status": {"enabled": False},
        }
        if self.path not in payloads:
            self.send_error(404)
            return
        body = json.dumps(payloads[self.path]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextlib.contextmanager
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


class PreflightTests(unittest.TestCase):
    def test_reads_health_and_database_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp, server() as url:
            root = Path(temp)
            plugin = root / "codex/plugins/cache/claude-mem-local/claude-mem/13.15.0/.codex-plugin"
            plugin.mkdir(parents=True)
            (plugin / "plugin.json").write_text('{"version":"13.15.0"}')
            (plugin.parent / ".mcp.json").write_text('{"mcpServers":{}}')
            (root / "codex/config.toml").write_text(
                '[plugins."claude-mem@thedotmack"]\n'
                'enabled = false\n\n'
                '[plugins."claude-mem@claude-mem-local"]\n'
                'enabled = true\n'
            )
            claude = root / "claude"
            (claude / "plugins").mkdir(parents=True)
            (claude / "settings.json").write_text(
                '{"enabledPlugins":{"claude-mem@thedotmack":true}}'
            )
            (claude / "plugins/installed_plugins.json").write_text(
                json.dumps(
                    {
                        "plugins": {
                            "claude-mem@thedotmack": [
                                {"installPath": str(plugin.parent)}
                            ]
                        }
                    }
                )
            )
            data = root / "data"
            data.mkdir()
            database = data / "claude-mem.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE observations (id INTEGER)")
                connection.execute("CREATE TABLE sync_outbox (operation TEXT)")
                connection.executemany(
                    "INSERT INTO sync_outbox VALUES (?)", [("upsert",), ("upsert",), ("delete",)]
                )
            before_bytes = database.read_bytes()
            before_files = sorted(path.name for path in data.iterdir())
            args = argparse.Namespace(
                url=url,
                timeout=1.0,
                codex_home=str(root / "codex"),
                claude_config_dir=str(claude),
                data_dir=str(data),
            )
            report = PREFLIGHT.build_report(args)
            self.assertTrue(report["read_only"])
            self.assertEqual(report["worker"]["processing"]["queueDepth"], 0)
            self.assertEqual(report["database"]["counts"]["sync_outbox"], 3)
            self.assertEqual(report["plugins"][0]["version"], "13.15.0")
            self.assertEqual(report["mcp_registration"]["effective"], "registered")
            self.assertTrue(
                report["mcp_registration"]["worker_status_layout_false_negative"]
            )
            self.assertFalse(any("retrieval tools" in item for item in report["warnings"]))
            self.assertEqual(report["database"]["snapshot_mode"], "immutable-main-database")
            self.assertEqual(database.read_bytes(), before_bytes)
            self.assertEqual(sorted(path.name for path in data.iterdir()), before_files)

    def test_unavailable_worker_is_a_warning_not_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(
                url="http://127.0.0.1:1",
                timeout=0.05,
                codex_home=str(Path(temp) / "codex"),
                claude_config_dir=str(Path(temp) / "claude"),
                data_dir=str(Path(temp) / "data"),
            )
            report = PREFLIGHT.build_report(args)
            self.assertIsNone(report["worker"]["health"])
            self.assertTrue(any("base engineering workflow" in item for item in report["warnings"]))

    def test_wal_snapshot_does_not_create_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            database = data / "claude-mem.db"
            writer = sqlite3.connect(database)
            try:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("PRAGMA wal_autocheckpoint=0")
                writer.execute("CREATE TABLE observations (id INTEGER)")
                writer.execute("INSERT INTO observations VALUES (1)")
                writer.commit()
                shm = Path(f"{database}-shm")
                if shm.exists():
                    shm.unlink()
                before_files = sorted(path.name for path in data.iterdir())
                report = PREFLIGHT.database_report(database)
                self.assertEqual(sorted(path.name for path in data.iterdir()), before_files)
                self.assertGreater(report["wal_bytes"], 0)
                self.assertIn("exclude rows", report["snapshot_note"])
            finally:
                writer.close()


if __name__ == "__main__":
    unittest.main()
