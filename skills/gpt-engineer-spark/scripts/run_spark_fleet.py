#!/usr/bin/env python3
"""Run model-pinned Spark delegates in safe, ordered fleet waves."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_MODEL = "gpt-5.3-codex-spark"
ROLES = {"spark-explorer", "spark-worker", "spark-verifier"}
READ_ONLY_ROLES = {"spark-explorer", "spark-verifier"}
TASK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
RUNNER = Path(__file__).resolve().with_name("run_spark_agent.py")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_paths(values: list[str], field: str, task_id: str) -> list[str]:
    normalized: list[str] = []
    for raw in values:
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"{field} must contain repository-relative paths for: {task_id}")
        value = path.as_posix()
        if value in {"", "."}:
            raise SystemExit(f"{field} must not contain an empty repository scope for: {task_id}")
        if value not in normalized:
            normalized.append(value)
    return normalized


def scopes_overlap(left: str, right: str) -> bool:
    if "." in {left, right}:
        return True
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    shared = min(len(left_parts), len(right_parts))
    return left_parts[:shared] == right_parts[:shared]


def load_manifest(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text())
    tasks = document.get("tasks") if isinstance(document, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit("Fleet manifest must contain a non-empty tasks array")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in tasks:
        if not isinstance(raw, dict):
            raise SystemExit("Every fleet task must be an object")
        task_id = raw.get("id")
        role = raw.get("role")
        prompt = raw.get("prompt")
        wave = raw.get("wave")
        depends_on = raw.get("dependsOn", [])
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or task_id in seen:
            raise SystemExit(f"Invalid or duplicate fleet task id: {task_id!r}")
        if role not in ROLES:
            raise SystemExit(f"Invalid Spark role for {task_id}: {role!r}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise SystemExit(f"Missing prompt for fleet task: {task_id}")
        if wave is not None and (not isinstance(wave, int) or wave < 0):
            raise SystemExit(f"Invalid wave for fleet task: {task_id}")
        if not isinstance(depends_on, list) or not all(isinstance(item, str) for item in depends_on):
            raise SystemExit(f"dependsOn must be a string array for: {task_id}")
        allow_paths = raw.get("allowPaths", [])
        allow_dirty = raw.get("allowDirtyPaths", [])
        if not isinstance(allow_paths, list) or not all(isinstance(item, str) for item in allow_paths):
            raise SystemExit(f"allowPaths must be a string array for: {task_id}")
        if not isinstance(allow_dirty, list) or not all(isinstance(item, str) for item in allow_dirty):
            raise SystemExit(f"allowDirtyPaths must be a string array for: {task_id}")
        seen.add(task_id)
        normalized.append(
            {
                "id": task_id,
                "role": role,
                "prompt": prompt.strip(),
                "wave": wave,
                "dependsOn": list(dict.fromkeys(depends_on)),
                "required": raw.get("required", True) is not False,
                "allowPaths": normalize_paths(allow_paths, "allowPaths", task_id),
                "allowDirtyPaths": normalize_paths(allow_dirty, "allowDirtyPaths", task_id),
            }
        )
    by_id = {task["id"]: task for task in normalized}
    for task in normalized:
        missing = [dependency for dependency in task["dependsOn"] if dependency not in by_id]
        if missing:
            raise SystemExit(f"Unknown dependencies for {task['id']}: {', '.join(missing)}")
        if task["id"] in task["dependsOn"]:
            raise SystemExit(f"Task cannot depend on itself: {task['id']}")

    visiting: list[str] = []
    levels: dict[str, int] = {}

    def level(task_id: str) -> int:
        if task_id in levels:
            return levels[task_id]
        if task_id in visiting:
            start = visiting.index(task_id)
            cycle = visiting[start:] + [task_id]
            raise SystemExit("Fleet dependency cycle: " + " -> ".join(cycle))
        visiting.append(task_id)
        dependencies = by_id[task_id]["dependsOn"]
        dependency_level = max((level(dependency) + 1 for dependency in dependencies), default=0)
        visiting.pop()
        explicit_wave = by_id[task_id]["wave"]
        if explicit_wave is not None and explicit_wave < dependency_level:
            raise SystemExit(
                f"Explicit wave for {task_id} precedes one of its dependencies "
                f"(minimum {dependency_level})"
            )
        levels[task_id] = max(explicit_wave or 0, dependency_level)
        return levels[task_id]

    for task in normalized:
        task["wave"] = level(task["id"])
    return normalized


def delegate_command(
    task: dict[str, Any],
    cwd: Path,
    output_dir: Path,
    codex: str | None,
    allow_writes: bool,
    timeout: int,
) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--role",
        task["role"],
        "--cwd",
        str(cwd),
        "--output-dir",
        str(output_dir),
        "--timeout",
        str(timeout),
    ]
    if codex:
        command.extend(["--codex", codex])
    if task["role"] == "spark-worker":
        if not allow_writes:
            raise SystemExit("Spark worker tasks require fleet-level --allow-writes")
        if not task["allowPaths"]:
            raise SystemExit(f"Spark worker requires allowPaths: {task['id']}")
        command.append("--allow-writes")
        for path in task["allowPaths"]:
            command.extend(["--allow-path", path])
        for path in task["allowDirtyPaths"]:
            command.extend(["--allow-dirty-path", path])
    elif task["allowPaths"] or task["allowDirtyPaths"]:
        raise SystemExit(f"Read-only task cannot declare write paths: {task['id']}")
    return command


def run_task(
    task: dict[str, Any],
    cwd: Path,
    output_root: Path,
    codex: str | None,
    allow_writes: bool,
    timeout: int,
) -> dict[str, Any]:
    started = now()
    task_output = output_root / task["id"]
    command = delegate_command(task, cwd, task_output, codex, allow_writes, timeout)
    try:
        process = subprocess.run(
            command,
            input=task["prompt"] + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
        returncode: int | None = process.returncode
        stderr = process.stderr
    except OSError as exc:
        returncode = None
        stderr = f"Failed to launch Spark delegate runner: {exc}"
    result_path = task_output / "result.json"
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            result = {
                "status": "failed",
                "exitCode": returncode,
                "changedPaths": [],
                "violations": [f"invalid delegate result.json: {exc}"],
                "finalMessage": "",
            }
    else:
        result = {
            "status": "failed",
            "exitCode": returncode,
            "changedPaths": [],
            "violations": ["delegate did not emit result.json"],
            "finalMessage": "",
        }
    completed = returncode == 0 and result.get("status") == "completed"
    return {
        "id": task["id"],
        "wave": task["wave"],
        "role": task["role"],
        "required": task["required"],
        "routeMethod": "cli-explicit-model",
        "requestedModel": REQUIRED_MODEL,
        "serverAcceptedRequest": completed,
        "modelAttestedByRuntime": None,
        "startedAt": started,
        "endedAt": now(),
        "status": "completed" if completed else "failed",
        "changedPaths": result.get("changedPaths", []),
        "violations": result.get("violations", []),
        "finalMessage": result.get("finalMessage", ""),
        "candidateChangesDirectory": result.get("candidateChangesDirectory"),
        "candidatePatch": result.get("candidatePatch"),
        "deletedPathsFile": (
            str(task_output / "deleted-paths.json")
            if (task_output / "deleted-paths.json").exists()
            else None
        ),
        "evidenceDirectory": str(task_output),
        "stderrTail": stderr[-2000:],
    }


def run_wave(
    tasks: list[dict[str, Any]],
    cwd: Path,
    output_root: Path,
    codex: str | None,
    allow_writes: bool,
    timeout: int,
    max_parallel: int,
) -> list[dict[str, Any]]:
    has_writer = any(task["role"] == "spark-worker" for task in tasks)
    if has_writer and any(task["role"] in READ_ONLY_ROLES for task in tasks):
        raise SystemExit("Do not mix readers and writers in the same fleet wave")
    if has_writer:
        return [
            run_task(task, cwd, output_root, codex, allow_writes, timeout)
            for task in tasks
        ]
    results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_parallel, len(tasks))) as pool:
        futures = {
            pool.submit(run_task, task, cwd, output_root, codex, allow_writes, timeout): task["id"]
            for task in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    return [results[task["id"]] for task in tasks]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="JSON fleet task manifest")
    parser.add_argument("--cwd", default=".", help="Trusted Git worktree")
    parser.add_argument("--output-dir", required=True, help="Evidence directory outside the repository")
    parser.add_argument("--codex", help="Codex executable path")
    parser.add_argument("--allow-writes", action="store_true", help="Authorize manifest worker tasks")
    parser.add_argument("--max-parallel", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout per delegate")
    args = parser.parse_args(argv)

    if not 1 <= args.max_parallel <= 5:
        raise SystemExit("--max-parallel must be between 1 and 5")
    cwd = Path(args.cwd).expanduser().resolve()
    if not (cwd / ".git").exists():
        raise SystemExit(f"Not a Git repository root: {cwd}")
    output_root = Path(args.output_dir).expanduser().resolve()
    if output_root == cwd or cwd in output_root.parents:
        raise SystemExit("--output-dir must be outside the delegated repository")
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit("--output-dir must be new or empty to prevent stale fleet evidence")
    tasks = load_manifest(Path(args.manifest).expanduser().resolve())
    waves = {task["wave"] for task in tasks}
    writer_waves = {task["wave"] for task in tasks if task["role"] == "spark-worker"}
    if writer_waves and writer_waves != {max(waves)}:
        raise SystemExit("Candidate writers must occupy the terminal fleet wave")
    for wave in waves:
        wave_tasks = [task for task in tasks if task["wave"] == wave]
        has_writer = any(task["role"] == "spark-worker" for task in wave_tasks)
        if has_writer and any(task["role"] in READ_ONLY_ROLES for task in wave_tasks):
            raise SystemExit("Do not mix readers and writers in the same fleet wave")
    writers = [task for task in tasks if task["role"] == "spark-worker"]
    for index, writer in enumerate(writers):
        for other in writers[index + 1 :]:
            overlaps = [
                f"{left} <> {right}"
                for left in writer["allowPaths"]
                for right in other["allowPaths"]
                if scopes_overlap(left, right)
            ]
            if overlaps:
                raise SystemExit(
                    f"Overlapping candidate writer scopes for {writer['id']} and {other['id']}: "
                    + ", ".join(overlaps)
                )
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.chmod(0o700)

    all_results: list[dict[str, Any]] = []
    results_by_id: dict[str, dict[str, Any]] = {}
    for wave in sorted({task["wave"] for task in tasks}):
        wave_tasks = [task for task in tasks if task["wave"] == wave]
        runnable: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for task in wave_tasks:
            blocked_by = [
                dependency
                for dependency in task["dependsOn"]
                if results_by_id[dependency]["status"] != "completed"
            ]
            if blocked_by:
                result = {
                    "id": task["id"],
                    "wave": task["wave"],
                    "role": task["role"],
                    "required": task["required"],
                    "routeMethod": "cli-explicit-model",
                    "requestedModel": REQUIRED_MODEL,
                    "serverAcceptedRequest": False,
                    "modelAttestedByRuntime": None,
                    "startedAt": None,
                    "endedAt": None,
                    "status": "skipped",
                    "blockedBy": blocked_by,
                    "changedPaths": [],
                    "violations": ["dependency did not complete"],
                    "finalMessage": "",
                    "candidateChangesDirectory": None,
                    "candidatePatch": None,
                    "deletedPathsFile": None,
                    "evidenceDirectory": None,
                    "stderrTail": "",
                }
                results.append(result)
                results_by_id[task["id"]] = result
            else:
                runnable.append(task)
        if runnable:
            executed = run_wave(
                runnable,
                cwd,
                output_root,
                args.codex,
                args.allow_writes,
                args.timeout,
                args.max_parallel,
            )
            results.extend(executed)
            results_by_id.update({result["id"]: result for result in executed})
        results.sort(key=lambda result: [task["id"] for task in wave_tasks].index(result["id"]))
        all_results.extend(results)

    skipped = [result["id"] for result in all_results if result["status"] == "skipped"]
    failed = [result["id"] for result in all_results if result["status"] == "failed"]
    complete = all(
        not result["required"] or result["status"] == "completed" for result in all_results
    )
    envelope = {
        "schema": "gpt-engineer-spark-fleet/v2",
        "status": "completed" if complete else "incomplete",
        "requiredModel": REQUIRED_MODEL,
        "routeMethod": "cli-explicit-model",
        "maxParallel": args.max_parallel,
        "stoppedAfterWave": None,
        "failedTaskIds": failed,
        "skippedTaskIds": skipped,
        "delegates": all_results,
        "requiresMainAgentIntegration": bool(writer_waves),
    }
    (output_root / "fleet-result.json").write_text(json.dumps(envelope, indent=2) + "\n")
    if not complete:
        print(f"Spark fleet incomplete; inspect {output_root}", file=sys.stderr)
        return 1
    print(json.dumps(envelope, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
