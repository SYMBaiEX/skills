#!/usr/bin/env python3
"""Fail-closed, external cache for complete gate command truth."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
_HEX = set("0123456789abcdef")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_hash(value: object) -> str:
    return _sha(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    )


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError("not a usable Git repository: " + str(repo))
    return result.stdout


def _git_common_dir(repo: Path) -> Path:
    return Path(
        _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .decode()
        .strip()
    ).resolve()


def _digest_path(path: Path) -> str:
    try:
        info = path.lstat()
    except OSError:
        return "missing"
    if stat.S_ISLNK(info.st_mode):
        return "link:" + _sha(os.readlink(path).encode("utf-8", "surrogateescape"))
    if not stat.S_ISREG(info.st_mode):
        return "nonregular"
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _command_truth_files(repo: Path) -> list[tuple[str, str]]:
    names = (
        "AGENTS.md",
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "bun.lock",
        "bun.lockb",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "Makefile",
        "justfile",
    )
    found = [
        repo / name
        for name in names
        if (repo / name).exists() or (repo / name).is_symlink()
    ]
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        found.extend(
            path for path in workflows.rglob("*") if path.is_file() or path.is_symlink()
        )
    return sorted((str(path.relative_to(repo)), _digest_path(path)) for path in found)


def repository_fingerprint(repo: str | os.PathLike[str]) -> str:
    root = Path(repo).resolve()
    untracked = (
        _git(root, "ls-files", "--others", "--exclude-standard", "-z")
        .decode("utf-8", "surrogateescape")
        .split("\0")
    )
    head_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        check=False,
    )
    head = (
        head_result.stdout.decode().strip()
        if head_result.returncode == 0
        else "(unborn)"
    )
    if head == "(unborn)":
        diff = _git(root, "diff", "--cached", "--binary") + _git(
            root, "diff", "--binary"
        )
    else:
        diff = _git(root, "diff", "HEAD", "--binary")
    return _json_hash(
        {
            "git_common_dir": str(_git_common_dir(root)),
            "head": head,
            "diff": _sha(diff),
            "untracked": [
                (item, _digest_path(root / item))
                for item in sorted(item for item in untracked if item)
            ],
            "command_truth": _command_truth_files(root),
        }
    )


def _relative(root: Path, value: str | os.PathLike[str]) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return str(candidate.resolve().relative_to(root)) or "."
    except ValueError as exc:
        raise ValueError("path must be inside repo") from exc


def command_truth_key(
    argv: Sequence[str],
    cwd: str | os.PathLike[str],
    env: Mapping[str, str] | None = None,
    *,
    repo: str | os.PathLike[str] | None = None,
    allowed_env: Iterable[str] = (),
    scope_paths: Iterable[str | os.PathLike[str]] = (),
) -> str:
    if (
        isinstance(argv, (str, bytes))
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        raise ValueError(
            "argv must be a non-empty list of strings, never a shell command"
        )
    root = Path(repo if repo is not None else cwd).resolve()
    supplied = os.environ if env is None else env
    environment = {
        name: _sha(str(supplied[name]).encode())
        for name in sorted(set(allowed_env))
        if name in supplied
    }
    scopes = tuple(sorted({_relative(root, item) for item in scope_paths}))
    return _json_hash(
        {
            "schema_version": SCHEMA_VERSION,
            "argv": list(argv),
            "cwd": _relative(root, cwd),
            "scope_paths": scopes,
            "allowlisted_env": environment,
            "repository_fingerprint": repository_fingerprint(root),
        }
    )


def default_state_root() -> Path:
    return (
        Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        / "gpt-engineer"
        / "gate-cache"
    )


def _ensure_real_directory(path: Path) -> None:
    expanded = path.expanduser().absolute()
    current = Path(expanded.anchor)
    for part in expanded.parts[1:]:
        current /= part
        if current.is_symlink() and str(current) not in {"/var", "/tmp"}:
            raise ValueError("cache state path contains a symlink or non-directory")
    path = expanded.resolve()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("cache state path contains a symlink or non-directory")
        else:
            current.mkdir(mode=0o700)
    os.chmod(path, 0o700)


def _safe_child(directory: Path, name: str) -> Path:
    candidate = directory / name
    if candidate.parent != directory or "/" in name or "\\" in name:
        raise ValueError("unsafe cache filename")
    return candidate


def _is_hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def _valid_relative(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value
        and not Path(value).is_absolute()
        and ".." not in Path(value).parts
    )


def _valid_entry(value: Any, key: str, fingerprint: str, *, reusable: bool) -> bool:
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("key") != key
    ):
        return False
    command = value.get("command")
    if (
        not isinstance(command, dict)
        or command.get("repository_fingerprint") != fingerprint
    ):
        return False
    argv, scopes, environment = (
        command.get("argv"),
        command.get("scope_paths"),
        command.get("allowlisted_env"),
    )
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        return False
    if (
        not _valid_relative(command.get("cwd"))
        or not isinstance(scopes, list)
        or not all(_valid_relative(item) for item in scopes)
    ):
        return False
    if not isinstance(environment, dict) or not all(
        isinstance(name, str) and _is_hex(digest)
        for name, digest in environment.items()
    ):
        return False
    if not _utc(value.get("started_at")) or not _utc(value.get("ended_at")):
        return False
    started = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(value["ended_at"].replace("Z", "+00:00"))
    if ended < started:
        return False
    expected_key = _json_hash(
        {
            "schema_version": SCHEMA_VERSION,
            "argv": argv,
            "cwd": command["cwd"],
            "scope_paths": scopes,
            "allowlisted_env": environment,
            "repository_fingerprint": fingerprint,
        }
    )
    if expected_key != key:
        return False
    for stream in ("stdout", "stderr"):
        output = value.get(stream)
        if (
            not isinstance(output, dict)
            or not _is_hex(output.get("sha256"))
            or not isinstance(output.get("truncated"), bool)
        ):
            return False
    if reusable:
        return (
            value.get("exit_code") == 0
            and not isinstance(value.get("exit_code"), bool)
            and value.get("status") == "passed"
            and value.get("timed_out") is False
            and value.get("complete") is True
            and not value["stdout"]["truncated"]
            and not value["stderr"]["truncated"]
        )
    return (
        isinstance(value.get("exit_code"), int)
        and not isinstance(value.get("exit_code"), bool)
        and isinstance(value.get("status"), str)
        and isinstance(value.get("timed_out"), bool)
        and isinstance(value.get("complete"), bool)
    )


class GateCache:
    def __init__(
        self,
        repo: str | os.PathLike[str],
        state_root: str | os.PathLike[str] | None = None,
    ) -> None:
        self.repo = Path(repo).resolve()
        root = Path(state_root) if state_root is not None else default_state_root()
        prospective = root.expanduser().absolute().resolve(strict=False)
        if prospective == self.repo or self.repo in prospective.parents:
            raise ValueError("cache state root must be outside checkout")
        _ensure_real_directory(root)
        self.state_root = root.expanduser().resolve()
        self.directory = _safe_child(
            self.state_root, _sha(str(_git_common_dir(self.repo)).encode())
        )
        _ensure_real_directory(self.directory)
        self.lock_path = _safe_child(self.directory, ".lock")

    def _entry_path(self, key: str) -> Path:
        if not _is_hex(key):
            raise ValueError("invalid cache key")
        return _safe_child(self.directory, key + ".json")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _fingerprint(self) -> str:
        return repository_fingerprint(self.repo)

    def _fsync_directory(self) -> None:
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def put(self, key: str, entry: Mapping[str, Any]) -> dict[str, Any]:
        record = dict(entry)
        if not _valid_entry(record, key, self._fingerprint(), reusable=False):
            raise ValueError("malformed cache entry")
        target = self._entry_path(key)
        with self._locked():
            fd, temporary = tempfile.mkstemp(prefix=".tmp-", dir=self.directory)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "wb") as output:
                    output.write(
                        json.dumps(
                            record,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=True,
                        ).encode()
                    )
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, target)
                os.chmod(target, 0o600)
                self._fsync_directory()
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return record

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            target = self._entry_path(key)
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                return None
            with target.open("rb") as source:
                record = json.load(source)
            return (
                record
                if _valid_entry(record, key, self._fingerprint(), reusable=True)
                else None
            )
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def invalidate(self, key: str | None = None) -> int:
        targets = (
            [self._entry_path(key)] if key else sorted(self.directory.glob("*.json"))
        )
        with self._locked():
            count = 0
            for target in targets:
                try:
                    if not target.is_symlink():
                        target.unlink()
                        count += 1
                except FileNotFoundError:
                    pass
            self._fsync_directory()
            return count

    def prune(self, older_than: float) -> int:
        if older_than < 0:
            raise ValueError("older_than must be non-negative")
        now = datetime.now(timezone.utc)
        with self._locked():
            count = 0
            for target in sorted(self.directory.glob("*.json")):
                try:
                    if target.is_symlink():
                        target.unlink()
                        count += 1
                        continue
                    with target.open("rb") as source:
                        entry = json.load(source)
                    ended = datetime.fromisoformat(
                        entry.get("ended_at", "").replace("Z", "+00:00")
                    )
                    if (now - ended).total_seconds() > older_than:
                        target.unlink()
                        count += 1
                except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
                    try:
                        target.unlink()
                        count += 1
                    except FileNotFoundError:
                        pass
            self._fsync_directory()
            return count


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--state-root")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("fingerprint")
    put = sub.add_parser("put")
    put.add_argument("key")
    put.add_argument("--entry-json", required=True)
    get = sub.add_parser("get")
    get.add_argument("key")
    invalidate = sub.add_parser("invalidate")
    invalidate.add_argument("key", nargs="?")
    prune = sub.add_parser("prune")
    prune.add_argument("--older-than", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "fingerprint":
            result: Any = {"ok": True, "fingerprint": repository_fingerprint(args.repo)}
        else:
            cache = GateCache(args.repo, args.state_root)
            if args.action == "put":
                result = {
                    "ok": True,
                    "entry": cache.put(args.key, json.loads(args.entry_json)),
                }
            elif args.action == "get":
                result = {"ok": True, "entry": cache.get(args.key)}
            elif args.action == "invalidate":
                result = {"ok": True, "invalidated": cache.invalidate(args.key)}
            else:
                result = {"ok": True, "pruned": cache.prune(args.older_than)}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
