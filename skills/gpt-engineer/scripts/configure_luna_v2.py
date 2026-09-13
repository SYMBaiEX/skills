#!/usr/bin/env python3
"""Recovery-only removal of the old managed Luna catalog override. Never create a catalog."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

MANAGED_CATALOG = "model-catalogs/gpt-engineer-luna-v2.json"


def configuration(path):
    if path.is_symlink():
        raise ValueError("Refusing symlink configuration")
    if not path.exists():
        return "", {}
    if tomllib is None:
        raise ValueError("Python 3.11+ or tomli is required")
    text = path.read_text()
    return text, tomllib.loads(text)


def recover(home, disable=False):
    home = Path(home).expanduser()
    if home.is_symlink():
        raise ValueError("Refusing symlink Codex home")
    home = home.resolve()
    config = home / "config.toml"
    text, data = configuration(config)
    override = data.get("model_catalog_json")
    managed = str(home / MANAGED_CATALOG)
    if override is None:
        return {"status": "stock", "changed": False}
    if override != managed:
        return {"status": "custom-preserved", "changed": False}
    if not disable:
        return {"status": "legacy-override-active", "changed": False,
                "next": "Review and use --disable to return to the stock catalog"}
    lock = home / ".gpt-engineer-luna-recovery.lock"
    with os.fdopen(os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), "r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        text, data = configuration(config)
        if data.get("model_catalog_json") != managed:
            raise ValueError("Configuration changed; recheck before recovery")
        # Edit only a single line. Full TOML equality proves no unrelated value changed,
        # including multiline strings or tables containing key-looking text.
        lines = text.splitlines(keepends=True)
        candidates = [i for i, line in enumerate(lines) if re.match(r"^\s*model_catalog_json\s*=", line)]
        expected = dict(data)
        expected.pop("model_catalog_json")
        safe = []
        for i in candidates:
            candidate = "".join(lines[:i] + lines[i + 1:])
            try:
                if tomllib.loads(candidate) == expected:
                    safe.append(candidate)
            except ValueError:
                pass
        if len(safe) != 1:
            raise ValueError("Cannot safely remove the managed setting; manual review required")
        backup = home / ("config.toml.gpt-engineer-recovery." + str(time.time_ns()) + ".bak")
        with os.fdopen(os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        fd, temporary = tempfile.mkstemp(prefix=".gpt-engineer-recovery-", dir=home)
        try:
            with os.fdopen(fd, "w") as out:
                out.write(safe[0])
                out.flush()
                os.fsync(out.fileno())
            os.chmod(temporary, config.stat().st_mode & 0o777)
            if config.is_symlink() or config.read_text() != text:
                raise ValueError("Configuration changed during recovery")
            os.replace(temporary, config)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    # A historical catalog may have been customized; removing its setting is enough.
    return {"status": "disabled", "changed": True, "catalogFile": "retained",
            "next": "Restart Codex; inspect the retained catalog separately if removal is wanted"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--disable", action="store_true")
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    args = parser.parse_args(argv)
    try:
        result = recover(args.codex_home, args.disable)
        print(json.dumps(result))
        return 1 if result["status"] == "legacy-override-active" else 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
