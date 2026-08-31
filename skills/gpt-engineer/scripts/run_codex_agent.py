#!/usr/bin/env python3
"""Run one model-pinned Codex delegate when native role routing is unavailable."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import run_journal

SKILL_ROOT = Path(__file__).resolve().parent.parent
HANDOFF_SCHEMA = SKILL_ROOT / "assets" / "codex" / "handoff.schema.json"
ROLES = {
    "sol-engineer": {
        "model": "gpt-5.6-sol",
        "effort": "high",
        "profile": "sol-engineer.toml",
        "write_capable": True,
    },
    "terra-explorer": {
        "model": "gpt-5.6-terra",
        "effort": "medium",
        "profile": "terra-explorer.toml",
        "write_capable": False,
    },
    "terra-worker": {
        "model": "gpt-5.6-terra",
        "effort": "medium",
        "profile": "terra-worker.toml",
        "write_capable": True,
    },
    "luna-worker": {
        "model": "gpt-5.6-luna",
        "effort": "low",
        "profile": "luna-worker.toml",
        "write_capable": True,
    },
    "luna-max-worker": {
        "model": "gpt-5.6-luna",
        "effort": "max",
        "service_tier": "fast",
        "profile": "luna-max-worker.toml",
        "write_capable": True,
    },
    "luna-verifier": {
        "model": "gpt-5.6-luna",
        "effort": "medium",
        "profile": "luna-verifier.toml",
        "write_capable": True,
    },
}


def validate_json_schema(
    value: object,
    schema: dict[str, object],
    path: str = "$",
) -> list[str]:
    """Validate the strict JSON Schema subset used by the handoff contract."""

    errors: list[str] = []
    expected_type = schema.get("type")
    type_checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: (
            isinstance(item, (int, float)) and not isinstance(item, bool)
        ),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if isinstance(expected_type, str):
        check = type_checks.get(expected_type)
        if check is None:
            return [f"{path}: unsupported schema type {expected_type!r}"]
        if not check(value):
            return [f"{path}: expected {expected_type}"]

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path}: value {value!r} is not in the allowed enum")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path}: string is shorter than {minimum}")
        if isinstance(maximum, int) and len(value) > maximum:
            errors.append(f"{path}: string is longer than {maximum}")

    if isinstance(value, list):
        maximum = schema.get("maxItems")
        if isinstance(maximum, int) and len(value) > maximum:
            errors.append(f"{path}: array has more than {maximum} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    validate_json_schema(item, item_schema, f"{path}[{index}]")
                )

    if isinstance(value, dict):
        properties = schema.get("properties")
        known = properties if isinstance(properties, dict) else {}
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    errors.append(f"{path}: missing required property {key!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in known:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, child_schema in known.items():
            if key in value and isinstance(child_schema, dict):
                errors.extend(
                    validate_json_schema(value[key], child_schema, f"{path}.{key}")
                )
    return errors


def role_instructions(role: str) -> str:
    path = SKILL_ROOT / "assets" / "codex" / "agents" / str(ROLES[role]["profile"])
    match = re.search(
        r'developer_instructions\s*=\s*"""(.*?)"""', path.read_text(), re.DOTALL
    )
    if not match:
        raise SystemExit(f"Missing developer_instructions in: {path}")
    return match.group(1).strip()


def codex_version(executable: str) -> tuple[tuple[int, ...], str]:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return (), "unknown"
    rendered = result.stdout.strip() or result.stderr.strip()
    match = re.search(r"(\d+(?:\.\d+)+)", rendered)
    return (
        tuple(int(part) for part in match.group(1).split(".")) if match else (),
        rendered,
    )


def resolve_codex(explicit: str | None) -> tuple[str, str]:
    if explicit:
        _, rendered = codex_version(explicit)
        return explicit, rendered
    candidates = [shutil.which("codex")]
    app_binary = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    if app_binary.is_file():
        candidates.append(str(app_binary))
    ranked = []
    for candidate in dict.fromkeys(value for value in candidates if value):
        version, rendered = codex_version(candidate)
        ranked.append((version, candidate, rendered))
    if not ranked:
        raise SystemExit("codex executable not found")
    _, executable, rendered = max(ranked, key=lambda item: item[0])
    return executable, rendered


def normalize_scope(values: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        candidate = PurePosixPath(value.replace(os.sep, "/"))
        if (
            candidate.is_absolute()
            or ".." in candidate.parts
            or str(candidate) in ("", ".")
        ):
            raise SystemExit(f"Invalid repository-relative path scope: {value}")
        normalized.append(str(candidate).rstrip("/"))
    return tuple(dict.fromkeys(normalized))


def path_in_scope(path: str, scopes: tuple[str, ...]) -> bool:
    return any(path == scope or path.startswith(scope + "/") for scope in scopes)


def git_paths(cwd: Path) -> set[str]:
    commands = (
        ["git", "diff", "--name-only", "-z"],
        ["git", "diff", "--cached", "--name-only", "-z"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True)
        paths.update(
            part.decode("utf-8") for part in result.stdout.split(b"\0") if part
        )
    return paths


def fingerprint(cwd: Path, path: str) -> str:
    target = cwd / path
    if not target.exists() and not target.is_symlink():
        return "missing"
    digest = hashlib.sha256()
    digest.update(str(target.lstat().st_mode).encode())
    if target.is_symlink():
        digest.update(os.readlink(target).encode())
    elif target.is_file():
        digest.update(target.read_bytes())
    else:
        digest.update(b"directory")
    return digest.hexdigest()


def snapshot(cwd: Path) -> dict[str, str]:
    return {path: fingerprint(cwd, path) for path in sorted(git_paths(cwd))}


def copy_path(source: Path, destination: Path) -> None:
    if not source.exists() and not source.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        elif destination.exists() or destination.is_symlink():
            destination.unlink()
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_dir() and not destination.is_symlink():
        shutil.rmtree(destination)
    elif destination.exists() or destination.is_symlink():
        destination.unlink()
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def git_changed_paths(candidate: Path, baseline_commit: str) -> list[str]:
    commands = (
        ["git", "diff", "--name-only", "-z", baseline_commit, "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=candidate, check=True, capture_output=True)
        paths.update(
            part.decode("utf-8") for part in result.stdout.split(b"\0") if part
        )
    return sorted(
        path
        for path in paths
        if path != ".gpt-engineer-evidence"
        and not path.startswith(".gpt-engineer-evidence/")
    )


def prepare_candidate(
    cwd: Path,
    output_dir: Path,
    baseline_paths: set[str],
) -> tuple[Path, str]:
    candidate = output_dir / "candidate-worktree"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-local",
            "--depth",
            "1",
            str(cwd),
            str(candidate),
        ],
        check=True,
        capture_output=True,
    )
    for path in sorted(baseline_paths):
        copy_path(cwd / path, candidate / path)
    subprocess.run(["git", "add", "-A"], cwd=candidate, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=SYMBaiEX",
            "-c",
            "user.email=solsymbaiex@gmail.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "Candidate baseline",
        ],
        cwd=candidate,
        check=True,
    )
    baseline_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=candidate,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return candidate, baseline_commit


def bundle_candidate_changes(
    candidate: Path,
    output_dir: Path,
    changed_paths: list[str],
    baseline_commit: str,
) -> tuple[str, str, list[str]]:
    unsafe_symlinks: list[str] = []
    for path in changed_paths:
        target = candidate / path
        if target.is_symlink():
            resolved = target.resolve(strict=False)
            if resolved != candidate and candidate not in resolved.parents:
                unsafe_symlinks.append(path)
    patch_result = subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", baseline_commit, "--"],
        cwd=candidate,
        check=True,
        capture_output=True,
    )
    patch_path = output_dir / "candidate.patch"
    patch_path.write_bytes(patch_result.stdout)
    changes_dir = output_dir / "candidate-changes"
    changes_dir.mkdir()
    deleted: list[str] = []
    if not unsafe_symlinks:
        for path in changed_paths:
            source = candidate / path
            destination = changes_dir / path
            if not source.exists() and not source.is_symlink():
                deleted.append(path)
            elif source.is_file() and not source.is_symlink():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            elif source.is_symlink():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(os.readlink(source))
    (output_dir / "deleted-paths.json").write_text(json.dumps(deleted, indent=2) + "\n")
    return str(changes_dir), str(patch_path), unsafe_symlinks


def external_symlinks(cwd: Path) -> list[str]:
    commands = (
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True)
        paths.update(
            part.decode("utf-8") for part in result.stdout.split(b"\0") if part
        )
    unsafe: list[str] = []
    for path in sorted(paths):
        target = cwd / path
        if not target.is_symlink():
            continue
        resolved = target.resolve(strict=False)
        if resolved != cwd and cwd not in resolved.parents:
            unsafe.append(path)
    return unsafe


def validate_write_scope(
    cwd: Path,
    baseline: dict[str, str],
    allow_paths: tuple[str, ...],
    allow_dirty: tuple[str, ...],
) -> None:
    if not allow_paths:
        raise SystemExit("Write-capable delegates require at least one --allow-path")
    invalid_dirty_scopes = [
        path for path in allow_dirty if not path_in_scope(path, allow_paths)
    ]
    if invalid_dirty_scopes:
        raise SystemExit("Every --allow-dirty-path must be inside an --allow-path")
    unsafe_symlinks = external_symlinks(cwd)
    if unsafe_symlinks:
        raise SystemExit(
            "Write-capable fallback refuses repositories with symlinks that resolve outside the "
            "worktree: " + ", ".join(unsafe_symlinks)
        )
    unauthorized = [
        path
        for path in baseline
        if path_in_scope(path, allow_paths) and not path_in_scope(path, allow_dirty)
    ]
    if unauthorized:
        joined = ", ".join(unauthorized)
        raise SystemExit(
            "Write scope overlaps pre-existing dirty paths; review them and pass "
            f"--allow-dirty-path explicitly: {joined}"
        )


def build_command(
    codex: str,
    role: str,
    cwd: Path,
    final_message_path: Path,
    allow_writes: bool,
) -> list[str]:
    profile = ROLES[role]
    if role in {"terra-worker", "luna-worker", "luna-max-worker"} and not allow_writes:
        raise SystemExit(f"{role} requires --allow-writes")
    sandbox = (
        "workspace-write" if profile["write_capable"] and allow_writes else "read-only"
    )
    command = [
        codex,
        "--ask-for-approval",
        "never",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--output-last-message",
        str(final_message_path),
        "--output-schema",
        str(HANDOFF_SCHEMA),
        "--cd",
        str(cwd),
        "--sandbox",
        sandbox,
        "--model",
        str(profile["model"]),
        "--config",
        f'model_reasoning_effort="{profile["effort"]}"',
        "--config",
        "features.multi_agent=false",
        "--config",
        'web_search="disabled"',
    ]
    if profile.get("service_tier"):
        command.extend(
            [
                "--config",
                f'service_tier="{profile["service_tier"]}"',
                "--config",
                "features.fast_mode=true",
            ]
        )
    if sandbox == "workspace-write":
        command.extend(
            [
                "--config",
                "sandbox_workspace_write.network_access=false",
                "--config",
                "sandbox_workspace_write.exclude_tmpdir_env_var=true",
                "--config",
                "sandbox_workspace_write.exclude_slash_tmp=true",
            ]
        )
    command.append("-")
    return command


def acquire_lock(cwd: Path, exclusive: bool, timeout: int):
    lock_root = Path(tempfile.gettempdir()) / "gpt-engineer-locks"
    lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_name = hashlib.sha256(str(cwd).encode()).hexdigest() + ".lock"
    handle = (lock_root / lock_name).open("a+")
    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                raise SystemExit("Timed out waiting for the repository delegate lock")
            time.sleep(0.1)


def stop_process_group(process: subprocess.Popen[bytes]) -> None:
    for sig, grace in ((signal.SIGINT, 2), (signal.SIGTERM, 2), (signal.SIGKILL, 0)):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        if grace:
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                continue


def close_process_pipes(process: subprocess.Popen[bytes]) -> None:
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def capture_stream(
    stream: object,
    destination: Path,
    maximum_bytes: int,
    state: dict[str, object],
) -> None:
    total = 0
    written = 0
    try:
        with destination.open("wb") as output:
            while True:
                chunk = stream.read(65536)  # type: ignore[attr-defined]
                if not chunk:
                    break
                total += len(chunk)
                if written < maximum_bytes:
                    retained = chunk[: maximum_bytes - written]
                    output.write(retained)
                    written += len(retained)
    except Exception as exc:  # pragma: no cover - defensive thread boundary
        state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        state["totalBytes"] = total
        state["retainedBytes"] = written
        state["truncated"] = total > maximum_bytes


def event_status(path: Path) -> tuple[bool, str | None]:
    completed = False
    failure: str | None = None
    if not path.exists():
        return completed, failure
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = str(event.get("type", ""))
        if event_type == "turn.completed":
            completed = True
        if event_type in ("turn.failed", "error"):
            failure = event_type
    return completed, failure


def atomic_write_json(path: Path, value: object) -> None:
    """Publish a complete result envelope without exposing a partial JSON file."""
    fd, temporary = tempfile.mkstemp(prefix=".result-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def journal_event_id(run_id: str, stage_id: str, attempt: int, event_type: str) -> str:
    value = f"gpt-engineer-runner/v1\0{run_id}\0{stage_id}\0{attempt}\0{event_type}"
    return "runner-" + hashlib.sha256(value.encode()).hexdigest()


def bounded_error(error: BaseException, cwd: Path) -> str:
    rendered = f"{type(error).__name__}: {error}"
    for sensitive, replacement in ((str(Path.home()), "~"), (str(cwd), "<repo>")):
        rendered = rendered.replace(sensitive, replacement)
    return rendered[:512]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=tuple(ROLES), required=True)
    parser.add_argument(
        "--stage-id", help="Stable stage identifier; defaults to the role"
    )
    parser.add_argument(
        "--cwd", default=".", help="Trusted Git worktree for the delegated task"
    )
    parser.add_argument("--prompt-file", help="Prompt file; otherwise read stdin")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory outside the repository for run evidence",
    )
    parser.add_argument("--codex", help="Codex executable path")
    parser.add_argument(
        "--allow-writes", action="store_true", help="Allow a write-capable role to edit"
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        help="Repository-relative write scope",
    )
    parser.add_argument(
        "--allow-dirty-path",
        action="append",
        default=[],
        help="Reviewed dirty path a writer may modify",
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--lock-timeout", type=int, default=30)
    parser.add_argument("--max-prompt-chars", type=int, default=24000)
    parser.add_argument("--max-events-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--max-stderr-bytes", type=int, default=2 * 1024 * 1024)
    parser.add_argument(
        "--journal-backend",
        choices=("private", "repo", "off"),
        default="private",
        help="Durable run journal; repo mode requires an explicit run_journal.py init",
    )
    parser.add_argument(
        "--journal-state-home", help="Private journal state home override"
    )
    parser.add_argument(
        "--journal-run-id", help="Attach this delegate to an existing run"
    )
    parser.add_argument(
        "--journal-lane-id", help="Stable lane identity; defaults to stage and attempt"
    )
    parser.add_argument("--journal-attempt", type=int, default=1)
    parser.add_argument(
        "--task-class", help="Stable task class for comparable outcome analysis"
    )
    parser.add_argument(
        "--acceptance-contract-hash",
        help="Hash of the unchanged acceptance contract for comparable outcome analysis",
    )
    parser.add_argument(
        "--route-context-json",
        default="{}",
        help="JSON object of non-route comparison variables",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    stage_id = args.stage_id or args.role
    if args.journal_attempt <= 0:
        parser.error("--journal-attempt must be positive")
    if args.journal_backend == "off" and (
        args.journal_state_home or args.journal_run_id or args.journal_lane_id
    ):
        parser.error("journal options cannot be combined with --journal-backend off")
    try:
        route_context = json.loads(args.route_context_json)
    except json.JSONDecodeError as exc:
        parser.error(f"--route-context-json must be valid JSON: {exc}")
    if not isinstance(route_context, dict):
        parser.error("--route-context-json must be a JSON object")
    for reserved in ("route", "model", "effort", "reasoningEffort", "mode"):
        route_context.pop(reserved, None)
    attempt = args.journal_attempt
    lane_id = args.journal_lane_id or f"{stage_id}:{attempt}"

    cwd = Path(args.cwd).expanduser().resolve()
    if not (cwd / ".git").exists():
        raise SystemExit(f"Not a Git repository root: {cwd}")
    output_dir = Path(args.output_dir).expanduser().resolve()
    if output_dir == cwd or cwd in output_dir.parents:
        raise SystemExit("--output-dir must be outside the delegated repository")
    codex, codex_version_text = resolve_codex(args.codex)

    prompt = (
        Path(args.prompt_file).read_text() if args.prompt_file else sys.stdin.read()
    )
    if not prompt.strip():
        raise SystemExit("Delegated prompt is empty")
    if (
        args.max_prompt_chars <= 0
        or args.max_events_bytes <= 0
        or args.max_stderr_bytes <= 0
    ):
        raise SystemExit("Prompt and output limits must be positive")
    if len(prompt) > args.max_prompt_chars:
        raise SystemExit(
            f"Delegated prompt has {len(prompt)} characters; limit is {args.max_prompt_chars}. "
            "Send a compact context packet or raise the limit explicitly."
        )
    allow_paths = normalize_scope(args.allow_path)
    allow_dirty = normalize_scope(args.allow_dirty_path)
    profile = ROLES[args.role]
    profile_sha256 = hashlib.sha256(
        (
            SKILL_ROOT / "assets" / "codex" / "agents" / str(profile["profile"])
        ).read_bytes()
    ).hexdigest()
    write_mode = bool(profile["write_capable"] and args.allow_writes)
    execution_mode = "isolated-candidate" if write_mode else "read-only"
    if args.dry_run:
        if write_mode:
            validate_write_scope(cwd, snapshot(cwd), allow_paths, allow_dirty)
        command = build_command(
            codex,
            args.role,
            cwd,
            output_dir / "last-message.txt",
            args.allow_writes,
        )
        print(
            json.dumps(
                {
                    "role": args.role,
                    "stageId": stage_id,
                    "model": profile["model"],
                    "reasoningEffort": profile["effort"],
                    "serviceTier": profile.get("service_tier", "default"),
                    "profileSha256": profile_sha256,
                    "codexVersion": codex_version_text,
                    "sandbox": command[command.index("--sandbox") + 1],
                    "allowPaths": allow_paths,
                    "isolatedCandidate": write_mode,
                    "promptCharacters": len(prompt),
                    "journal": {
                        "backend": args.journal_backend,
                        "requestedRunId": args.journal_run_id,
                        "laneId": lane_id,
                        "attempt": attempt,
                        "mutatesState": False,
                    },
                    "taskClass": args.task_class,
                    "acceptanceContractHash": args.acceptance_contract_hash,
                    "remainingRouteContext": route_context or None,
                    "command": command,
                },
                indent=2,
            )
        )
        return 0

    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(
            "--output-dir must be new or empty to prevent stale delegate evidence"
        )
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)
    started_at = datetime.now(timezone.utc)
    started_monotonic = time.monotonic()
    lock = acquire_lock(cwd, write_mode, args.lock_timeout)
    process: subprocess.Popen[bytes] | None = None
    timed_out = False
    launch_error: str | None = None
    lifecycle_error: str | None = None
    lifecycle_messages: list[str] = []
    baseline: dict[str, str] = {}
    after: dict[str, str] = {}
    candidate: Path | None = None
    candidate_baseline_commit: str | None = None
    candidate_head_commit: str | None = None
    final_message_path = output_dir / "last-message.txt"
    events_path = output_dir / "events.jsonl"
    stderr_path = output_dir / "stderr.log"
    capture_threads: list[threading.Thread] = []
    event_capture: dict[str, object] = {}
    stderr_capture: dict[str, object] = {}
    journal: run_journal.RunJournal | None = None
    journal_owned = False
    journal_errors: list[str] = []
    journal_status = "off" if args.journal_backend == "off" else "unavailable"
    dispatch_id: str | None = None
    lifecycle_signals = (signal.SIGTERM, signal.SIGHUP)
    previous_handlers = (
        {sig: signal.getsignal(sig) for sig in lifecycle_signals}
        if threading.current_thread() is threading.main_thread()
        else {}
    )

    def interrupt(signum: int, _frame: object) -> None:
        if process is not None:
            stop_process_group(process)
        raise KeyboardInterrupt(f"delegate runner received signal {signum}")

    for sig in previous_handlers:
        signal.signal(sig, interrupt)
    try:
        baseline = snapshot(cwd)
        if write_mode:
            validate_write_scope(cwd, baseline, allow_paths, allow_dirty)
            candidate, candidate_baseline_commit = prepare_candidate(
                cwd,
                output_dir,
                set(baseline),
            )
            internal_evidence = candidate / ".gpt-engineer-evidence"
            internal_evidence.mkdir()
            final_message_path = internal_evidence / "last-message.txt"
            execution_cwd = candidate
        else:
            execution_cwd = cwd
        command = build_command(
            codex,
            args.role,
            execution_cwd,
            final_message_path,
            args.allow_writes,
        )
        delegated_prompt = (
            role_instructions(args.role)
            + "\n\nDo not delegate further. Stay within the exact task and authority below.\n\n"
            + (
                "You are editing an isolated candidate copy. The original repository is not writable. "
                "Write only within these repository-relative paths: "
                + ", ".join(allow_paths)
                + ". Return a candidate change set for main-agent review; do not commit.\n"
                if write_mode
                else "This is a read-only task. Do not modify repository files.\n"
            )
            + (
                "The candidate includes these reviewed pre-existing dirty paths: "
                + ", ".join(allow_dirty)
                + ".\n"
                if allow_dirty
                else "Do not modify any pre-existing dirty path.\n"
            )
            + prompt.strip()
            + "\n\nReturn only the JSON handoff required by the configured output schema. "
            + f"Set stage_id to {stage_id!r}. Keep the summary bounded, cite file:symbol or "
            + "file:line evidence, echo assigned requirement IDs, report applicable gate results, "
            + "include a documentation disposition, distinguish passed/failed/skipped/not-run/"
            + "not-applicable/blocked checks, and name one concrete next action.\n"
            + "\n"
        )
        if len(delegated_prompt) > args.max_prompt_chars:
            raise SystemExit(
                f"Complete delegated prompt has {len(delegated_prompt)} characters; limit is "
                f"{args.max_prompt_chars}. Reduce the context packet or raise the limit explicitly."
            )
        if args.journal_backend != "off":
            try:
                if args.journal_run_id:
                    journal = run_journal.open_run(
                        cwd,
                        args.journal_run_id,
                        backend=args.journal_backend,
                        state_home=args.journal_state_home,
                    )
                else:
                    journal = run_journal.start_run(
                        cwd,
                        backend=args.journal_backend,
                        state_home=args.journal_state_home,
                        objective_summary=f"Codex delegate stage {stage_id}",
                        metadata={
                            "producer": "run_codex_agent.py",
                            "role": args.role,
                            "route": profile["model"],
                            "effort": profile["effort"],
                            "mode": execution_mode,
                            "profileSha256": profile_sha256,
                            "taskClass": args.task_class,
                            "acceptanceContractHash": args.acceptance_contract_hash,
                            "remainingRouteContext": route_context or None,
                        },
                    )
                    journal_owned = True
                dispatch_id = f"{journal.run_id}:{stage_id}:{attempt}"
                journal_projection = journal.status()
                if dispatch_id in journal_projection["dispatches"]:
                    raise SystemExit(
                        "The journal already contains this stage attempt; increment "
                        "--journal-attempt after reconciling its evidence"
                    )
                existing_stage = journal_projection["stages"].get(stage_id)
                if existing_stage and existing_stage.get("status") == "running":
                    raise SystemExit(
                        "The journal already has an active attempt for this stage; reconcile it "
                        "before dispatching another"
                    )
                if existing_stage is None:
                    journal.append(
                        "stage.planned",
                        stage_id=stage_id,
                        attempt=attempt,
                        event_id=journal_event_id(
                            journal.run_id, stage_id, attempt, "stage.planned"
                        ),
                        data={
                            "stageId": stage_id,
                            "status": "pending",
                            "kind": "fallback-delegate",
                            "dependencies": [],
                            "requiredGates": [],
                            "writerScopes": list(allow_paths) if write_mode else [],
                        },
                    )
                journal.append(
                    "dispatch.accepted",
                    stage_id=stage_id,
                    attempt=attempt,
                    event_id=journal_event_id(
                        journal.run_id, stage_id, attempt, "dispatch.accepted"
                    ),
                    data={
                        "stageId": stage_id,
                        "dispatchId": dispatch_id,
                        "laneId": lane_id,
                        "status": "running",
                        "role": args.role,
                        "route": profile["model"],
                        "effort": profile["effort"],
                        "mode": execution_mode,
                        "serviceTier": profile.get("service_tier", "default"),
                        "profileSha256": profile_sha256,
                        "taskClass": args.task_class,
                        "acceptanceContractHash": args.acceptance_contract_hash,
                        "remainingRouteContext": route_context or None,
                    },
                )
                journal_status = "attached" if not journal_owned else "running"
            except (OSError, ValueError, run_journal.JournalError) as exc:
                journal_errors.append(bounded_error(exc, cwd))
                journal_status = "error"
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            assert process.stdout is not None
            assert process.stderr is not None
            capture_threads = [
                threading.Thread(
                    target=capture_stream,
                    args=(
                        process.stdout,
                        events_path,
                        args.max_events_bytes,
                        event_capture,
                    ),
                    daemon=True,
                ),
                threading.Thread(
                    target=capture_stream,
                    args=(
                        process.stderr,
                        stderr_path,
                        args.max_stderr_bytes,
                        stderr_capture,
                    ),
                    daemon=True,
                ),
            ]
            for thread in capture_threads:
                thread.start()
            try:
                assert process.stdin is not None
                process.stdin.write(delegated_prompt.encode())
                process.stdin.close()
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_process_group(process)
        except OSError as exc:
            launch_error = f"Failed to launch Codex delegate: {exc}"
            lifecycle_messages.append(launch_error)
        after = snapshot(cwd)
        if candidate is not None:
            candidate_head_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=candidate,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
    except KeyboardInterrupt as exc:
        if process is not None:
            stop_process_group(process)
        lifecycle_error = f"Delegate lifecycle interrupted: {type(exc).__name__}: {exc}"
        lifecycle_messages.append(lifecycle_error)
        try:
            after = snapshot(cwd)
        except Exception as snapshot_error:
            after = baseline
            lifecycle_messages.append(
                f"Failed to capture post-interruption snapshot: {snapshot_error}"
            )
    except Exception:
        if candidate is not None:
            shutil.rmtree(candidate, ignore_errors=True)
            candidate = None
        if journal is not None and journal_owned:
            try:
                journal.close(
                    "failed",
                    "Delegate runner aborted before a result envelope was produced.",
                )
            except (OSError, ValueError, run_journal.JournalError):
                pass
        raise
    finally:
        if process is not None:
            stop_process_group(process)
            for thread in capture_threads:
                thread.join(timeout=5)
            if any(thread.is_alive() for thread in capture_threads):
                lifecycle_error = (
                    lifecycle_error or "Delegate output capture did not terminate"
                )
                lifecycle_messages.append(lifecycle_error)
            close_process_pipes(process)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

    if not events_path.exists():
        events_path.write_text("")
    if not stderr_path.exists():
        stderr_path.write_text("")
    if timed_out:
        lifecycle_messages.append("Timed out.")
    if lifecycle_messages:
        with stderr_path.open("a") as stderr_output:
            if stderr_path.stat().st_size:
                stderr_output.write("\n")
            stderr_output.write("\n".join(lifecycle_messages) + "\n")
    completed, failure = event_status(events_path)
    final_message = (
        final_message_path.read_text().strip() if final_message_path.exists() else ""
    )
    if final_message:
        (output_dir / "last-message.txt").write_text(final_message + "\n")
    violations: list[str] = []
    handoff: dict[str, object] | None = None
    if final_message:
        try:
            parsed_handoff = json.loads(final_message)
            if not isinstance(parsed_handoff, dict):
                violations.append("delegate handoff is not a JSON object")
            else:
                handoff = parsed_handoff
                schema = json.loads(HANDOFF_SCHEMA.read_text())
                violations.extend(
                    f"delegate handoff schema violation: {item}"
                    for item in validate_json_schema(handoff, schema)
                )
                if handoff.get("stage_id") != stage_id:
                    violations.append(
                        "delegate handoff stage_id does not match requested stage: "
                        f"{handoff.get('stage_id')!r} != {stage_id!r}"
                    )
        except json.JSONDecodeError as exc:
            violations.append(f"delegate handoff is not valid JSON: {exc}")
    if event_capture.get("truncated"):
        violations.append(
            f"delegate events exceeded {args.max_events_bytes} bytes and were truncated"
        )
    if stderr_capture.get("truncated"):
        violations.append(
            f"delegate stderr exceeded {args.max_stderr_bytes} bytes and was truncated"
        )
    for label, capture in (("events", event_capture), ("stderr", stderr_capture)):
        if capture.get("error"):
            violations.append(f"{label} capture failed: {capture['error']}")
    original_changes = sorted(
        path
        for path in set(baseline) | set(after)
        if baseline.get(path) != after.get(path)
    )
    if write_mode:
        assert candidate is not None
        assert candidate_baseline_commit is not None
        changed_paths = git_changed_paths(candidate, candidate_baseline_commit)
        violations.extend(
            f"original repository changed during isolated candidate run: {path}"
            for path in original_changes
        )
        violations.extend(
            f"out-of-scope candidate change: {path}"
            for path in changed_paths
            if not path_in_scope(path, allow_paths)
        )
        if candidate_head_commit != candidate_baseline_commit:
            violations.append("candidate delegate created one or more commits")
    else:
        changed_paths = original_changes
        if original_changes:
            violations.append("read-only delegate changed repository state")

    changes_directory: str | None = None
    candidate_patch: str | None = None
    if candidate is not None:
        assert candidate_baseline_commit is not None
        try:
            changes_directory, candidate_patch, unsafe_links = bundle_candidate_changes(
                candidate,
                output_dir,
                changed_paths,
                candidate_baseline_commit,
            )
            violations.extend(
                f"candidate symlink escapes worktree: {path}" for path in unsafe_links
            )
        finally:
            shutil.rmtree(candidate, ignore_errors=True)

    success = (
        not timed_out
        and launch_error is None
        and lifecycle_error is None
        and process is not None
        and process.returncode == 0
        and completed
        and failure is None
        and bool(final_message)
        and not violations
    )
    finished_at = datetime.now(timezone.utc)
    cleanup_verified = process is None or process.poll() is not None
    terminal_state = (
        "timed_out"
        if timed_out
        else "interrupted"
        if lifecycle_error
        else "launch_failed"
        if launch_error
        else "completed"
        if success
        else "failed"
    )
    envelope = {
        "runId": journal.run_id if journal is not None else None,
        "laneId": lane_id,
        "attempt": attempt,
        "dispatchId": dispatch_id,
        "role": args.role,
        "stageId": stage_id,
        "route": profile["model"],
        "effort": profile["effort"],
        "mode": execution_mode,
        "taskClass": args.task_class,
        "acceptanceContractHash": args.acceptance_contract_hash,
        "remainingRouteContext": route_context or None,
        "requestedModel": profile["model"],
        "requestedReasoningEffort": profile["effort"],
        "profileSha256": profile_sha256,
        "codexVersion": codex_version_text,
        "status": "completed" if success else "failed",
        "exitCode": process.returncode if process is not None else None,
        "changedPaths": changed_paths,
        "violations": violations,
        "finalMessage": final_message,
        "handoff": handoff,
        "routeEvidence": {
            "explicitModelFlag": True,
            "explicitReasoningConfig": True,
            "ignoredUserConfig": True,
            "recursiveDelegationDisabled": True,
        },
        "lifecycle": {
            "attempt": attempt,
            "startedAtUtc": started_at.isoformat().replace("+00:00", "Z"),
            "finishedAtUtc": finished_at.isoformat().replace("+00:00", "Z"),
            "durationMs": round((time.monotonic() - started_monotonic) * 1000),
            "processGroupId": process.pid if process is not None else None,
            "lockMode": "exclusive" if write_mode else "shared",
            "timedOut": timed_out,
            "completionEventObserved": completed,
            "failureEvent": failure,
            "cleanupVerified": cleanup_verified,
            "terminalState": terminal_state,
            "inputPromptCharacters": len(prompt),
            "delegatedPromptCharacters": len(delegated_prompt),
            "maxPromptCharacters": args.max_prompt_chars,
            "eventsBytes": event_capture.get("totalBytes", 0),
            "eventsRetainedBytes": event_capture.get("retainedBytes", 0),
            "eventsTruncated": bool(event_capture.get("truncated")),
            "stderrBytes": stderr_capture.get("totalBytes", 0),
            "stderrRetainedBytes": stderr_capture.get("retainedBytes", 0),
            "stderrTruncated": bool(stderr_capture.get("truncated")),
        },
        "appliedToRepository": False if write_mode else None,
        "candidateChangesDirectory": changes_directory,
        "candidatePatch": candidate_patch,
        "candidateBaselineCommit": candidate_baseline_commit,
        "candidateHeadCommit": candidate_head_commit,
    }
    if launch_error:
        envelope["launchError"] = launch_error
    if lifecycle_error:
        envelope["lifecycleError"] = lifecycle_error
    if journal is not None:
        journal_stage_status = (
            "completed" if success else "interrupted" if lifecycle_error else "failed"
        )
        try:
            if final_message:
                journal.append(
                    "handoff.received",
                    stage_id=stage_id,
                    attempt=attempt,
                    event_id=journal_event_id(
                        journal.run_id, stage_id, attempt, "handoff.received"
                    ),
                    data={
                        "stageId": stage_id,
                        "dispatchId": dispatch_id,
                        "laneId": lane_id,
                        "status": journal_stage_status,
                        "route": profile["model"],
                        "effort": profile["effort"],
                        "mode": execution_mode,
                        "durationMs": envelope["lifecycle"]["durationMs"],
                        "changedPaths": changed_paths,
                        "requirementIds": handoff.get("requirement_ids", [])
                        if handoff
                        else [],
                        "gateResults": handoff.get("gate_results", [])
                        if handoff
                        else [],
                        "checkCount": len(handoff.get("checks", [])) if handoff else 0,
                        "violationCount": len(violations),
                        "handoffSha256": hashlib.sha256(
                            final_message.encode()
                        ).hexdigest(),
                    },
                )
            else:
                journal.append(
                    "run.interrupted",
                    stage_id=stage_id,
                    attempt=attempt,
                    event_id=journal_event_id(
                        journal.run_id, stage_id, attempt, "run.interrupted"
                    ),
                    data={
                        "stageId": stage_id,
                        "dispatchId": dispatch_id,
                        "laneId": lane_id,
                        "status": terminal_state,
                        "reason": "delegate-finished-without-handoff",
                    },
                )
            if journal_owned:
                close_status = (
                    "completed"
                    if success
                    else "interrupted"
                    if lifecycle_error or timed_out
                    else "failed"
                )
                journal.close(
                    close_status, f"Delegate stage {stage_id} {close_status}."
                )
                journal_status = "closed"
        except (OSError, ValueError, run_journal.JournalError) as exc:
            journal_errors.append(bounded_error(exc, cwd))
            journal_status = "error"
    envelope["journal"] = {
        "schema": run_journal.SCHEMA,
        "backend": args.journal_backend,
        "ownedRun": journal_owned,
        "status": journal_status,
        "requestedRunId": args.journal_run_id,
    }
    if journal_errors:
        envelope["journalError"] = "; ".join(journal_errors)
    envelope["lifecycle"]["finishedAtUtc"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    envelope["lifecycle"]["durationMs"] = round(
        (time.monotonic() - started_monotonic) * 1000
    )
    atomic_write_json(output_dir / "result.json", envelope)
    if not success:
        print(f"Codex delegate failed closed; inspect {output_dir}", file=sys.stderr)
        return 124 if timed_out else 1
    print(final_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
