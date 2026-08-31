#!/usr/bin/env python3
"""Private, append-only orchestration journals for GPT Engineer runs.

This deliberately records bounded engineering state, never model prompts or replies.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "gpt-engineer-run-journal/v1"
EVENT_TYPES = frozenset(
    {
        "run.started",
        "stage.planned",
        "dispatch.accepted",
        "handoff.received",
        "finding.updated",
        "requirement.updated",
        "barrier.started",
        "barrier.completed",
        "verification.completed",
        "command.completed",
        "run.interrupted",
        "run.closed",
        "journal.recovered",
    }
)
STAGE_STATUSES = frozenset(
    {"pending", "ready", "running", "completed", "failed", "blocked", "interrupted"}
)
REQUIREMENT_STATUSES = frozenset(
    {"pending", "passed", "failed", "skipped", "not_run", "not_applicable", "blocked"}
)
FINDING_STATUSES = frozenset(
    {
        "pending",
        "implemented",
        "already_satisfied",
        "invalid",
        "duplicate",
        "deferred",
        "blocked",
    }
)
GATE_STATUSES = REQUIREMENT_STATUSES
SECRET = re.compile(
    r"(?i)(?:(?:api[_-]?key|token|password|secret|authorization|access[_-]?token)\s*(?:=|:|\s)\s*[^\s,;]+|([?&](?:token|api_key|access_token|key)=[^&#\s]+)|\bsk-[A-Za-z0-9_-]{16,}|https?://[^\s/@]+:[^\s/@]+@[^\s]+|[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{10,})"
)
MAX_EVENT_BYTES, MAX_TEXT = 32768, 2048


class JournalError(ValueError):
    pass


def utcnow() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def valid_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return SECRET.sub("[REDACTED]", value)[:MAX_TEXT]
    if isinstance(value, list):
        return [redact(x) for x in value[:100]]
    if isinstance(value, dict):
        return {
            str(k)[:100]: (
                "[REDACTED]"
                if re.search(
                    r"(?i)(?:api[_-]?key|token|password|secret|authorization)$", str(k)
                )
                else redact(v)
            )
            for k, v in list(value.items())[:100]
        }
    return value


def _chmod(path: Path, mode: int) -> None:
    os.chmod(path, mode)
    if (path.stat().st_mode & 0o777) != mode:
        raise JournalError(f"unsafe permissions: {path}")


def _safe_dir(path: Path) -> Path:
    """Create a private directory, refusing symlinks at every newly-owned level."""
    # macOS exposes /var and /tmp as system symlinks.  Canonicalise those
    # inherited ancestors before checking the journal-controlled path.
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise JournalError(f"unsafe journal path: {expanded}")
    current = Path(expanded.anchor)
    for part in expanded.parts[1:]:
        current /= part
        if current.is_symlink() and str(current) not in {"/var", "/tmp"}:
            raise JournalError(f"unsafe journal path: {current}")
    path = expanded.resolve()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise JournalError(f"unsafe journal path: {current}")
        else:
            current.mkdir(mode=0o700)
            _chmod(current, 0o700)
    _chmod(path, 0o700)
    return path


def repo_identity(repo: Path) -> dict[str, str]:
    repo = repo.resolve()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise JournalError("repository is not a usable git worktree")
        return result.stdout.strip()

    top = Path(git("rev-parse", "--show-toplevel")).resolve()

    def path_hash(value: str) -> str:
        return hashlib.sha256(str(Path(value).resolve()).encode()).hexdigest()

    common = git("rev-parse", "--git-common-dir")
    common_path = (
        (top / common).resolve()
        if not Path(common).is_absolute()
        else Path(common).resolve()
    )
    worktree = git("rev-parse", "--git-dir")
    worktree_path = (
        (top / worktree).resolve()
        if not Path(worktree).is_absolute()
        else Path(worktree).resolve()
    )
    head_result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=top,
        capture_output=True,
        text=True,
        check=False,
    )
    head = head_result.stdout.strip() if head_result.returncode == 0 else "(unborn)"
    if head == "(unborn)":
        dirty = bytearray(
            subprocess.run(
                ["git", "diff", "--cached", "--binary"],
                cwd=top,
                capture_output=True,
                check=True,
            ).stdout
        )
        dirty.extend(
            subprocess.run(
                ["git", "diff", "--binary"], cwd=top, capture_output=True, check=True
            ).stdout
        )
    else:
        dirty = bytearray(
            subprocess.run(
                ["git", "diff", "HEAD", "--binary"],
                cwd=top,
                capture_output=True,
                check=True,
            ).stdout
        )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=top,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    for raw in sorted(path for path in untracked if path):
        relative = raw.decode("utf-8", "surrogateescape")
        target = top / relative
        dirty.extend(raw + b"\0")
        if target.is_symlink():
            dirty.extend(os.readlink(target).encode("utf-8", "surrogateescape"))
        elif target.is_file():
            dirty.extend(hashlib.sha256(target.read_bytes()).digest())
        else:
            dirty.extend(b"directory")
    return {
        "rootHash": path_hash(str(top)),
        "commonGitHash": path_hash(str(common_path)),
        "worktreeHash": path_hash(str(worktree_path)),
        "head": head,
        "branch": git("branch", "--show-current"),
        "dirtyDigest": hashlib.sha256(dirty).hexdigest(),
    }


def repo_key(repo: Path) -> str:
    identity = repo_identity(repo)
    return identity["rootHash"][:24]


def default_root(repo: Path, state_home: str | None = None) -> Path:
    base = Path(
        state_home or os.environ.get("XDG_STATE_HOME", "~/.local/state")
    ).expanduser()
    return base / "gpt-engineer" / "repositories" / repo_key(repo) / "runs"


def init_repo_backend(repo: Path) -> Path:
    """The sole opt-in mutator for a repo-local backend."""
    repo = repo.resolve()
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    config, ignore = root / ".engineer", root / ".engineer" / ".gitignore"
    if config.is_symlink() or (ignore.exists() and ignore.is_symlink()):
        raise JournalError("repo backend symlink rejected")
    tracked = subprocess.run(
        ["git", "ls-files", "--", ".engineer/runs"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked.stdout.strip():
        raise JournalError("repo runtime path is tracked")
    expected_config = canonical({"backend": "repo-local/v1", "schema": SCHEMA}) + "\n"
    expected_ignore = "runs/\n!config.json\n!.gitignore\n"
    _safe_dir(config)
    for path, expected in (
        (config / "config.json", expected_config),
        (ignore, expected_ignore),
    ):
        if path.exists() and path.read_text(encoding="utf-8") != expected:
            raise JournalError("repo backend sentinel mismatch")
        if not path.exists():
            path.write_text(expected, encoding="utf-8")
        _chmod(path, 0o600)
    return config / "runs"


class Journal:
    def __init__(
        self,
        repo: str | Path,
        state_root: str | Path | None = None,
        *,
        repo_local: bool = False,
        state_home: str | Path | None = None,
    ):
        if state_root is not None and state_home is not None:
            raise JournalError("choose state_root or state_home")
        self.repo = Path(repo)
        self.identity = repo_identity(self.repo)
        repo_root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        if state_root is not None:
            root = Path(state_root)
        elif repo_local:
            root = repo_root / ".engineer" / "runs"
        else:
            base = Path(
                state_home or os.environ.get("XDG_STATE_HOME", "~/.local/state")
            ).expanduser()
            root = (
                base
                / "gpt-engineer"
                / "repositories"
                / self.identity["rootHash"][:24]
                / "runs"
            )
        prospective = root.expanduser().absolute().resolve(strict=False)
        if not repo_local and (
            prospective == repo_root or repo_root in prospective.parents
        ):
            raise JournalError("private journal state must be outside checkout")
        if repo_local:
            config, ignore = (
                repo_root / ".engineer" / "config.json",
                repo_root / ".engineer" / ".gitignore",
            )
            expected_config = (
                canonical({"backend": "repo-local/v1", "schema": SCHEMA}) + "\n"
            )
            expected_ignore = "runs/\n!config.json\n!.gitignore\n"
            if (
                any(p.is_symlink() for p in (config.parent, config, ignore))
                or not config.is_file()
                or not ignore.is_file()
                or config.read_text() != expected_config
                or ignore.read_text() != expected_ignore
            ):
                raise JournalError("repo-local journal requires safe init --repo")
            if subprocess.run(
                ["git", "ls-files", "--", ".engineer/runs"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip():
                raise JournalError("repo runtime path is tracked")
        self.runs_root = _safe_dir(root)

    def _run(self, run_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
            raise JournalError("invalid run id")
        target = self.runs_root / run_id
        if target.is_symlink():
            raise JournalError("run path symlink rejected")
        return target

    @contextmanager
    def _locked(self, run: Path) -> Iterator[None]:
        lock = run / ".lock"
        if lock.is_symlink():
            raise JournalError("lock symlink rejected")
        fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        _chmod(lock, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def start(
        self, run_id: str | None = None, *, data: dict[str, Any] | None = None
    ) -> str:
        run_id = run_id or uuid.uuid4().hex
        run = self._run(run_id)
        if run.exists():
            raise JournalError("run already exists")
        run.mkdir(mode=0o700)
        _chmod(run, 0o700)
        manifest = {
            "schema": SCHEMA,
            "runId": run_id,
            "repository": self.identity,
            "createdAtUtc": utcnow(),
        }
        self._atomic(run / "manifest.json", manifest)
        self.append(run_id, "run.started", data=data or {})
        return run_id

    def _atomic(self, target: Path, value: Any) -> None:
        if target.is_symlink():
            raise JournalError("derived file symlink rejected")
        fd, name = tempfile.mkstemp(prefix=".tmp-", dir=target.parent)
        os.fchmod(fd, 0o600)
        try:
            os.write(fd, (canonical(value) + "\n").encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(name, target)
            dfd = os.open(target.parent, os.O_RDONLY)
            os.fsync(dfd)
            os.close(dfd)
            _chmod(target, 0o600)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _manifest(self, run: Path) -> dict[str, Any]:
        path = run / "manifest.json"
        if path.is_symlink() or not path.is_file():
            raise JournalError("missing or unsafe run manifest")
        try:
            manifest = json.loads(path.read_bytes())
        except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
            raise JournalError("malformed run manifest") from exc
        repository = manifest.get("repository") if isinstance(manifest, dict) else None
        required = {
            "rootHash",
            "commonGitHash",
            "worktreeHash",
            "head",
            "branch",
            "dirtyDigest",
        }
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema") != SCHEMA
            or manifest.get("runId") != run.name
            or not valid_utc(manifest.get("createdAtUtc"))
            or not isinstance(repository, dict)
            or not required.issubset(repository)
            or not all(isinstance(repository[key], str) for key in required)
        ):
            raise JournalError("invalid run manifest")
        return manifest

    def _validate_stored_event(
        self, event: Any, run: Path, sequence: int
    ) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise JournalError("journal event must be an object")
        if event.get("schema") != SCHEMA or event.get("runId") != run.name:
            raise JournalError("journal event identity mismatch")
        if event.get("sequence") != sequence:
            raise JournalError("journal sequence mismatch")
        if (
            not isinstance(event.get("eventId"), str)
            or not event["eventId"]
            or len(event["eventId"]) > 160
        ):
            raise JournalError("invalid journal event id")
        if not valid_utc(event.get("occurredAtUtc")):
            raise JournalError("invalid journal timestamp")
        if event.get("redaction") != {"policy": "bounded-v1"}:
            raise JournalError("invalid journal redaction marker")
        stage_id, attempt = event.get("stageId"), event.get("attempt")
        if stage_id is not None and (not isinstance(stage_id, str) or not stage_id):
            raise JournalError("invalid journal stage id")
        if attempt is not None and (
            not isinstance(attempt, int) or isinstance(attempt, bool) or attempt <= 0
        ):
            raise JournalError("invalid journal attempt")
        event_type, data = event.get("type"), event.get("data")
        self._validate(event_type, data)
        if stage_id is not None and data.get("stageId") not in (None, stage_id):
            raise JournalError("journal stage identity mismatch")
        return event

    def _events(self, run: Path, *, recover: bool = False) -> list[dict[str, Any]]:
        self._manifest(run)
        path = run / "journal.jsonl"
        if not path.exists():
            return []
        if path.is_symlink() or not path.is_file():
            raise JournalError("unsafe journal file")
        raw = path.read_bytes()
        lines = raw.splitlines(keepends=True)
        result = []
        for i, line in enumerate(lines):
            terminated = line.endswith(b"\n")
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                if recover and i == len(lines) - 1 and not terminated:
                    backup = run / (
                        "journal.jsonl.partial-" + utcnow().replace(":", "")
                    )
                    bfd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    try:
                        os.write(bfd, line)
                        os.fsync(bfd)
                    finally:
                        os.close(bfd)
                    _chmod(backup, 0o600)
                    jfd = os.open(path, os.O_WRONLY)
                    os.ftruncate(jfd, len(b"".join(lines[:-1])))
                    os.fsync(jfd)
                    os.close(jfd)
                    _chmod(path, 0o600)
                    dfd = os.open(run, os.O_RDONLY)
                    os.fsync(dfd)
                    os.close(dfd)
                    self._append_locked(
                        run,
                        "journal.recovered",
                        {"discardedSha256": hashlib.sha256(line).hexdigest()},
                    )
                    return self._events(run)
                raise JournalError(
                    "malformed terminated journal line"
                    if terminated
                    else "malformed journal tail"
                )
            result.append(self._validate_stored_event(event, run, i + 1))
        return result

    def _validate(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type not in EVENT_TYPES:
            raise JournalError("unknown event type")
        if not isinstance(data, dict):
            raise JournalError("event data must be an object")
        if event_type == "run.started":
            if not isinstance(data.get("objectiveSummary", ""), str) or not isinstance(
                data.get("metadata", {}), dict
            ):
                raise JournalError("invalid run metadata")
            for key in ("requirements", "gates"):
                values = data.get(key, [])
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    raise JournalError(f"invalid run {key}")
        if event_type in {
            "stage.planned",
            "dispatch.accepted",
            "handoff.received",
            "barrier.started",
            "barrier.completed",
        } and (not isinstance(data.get("stageId"), str) or not data["stageId"]):
            raise JournalError(f"{event_type} requires data.stageId")
        if event_type == "stage.planned":
            if data.get("status", "pending") not in STAGE_STATUSES:
                raise JournalError("invalid stage status")
            for key in ("dependencies", "requiredGates", "writerScopes"):
                values = data.get(key, [])
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    raise JournalError(f"invalid stage {key}")
        if event_type in {"dispatch.accepted", "handoff.received"} and (
            not isinstance(data.get("dispatchId"), str) or not data["dispatchId"]
        ):
            raise JournalError("dispatch event requires dispatchId")
        if event_type == "run.closed" and data.get("status") not in {
            "completed",
            "failed",
            "interrupted",
            "blocked",
        }:
            raise JournalError("invalid run close status")
        if event_type == "run.interrupted" and data.get("status") not in {
            None,
            "failed",
            "interrupted",
            "timed_out",
            "launch_failed",
        }:
            raise JournalError("invalid interruption status")
        if event_type in {"finding.updated", "requirement.updated"}:
            if not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_-]{0,79}", str(data.get("id", ""))
            ):
                raise JournalError("invalid finding/requirement id")
            allowed = (
                FINDING_STATUSES
                if event_type == "finding.updated"
                else REQUIREMENT_STATUSES
            )
            if data.get("status") not in allowed:
                raise JournalError("invalid status")
        if event_type == "verification.completed" and (
            not data.get("gateId") or data.get("status") not in GATE_STATUSES
        ):
            raise JournalError("verification requires gateId and gate status")
        if (
            event_type
            in {
                "dispatch.accepted",
                "handoff.received",
                "barrier.started",
                "barrier.completed",
            }
            and data.get(
                "status",
                "running"
                if event_type.endswith(("accepted", "started"))
                else "completed",
            )
            not in STAGE_STATUSES
        ):
            raise JournalError("invalid stage status")

    def _append_locked(
        self,
        run: Path,
        event_type: str,
        data: dict[str, Any],
        event_id: str | None = None,
        stage_id: str | None = None,
        attempt: int | None = None,
    ) -> dict[str, Any]:
        self._validate(event_type, data)
        events = self._events(run)
        event_id = event_id or uuid.uuid4().hex
        payload = {
            "type": event_type,
            "stageId": stage_id,
            "attempt": attempt,
            "data": redact(data),
            "redaction": {"policy": "bounded-v1"},
        }
        for old in events:
            if old["eventId"] == event_id:
                if canonical({k: old.get(k) for k in payload}) == canonical(payload):
                    return old
                raise JournalError("conflicting duplicate event id")
        if any(e["type"] == "run.closed" for e in events):
            raise JournalError("closed run is immutable")
        event = {
            "schema": SCHEMA,
            "eventId": event_id,
            "runId": run.name,
            "sequence": len(events) + 1,
            "occurredAtUtc": utcnow(),
            **payload,
        }
        encoded = (canonical(event) + "\n").encode()
        if len(encoded) > MAX_EVENT_BYTES:
            raise JournalError("event exceeds size limit")
        path = run / "journal.jsonl"
        fd = os.open(
            path,
            os.O_CREAT | os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            os.write(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)
        _chmod(path, 0o600)
        self._project(run)
        return event

    def append(
        self,
        run_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
        stage_id: str | None = None,
        attempt: int | None = None,
    ) -> dict[str, Any]:
        run = self._run(run_id)
        if not run.is_dir():
            raise JournalError("run not found")
        with self._locked(run):
            return self._append_locked(
                run, event_type, data or {}, event_id, stage_id, attempt
            )

    def _project(self, run: Path) -> dict[str, Any]:
        events = self._events(run)
        states = {
            "dispatches": {},
            "barriers": {},
            "requirements": {},
            "findings": {},
            "gates": {},
            "stages": {},
        }
        for e in events:
            d = e["data"]
            t = e["type"]
            if t == "run.started":
                states["requirements"].update(
                    {str(x): "pending" for x in d.get("requirements", [])}
                )
                states["gates"].update({str(x): "pending" for x in d.get("gates", [])})
            if t == "stage.planned":
                states["stages"][d["stageId"]] = {
                    "dependencies": sorted(d.get("dependencies", [])),
                    "requiredGates": sorted(d.get("requiredGates", [])),
                    "kind": d.get("kind", "unknown"),
                    "writerScopes": sorted(d.get("writerScopes", [])),
                    "status": d.get("status", "pending"),
                }
            if t in {"dispatch.accepted", "handoff.received"}:
                sid = d["stageId"]
                states["dispatches"][d.get("dispatchId", sid)] = d.get(
                    "status", "running" if t == "dispatch.accepted" else "completed"
                )
                if sid in states["stages"]:
                    states["stages"][sid]["status"] = d.get(
                        "status", "running" if t == "dispatch.accepted" else "completed"
                    )
            if t == "run.interrupted" and d.get("stageId"):
                sid = d["stageId"]
                states["dispatches"][d.get("dispatchId", sid)] = "interrupted"
                if sid in states["stages"]:
                    states["stages"][sid]["status"] = "interrupted"
            if t.startswith("barrier."):
                states["barriers"][d["stageId"]] = (
                    "running" if t.endswith("started") else d.get("status", "completed")
                )
            if t == "requirement.updated":
                states["requirements"][d["id"]] = d["status"]
            if t == "finding.updated":
                states["findings"][d["id"]] = d["status"]
            if t == "verification.completed":
                states["gates"][d["gateId"]] = d["status"]
        started = next((e["data"] for e in events if e["type"] == "run.started"), {})
        projection = {
            "schema": SCHEMA,
            "runId": run.name,
            "lastSequence": len(events),
            "closed": any(e["type"] == "run.closed" for e in events),
            "objectiveSummary": started.get("objectiveSummary", ""),
            "metadata": started.get("metadata", {}),
            **states,
        }
        self._atomic(run / "latest.json", projection)
        return projection

    def status(self, run_id: str) -> dict[str, Any]:
        run = self._run(run_id)
        with self._locked(run):
            return self._project(run)

    def resume(self, run_id: str) -> dict[str, Any]:
        run = self._run(run_id)
        with self._locked(run):
            manifest = self._manifest(run)
            now = repo_identity(self.repo)
            old = manifest["repository"]
            if any(
                old.get(k) != now.get(k)
                for k in ("rootHash", "commonGitHash", "worktreeHash")
            ):
                raise JournalError(
                    "repository/worktree identity changed; resume refused"
                )
            p = self._project(run)
            stages = p["stages"]
            for s in stages.values():
                if any(dep not in stages for dep in s["dependencies"]):
                    raise JournalError("stage dependency missing")

            def visit(sid: str, seen: set[str], stack: set[str]) -> None:
                if sid in stack:
                    raise JournalError("stage dependency cycle")
                if sid not in seen:
                    stack.add(sid)
                    [visit(x, seen, stack) for x in stages[sid]["dependencies"]]
                    stack.remove(sid)
                    seen.add(sid)

            seen = set()
            [visit(x, seen, set()) for x in stages]
            p["readyStageIds"] = sorted(
                s
                for s, v in stages.items()
                if v["status"] in {"pending", "ready"}
                and all(stages[d]["status"] == "completed" for d in v["dependencies"])
                and all(
                    p["gates"].get(g) == "passed" for g in v.get("requiredGates", [])
                )
            )
            p["drift"] = {
                k: {"expected": old[k], "actual": now[k]}
                for k in ("head", "branch", "dirtyDigest")
                if old.get(k) != now.get(k)
            }
            return p

    def close(
        self, run_id: str, *, status: str = "completed", summary: str = ""
    ) -> dict[str, Any]:
        if status not in {"completed", "failed", "interrupted", "blocked"}:
            raise JournalError("invalid close status")
        run = self._run(run_id)
        with self._locked(run):
            p = self._project(run)
            if status == "completed":
                for group in ("dispatches", "barriers"):
                    if any(v != "completed" for v in p[group].values()):
                        raise JournalError("cannot complete with open invariants")
                if any(v.get("status") != "completed" for v in p["stages"].values()):
                    raise JournalError("cannot complete with open invariants")
                for group in ("requirements", "gates"):
                    if any(
                        v not in {"passed", "not_applicable"} for v in p[group].values()
                    ):
                        raise JournalError("cannot complete with open invariants")
                if any(
                    v
                    not in {
                        "implemented",
                        "already_satisfied",
                        "invalid",
                        "duplicate",
                        "deferred",
                    }
                    for v in p["findings"].values()
                ):
                    raise JournalError("cannot complete with unresolved findings")
            return self._append_locked(
                run, "run.closed", {"status": status, "summary": summary}
            )

    def recover(self, run_id: str) -> dict[str, Any]:
        run = self._run(run_id)
        with self._locked(run):
            self._events(run, recover=True)
            return self._project(run)

    def prune(self, *, keep: int = 20) -> list[str]:
        if keep < 0:
            raise JournalError("keep must be non-negative")
        runs = sorted(
            (p for p in self.runs_root.iterdir() if p.is_dir() and not p.is_symlink()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        removed = []
        for p in runs[keep:]:
            with self._locked(p):
                if self._project(p)["closed"]:
                    shutil.rmtree(p)
                    removed.append(p.name)
        return removed


class RunJournal:
    """A run-bound public API suitable for an agent runner integration."""

    def __init__(self, journal: Journal, run_id: str):
        self._journal, self.run_id = journal, run_id

    @property
    def run_dir(self) -> Path:
        return self._journal._run(self.run_id)

    def append(
        self,
        event_type: str,
        *,
        data: dict[str, Any] | None = None,
        stage_id: str | None = None,
        attempt: int | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return self._journal.append(
            self.run_id,
            event_type,
            data,
            event_id=event_id,
            stage_id=stage_id,
            attempt=attempt,
        )

    def close(self, status: str, summary: str = "") -> dict[str, Any]:
        return self._journal.close(self.run_id, status=status, summary=summary)

    def status(self) -> dict[str, Any]:
        return self._journal.status(self.run_id)

    def resume(self) -> dict[str, Any]:
        return self._journal.resume(self.run_id)


def _api_journal(repo: str | Path, backend: str, state_home: str | None) -> Journal:
    if backend not in {"private", "repo"}:
        raise JournalError("backend must be private or repo")
    return Journal(
        repo,
        repo_local=backend == "repo",
        state_home=state_home if backend == "private" else None,
    )


def start_run(
    repo: str | Path,
    *,
    backend: str = "private",
    state_home: str | None = None,
    objective_summary: str = "",
    requirements: tuple[str, ...] = (),
    gates: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> RunJournal:
    journal = _api_journal(repo, backend, state_home)
    data = {
        "objectiveSummary": objective_summary,
        "requirements": list(requirements),
        "gates": list(gates),
        "metadata": metadata or {},
    }
    return RunJournal(journal, journal.start(run_id, data=data))


def open_run(
    repo: str | Path,
    run_id: str,
    *,
    backend: str = "private",
    state_home: str | None = None,
) -> RunJournal:
    journal = _api_journal(repo, backend, state_home)
    if not journal._run(run_id).is_dir():
        raise JournalError("run not found")
    return RunJournal(journal, run_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    def common(q: argparse.ArgumentParser, run: bool = False) -> None:
        q.add_argument("--repo", default=os.getcwd())
        q.add_argument("--backend", choices=("private", "repo"), default="private")
        q.add_argument("--state-home", "--state-root", dest="state_home")
        q.add_argument("--json", action="store_true")
        if run:
            q.add_argument("--run-id", required=True)

    q = sub.add_parser("init")
    q.add_argument("--repo", default=os.getcwd())
    q.add_argument("--json", action="store_true")
    q = sub.add_parser("start")
    common(q)
    q.add_argument("--run-id")
    q.add_argument("--data", default="{}")
    q = sub.add_parser("append")
    common(q, True)
    q.add_argument("event_type")
    q.add_argument("--data", default="{}")
    q.add_argument("--stage-id")
    q.add_argument("--attempt", type=int)
    q.add_argument("--event-id")
    for name in ("status", "resume", "recover"):
        q = sub.add_parser(name)
        common(q, True)
    q = sub.add_parser("close")
    common(q, True)
    q.add_argument("--status", default="completed")
    q.add_argument("--summary", default="")
    q = sub.add_parser("prune")
    common(q)
    q.add_argument("--keep", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = {"runsRoot": str(init_repo_backend(Path(args.repo)))}
        else:
            j = _api_journal(args.repo, args.backend, args.state_home)
            data = json.loads(getattr(args, "data", "{}"))
            if args.command == "start":
                result = {"runId": j.start(args.run_id, data=data)}
            elif args.command == "append":
                result = j.append(
                    args.run_id,
                    args.event_type,
                    data,
                    event_id=args.event_id,
                    stage_id=args.stage_id,
                    attempt=args.attempt,
                )
            elif args.command == "status":
                result = j.status(args.run_id)
            elif args.command == "resume":
                result = j.resume(args.run_id)
            elif args.command == "close":
                result = j.close(args.run_id, status=args.status, summary=args.summary)
            elif args.command == "recover":
                result = j.recover(args.run_id)
            else:
                result = {"removedRunIds": j.prune(keep=args.keep)}
        print(canonical(result) if args.json else json.dumps(result, indent=2))
        return 0
    except (JournalError, json.JSONDecodeError) as exc:
        print(f"journal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
