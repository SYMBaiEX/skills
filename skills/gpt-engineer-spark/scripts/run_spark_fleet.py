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
from pathlib import Path
from typing import Any


REQUIRED_MODEL = "gpt-5.3-codex-spark"
ROLES = {"spark-explorer", "spark-worker", "spark-verifier"}
READ_ONLY_ROLES = {"spark-explorer", "spark-verifier"}
TASK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
RUNNER = Path(__file__).resolve().with_name("run_spark_agent.py")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        wave = raw.get("wave", 0)
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or task_id in seen:
            raise SystemExit(f"Invalid or duplicate fleet task id: {task_id!r}")
        if role not in ROLES:
            raise SystemExit(f"Invalid Spark role for {task_id}: {role!r}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise SystemExit(f"Missing prompt for fleet task: {task_id}")
        if not isinstance(wave, int) or wave < 0:
            raise SystemExit(f"Invalid wave for fleet task: {task_id}")
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
                "required": raw.get("required", True) is not False,
                "allowPaths": allow_paths,
                "allowDirtyPaths": allow_dirty,
            }
        )
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
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.chmod(0o700)
    tasks = load_manifest(Path(args.manifest).expanduser().resolve())
    waves = {task["wave"] for task in tasks}
    writer_waves = {task["wave"] for task in tasks if task["role"] == "spark-worker"}
    if writer_waves and writer_waves != {max(waves)}:
        raise SystemExit("Candidate writers must occupy the terminal fleet wave")

    all_results: list[dict[str, Any]] = []
    stopped_after_wave: int | None = None
    for wave in sorted({task["wave"] for task in tasks}):
        wave_tasks = [task for task in tasks if task["wave"] == wave]
        results = run_wave(
            wave_tasks,
            cwd,
            output_root,
            args.codex,
            args.allow_writes,
            args.timeout,
            args.max_parallel,
        )
        all_results.extend(results)
        if any(result["required"] and result["status"] != "completed" for result in results):
            stopped_after_wave = wave
            break

    completed_ids = {result["id"] for result in all_results}
    skipped = [task["id"] for task in tasks if task["id"] not in completed_ids]
    complete = stopped_after_wave is None and not skipped and all(
        not result["required"] or result["status"] == "completed" for result in all_results
    )
    envelope = {
        "status": "completed" if complete else "incomplete",
        "requiredModel": REQUIRED_MODEL,
        "routeMethod": "cli-explicit-model",
        "maxParallel": args.max_parallel,
        "stoppedAfterWave": stopped_after_wave,
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
