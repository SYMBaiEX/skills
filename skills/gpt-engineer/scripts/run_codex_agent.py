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
import time
from pathlib import Path, PurePosixPath


SKILL_ROOT = Path(__file__).resolve().parent.parent
ROLES = {
    "sol-engineer": {
        "model": "gpt-5.6",
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
    "luna-verifier": {
        "model": "gpt-5.6-luna",
        "effort": "medium",
        "profile": "luna-verifier.toml",
        "write_capable": True,
    },
}


def role_instructions(role: str) -> str:
    path = SKILL_ROOT / "assets" / "codex" / "agents" / str(ROLES[role]["profile"])
    match = re.search(r'developer_instructions\s*=\s*"""(.*?)"""', path.read_text(), re.S)
    if not match:
        raise SystemExit(f"Missing developer_instructions in: {path}")
    return match.group(1).strip()


def codex_version(executable: str) -> tuple[tuple[int, ...], str]:
    try:
        result = subprocess.run(
            [executable, "--version"], check=True, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return (), "unknown"
    rendered = result.stdout.strip() or result.stderr.strip()
    match = re.search(r"(\d+(?:\.\d+)+)", rendered)
    return (tuple(int(part) for part in match.group(1).split(".")) if match else (), rendered)


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
        if candidate.is_absolute() or ".." in candidate.parts or str(candidate) in ("", "."):
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
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True)
        paths.update(part.decode("utf-8") for part in result.stdout.split(b"\0") if part)
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


def external_symlinks(cwd: Path) -> list[str]:
    commands = (
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True)
        paths.update(part.decode("utf-8") for part in result.stdout.split(b"\0") if part)
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
    invalid_dirty_scopes = [path for path in allow_dirty if not path_in_scope(path, allow_paths)]
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
    output_dir: Path,
    allow_writes: bool,
) -> list[str]:
    profile = ROLES[role]
    if role == "terra-worker" and not allow_writes:
        raise SystemExit("terra-worker requires --allow-writes")
    sandbox = "workspace-write" if profile["write_capable"] and allow_writes else "read-only"
    command = [
        codex,
        "--ask-for-approval",
        "never",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--output-last-message",
        str(output_dir / "last-message.txt"),
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
    if sandbox == "workspace-write":
        command.extend(["--config", "sandbox_workspace_write.network_access=false"])
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


def stop_process_group(process: subprocess.Popen[str]) -> None:
    for sig, grace in ((signal.SIGINT, 2), (signal.SIGTERM, 2), (signal.SIGKILL, 0)):
        if process.poll() is not None:
            return
        os.killpg(process.pid, sig)
        if grace:
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                continue


def event_status(stdout: str) -> tuple[bool, str | None]:
    completed = False
    failure: str | None = None
    for line in stdout.splitlines():
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=tuple(ROLES), required=True)
    parser.add_argument("--cwd", default=".", help="Trusted Git worktree for the delegated task")
    parser.add_argument("--prompt-file", help="Prompt file; otherwise read stdin")
    parser.add_argument("--output-dir", required=True, help="Directory outside the repository for run evidence")
    parser.add_argument("--codex", help="Codex executable path")
    parser.add_argument("--allow-writes", action="store_true", help="Allow a write-capable role to edit")
    parser.add_argument("--allow-path", action="append", default=[], help="Repository-relative write scope")
    parser.add_argument(
        "--allow-dirty-path", action="append", default=[], help="Reviewed dirty path a writer may modify"
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--lock-timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).expanduser().resolve()
    if not (cwd / ".git").exists():
        raise SystemExit(f"Not a Git repository root: {cwd}")
    output_dir = Path(args.output_dir).expanduser().resolve()
    if output_dir == cwd or cwd in output_dir.parents:
        raise SystemExit("--output-dir must be outside the delegated repository")
    codex, codex_version_text = resolve_codex(args.codex)

    prompt = Path(args.prompt_file).read_text() if args.prompt_file else sys.stdin.read()
    if not prompt.strip():
        raise SystemExit("Delegated prompt is empty")
    allow_paths = normalize_scope(args.allow_path)
    allow_dirty = normalize_scope(args.allow_dirty_path)
    profile = ROLES[args.role]
    write_mode = bool(profile["write_capable"] and args.allow_writes)
    baseline = snapshot(cwd)
    if write_mode:
        validate_write_scope(cwd, baseline, allow_paths, allow_dirty)

    command = build_command(codex, args.role, cwd, output_dir, args.allow_writes)
    delegated_prompt = (
        role_instructions(args.role)
        + "\n\nDo not delegate further. Stay within the exact task and authority below.\n\n"
        + (
            "Write only within these repository-relative paths: " + ", ".join(allow_paths) + ".\n"
            if write_mode
            else "This is a read-only task. Do not modify repository files.\n"
        )
        + (
            "Reviewed pre-existing dirty paths you may modify: " + ", ".join(allow_dirty) + ".\n"
            if allow_dirty
            else "Do not modify any pre-existing dirty path.\n"
        )
        + prompt.strip()
        + "\n"
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "role": args.role,
                    "model": profile["model"],
                    "codexVersion": codex_version_text,
                    "sandbox": command[command.index("--sandbox") + 1],
                    "allowPaths": allow_paths,
                    "promptCharacters": len(delegated_prompt),
                    "command": command,
                },
                indent=2,
            )
        )
        return 0

    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)
    lock = acquire_lock(cwd, write_mode, args.lock_timeout)
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
        message = f"Failed to launch Codex delegate: {exc}"
        (output_dir / "events.jsonl").write_text("")
        (output_dir / "stderr.log").write_text(message + "\n")
        envelope = {
            "role": args.role,
            "requestedModel": profile["model"],
            "codexVersion": codex_version_text,
            "status": "failed",
            "exitCode": None,
            "changedPaths": [],
            "violations": [],
            "finalMessage": "",
            "launchError": message,
        }
        (output_dir / "result.json").write_text(json.dumps(envelope, indent=2) + "\n")
        print(f"Codex delegate failed closed; inspect {output_dir}", file=sys.stderr)
        return 1
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=delegated_prompt, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_process_group(process)
        stdout, stderr = process.communicate()
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

    (output_dir / "events.jsonl").write_text(stdout)
    (output_dir / "stderr.log").write_text(stderr + ("\nTimed out.\n" if timed_out else ""))
    final_path = output_dir / "last-message.txt"
    completed, failure = event_status(stdout)
    final_message = final_path.read_text().strip() if final_path.exists() else ""
    after = snapshot(cwd)
    changed_paths = sorted(
        path for path in set(baseline) | set(after) if baseline.get(path) != after.get(path)
    )
    violations: list[str] = []
    for path, before_fingerprint in baseline.items():
        if fingerprint(cwd, path) != before_fingerprint and not path_in_scope(path, allow_dirty):
            violations.append(f"modified pre-existing dirty path: {path}")
    if write_mode:
        violations.extend(
            f"out-of-scope changed path: {path}"
            for path in after
            if path not in baseline and not path_in_scope(path, allow_paths)
        )
    elif after != baseline:
        violations.append("read-only delegate changed repository state")

    success = (
        not timed_out
        and process.returncode == 0
        and completed
        and failure is None
        and bool(final_message)
        and not violations
    )
    envelope = {
        "role": args.role,
        "requestedModel": profile["model"],
        "codexVersion": codex_version_text,
        "status": "completed" if success else "failed",
        "exitCode": process.returncode,
        "changedPaths": changed_paths,
        "violations": violations,
        "finalMessage": final_message,
    }
    (output_dir / "result.json").write_text(json.dumps(envelope, indent=2) + "\n")
    if not success:
        print(f"Codex delegate failed closed; inspect {output_dir}", file=sys.stderr)
        return 124 if timed_out else 1
    print(final_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
