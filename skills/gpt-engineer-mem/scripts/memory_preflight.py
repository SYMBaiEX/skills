#!/usr/bin/env python3
"""Read-only Claude Mem availability and health diagnostic."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_URL = "http://127.0.0.1:37777"


def get_json(base_url: str, path: str, timeout: float) -> tuple[Any | None, str | None]:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}{path}", timeout=timeout) as response:
            return json.load(response), None
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def table_count(connection: sqlite3.Connection, name: str) -> int | None:
    if not table_exists(connection, name):
        return None
    return int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])


def database_report(path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "wal_bytes": None,
        "counts": {},
        "outbox_operations": [],
        "outbox_operation_field": None,
        "snapshot_mode": "immutable-main-database",
        "snapshot_note": "counts exclude rows present only in the WAL",
    }
    wal = Path(f"{path}-wal")
    if wal.is_file():
        report["wal_bytes"] = wal.stat().st_size
    if not path.is_file():
        return report

    try:
        # mode=ro can still create a -shm sidecar for WAL databases. immutable=1 avoids filesystem
        # mutation; counts are therefore a conservative snapshot of the main database file.
        with sqlite3.connect(
            f"file:{path}?mode=ro&immutable=1", uri=True, timeout=1.0
        ) as connection:
            for table in (
                "observations",
                "sessions",
                "summaries",
                "sync_outbox",
                "sync_content_outbox",
                "sync_dead_letter",
            ):
                count = table_count(connection, table)
                if count is not None:
                    report["counts"][table] = count
            if table_exists(connection, "sync_outbox"):
                columns = {
                    row[1] for row in connection.execute('PRAGMA table_info("sync_outbox")')
                }
                operation = next(
                    (column for column in ("operation", "operation_type", "op", "type") if column in columns),
                    None,
                )
                if operation:
                    report["outbox_operation_field"] = operation
                    rows = connection.execute(
                        f'SELECT "{operation}", COUNT(*) FROM "sync_outbox" '
                        f'GROUP BY "{operation}" ORDER BY COUNT(*) DESC LIMIT 10'
                    ).fetchall()
                    report["outbox_operations"] = [
                        {"operation": str(row[0]), "count": int(row[1])} for row in rows
                    ]
    except sqlite3.Error as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    return report


def discover_plugins(codex_home: Path) -> list[dict[str, str]]:
    root = codex_home / "plugins" / "cache" / "claude-mem-local" / "claude-mem"
    plugins: list[dict[str, str]] = []
    if not root.is_dir():
        return plugins
    for manifest in sorted(root.glob("*/.codex-plugin/plugin.json")):
        try:
            data = json.loads(manifest.read_text())
        except (OSError, ValueError):
            data = {}
        plugins.append(
            {
                "version": str(data.get("version") or manifest.parents[1].name),
                "path": str(manifest.parents[1]),
            }
        )
    return plugins


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def codex_registration(codex_home: Path) -> dict[str, Any]:
    config = codex_home / "config.toml"
    entries: list[dict[str, Any]] = []
    try:
        text = config.read_text()
    except OSError:
        text = ""
    section = re.compile(
        r'^\[plugins\."(?P<name>claude-mem@[^"\n]+)"\]\s*\n'
        r'(?P<body>.*?)(?=^\[|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    for match in section.finditer(text):
        enabled_match = re.search(
            r"^enabled\s*=\s*(true|false)\s*$", match.group("body"), re.MULTILINE
        )
        entries.append(
            {
                "name": match.group("name"),
                "enabled": enabled_match is not None and enabled_match.group(1) == "true",
            }
        )
    return {
        "config": str(config),
        "configured": any(entry["enabled"] for entry in entries),
        "plugins": entries,
    }


def claude_registration(claude_config_dir: Path) -> dict[str, Any]:
    settings_path = claude_config_dir / "settings.json"
    installed_path = claude_config_dir / "plugins" / "installed_plugins.json"
    settings = read_json_object(settings_path)
    installed = read_json_object(installed_path)
    enabled_plugins = settings.get("enabledPlugins")
    installed_plugins = installed.get("plugins")
    enabled_plugins = enabled_plugins if isinstance(enabled_plugins, dict) else {}
    installed_plugins = installed_plugins if isinstance(installed_plugins, dict) else {}
    names = sorted(
        name
        for name in set(enabled_plugins) | set(installed_plugins)
        if name.startswith("claude-mem@")
    )
    entries: list[dict[str, Any]] = []
    install_roots: list[str] = []
    for name in names:
        installs = installed_plugins.get(name)
        installs = installs if isinstance(installs, list) else []
        roots = sorted(
            {
                str(item.get("installPath"))
                for item in installs
                if isinstance(item, dict) and item.get("installPath")
            }
        )
        install_roots.extend(roots)
        entries.append(
            {
                "name": name,
                "enabled": enabled_plugins.get(name) is True,
                "installed": bool(roots),
            }
        )
    return {
        "config": str(settings_path),
        "configured": any(entry["enabled"] and entry["installed"] for entry in entries),
        "plugins": entries,
        "install_roots": sorted(set(install_roots)),
    }


def mcp_registration_report(
    plugins: list[dict[str, str]],
    health: Any,
    worker_mcp: Any,
    codex: dict[str, Any],
    claude: dict[str, Any],
) -> dict[str, Any]:
    roots = {Path(plugin["path"]) for plugin in plugins}
    if isinstance(health, dict) and health.get("workerPath"):
        roots.add(Path(str(health["workerPath"])).parent.parent)
    roots.update(Path(path) for path in claude.get("install_roots", []))

    manifests: list[dict[str, str]] = []
    for root in sorted(roots):
        for layout, candidate in (
            ("root", root / ".mcp.json"),
            ("nested-plugin", root / "plugin" / ".mcp.json"),
        ):
            if candidate.is_file():
                manifests.append({"path": str(candidate), "layout": layout})

    worker_toggle = worker_mcp.get("enabled") if isinstance(worker_mcp, dict) else None
    clients_configured = bool(codex.get("configured") or claude.get("configured"))
    if manifests and clients_configured:
        effective = "registered"
    elif manifests:
        effective = "manifest-only"
    else:
        effective = "absent"
    root_manifest = any(item["layout"] == "root" for item in manifests)
    nested_manifest = any(item["layout"] == "nested-plugin" for item in manifests)
    layout_false_negative = worker_toggle is False and root_manifest and not nested_manifest
    notes: list[str] = []
    if layout_false_negative:
        notes.append(
            "worker HTTP status checks nested plugin/.mcp.json, but this package uses root .mcp.json"
        )
    return {
        "effective": effective,
        "manifests": manifests,
        "clients": {"codex": codex, "claude": claude},
        "worker_toggle_enabled": worker_toggle,
        "worker_status_layout_false_negative": layout_false_negative,
        "notes": notes,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    codex_home = Path(args.codex_home).expanduser()
    claude_config_dir = Path(
        getattr(args, "claude_config_dir", os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    ).expanduser()
    data_dir = Path(args.data_dir).expanduser()
    health, health_error = get_json(args.url, "/api/health", args.timeout)
    readiness, readiness_error = get_json(args.url, "/api/readiness", args.timeout)
    processing, processing_error = get_json(args.url, "/api/processing-status", args.timeout)
    dependency, dependency_error = get_json(
        args.url, "/api/settings/dependency-health", args.timeout
    )
    mcp, mcp_error = get_json(args.url, "/api/mcp/status", args.timeout)

    plugins = discover_plugins(codex_home)
    registration = mcp_registration_report(
        plugins,
        health,
        mcp,
        codex_registration(codex_home),
        claude_registration(claude_config_dir),
    )
    report: dict[str, Any] = {
        "read_only": True,
        "plugins": plugins,
        "mcp_registration": registration,
        "worker": {
            "url": args.url,
            "health": health,
            "readiness": readiness,
            "processing": processing,
            "dependency_health": dependency,
            "mcp": mcp,
            "errors": {
                key: value
                for key, value in {
                    "health": health_error,
                    "readiness": readiness_error,
                    "processing": processing_error,
                    "dependency_health": dependency_error,
                    "mcp": mcp_error,
                }.items()
                if value
            },
        },
        "database": database_report(data_dir / "claude-mem.db"),
        "warnings": [],
    }

    warnings: list[str] = report["warnings"]
    if health is None:
        warnings.append("worker health is unavailable; use the base engineering workflow")
    if isinstance(health, dict) and report["plugins"]:
        worker_path = str(health.get("workerPath") or "")
        if worker_path and not any(
            worker_path.startswith(plugin["path"] + os.sep) for plugin in report["plugins"]
        ):
            warnings.append("active worker path does not match a discovered Codex plugin cache")
    queue_depth = processing.get("queueDepth") if isinstance(processing, dict) else None
    if isinstance(queue_depth, int) and queue_depth > 0:
        warnings.append(f"worker queue depth is {queue_depth}; memory may be incomplete")
    if registration["effective"] == "absent":
        warnings.append("no Claude Mem MCP manifest was discovered")
    elif registration["effective"] == "manifest-only":
        warnings.append("MCP manifest exists, but no enabled Codex or Claude registration was found")
    counts = report["database"]["counts"]
    outbox = counts.get("sync_outbox", 0)
    if isinstance(outbox, int) and outbox > 1000:
        warnings.append(f"sync_outbox has {outbox} rows; investigate separately before cleanup")
    if report["database"]["bytes"] and report["database"]["bytes"] > 1_000_000_000:
        warnings.append("Claude Mem database exceeds 1 GB; investigate growth separately")
    if not report["plugins"]:
        warnings.append("no Claude Mem Codex plugin cache was discovered")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--url", default=os.environ.get("CLAUDE_MEM_URL", DEFAULT_URL))
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    parser.add_argument(
        "--claude-config-dir",
        default=os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"),
    )
    parser.add_argument("--data-dir", default=os.environ.get("CLAUDE_MEM_DATA_DIR", "~/.claude-mem"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        worker = "available" if report["worker"]["health"] is not None else "unavailable"
        print(f"Claude Mem worker: {worker}")
        print(f"Plugin installs: {len(report['plugins'])}")
        print(f"Database: {report['database']['path']}")
        for warning in report["warnings"]:
            print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
