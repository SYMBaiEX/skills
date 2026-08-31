#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import run_journal


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "a").write_text("a")
        subprocess.run(["git", "add", "a"], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=a@b",
                "-c",
                "user.name=a",
                "commit",
                "-qm",
                "init",
            ],
            cwd=self.repo,
            check=True,
        )
        self.j = run_journal.Journal(self.repo, Path(self.temp.name) / "state")

    def tearDown(self):
        self.temp.cleanup()

    def test_default_private_and_no_repo_mutation(self):
        j = run_journal.Journal(self.repo, Path(self.temp.name) / "private")
        r = j.start()
        self.assertFalse((self.repo / ".engineer").exists())
        self.assertEqual((j._run(r) / "journal.jsonl").stat().st_mode & 0o777, 0o600)

    def test_explicit_repo_opt_in(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                run_journal.main(["init", "--repo", str(self.repo), "--json"]), 0
            )
        p = run_journal.init_repo_backend(self.repo)
        self.assertEqual(
            (p.parent / ".gitignore").read_text(), "runs/\n!config.json\n!.gitignore\n"
        )
        self.assertEqual((p.parent / ".gitignore").stat().st_mode & 0o777, 0o600)

    def test_concurrent_appenders(self):
        r = self.j.start()
        with concurrent.futures.ThreadPoolExecutor(8) as x:
            list(
                x.map(
                    lambda n: self.j.append(
                        r,
                        "command.completed",
                        {"commandId": str(n), "status": "completed"},
                    ),
                    range(8),
                )
            )
        self.assertEqual(self.j.status(r)["lastSequence"], 9)

    def test_idempotency_and_conflict(self):
        r = self.j.start()
        self.j.append(r, "command.completed", {"status": "completed"}, event_id="x")
        self.j.append(r, "command.completed", {"status": "completed"}, event_id="x")
        with self.assertRaisesRegex(run_journal.JournalError, "conflicting"):
            self.j.append(r, "command.completed", {"status": "failed"}, event_id="x")

    def test_partial_tail_and_corrupt_full_line(self):
        r = self.j.start()
        p = self.j._run(r) / "journal.jsonl"
        p.write_bytes(p.read_bytes() + b"{bad")
        self.j.recover(r)
        self.assertTrue(
            any(
                e["type"] == "journal.recovered" for e in self.j._events(self.j._run(r))
            )
        )
        r = self.j.start()
        p = self.j._run(r) / "journal.jsonl"
        p.write_bytes(p.read_bytes() + b"{bad}\n")
        with self.assertRaises(run_journal.JournalError):
            self.j.recover(r)
        r = self.j.start()
        p = self.j._run(r) / "journal.jsonl"
        p.write_bytes(p.read_bytes() + b"\xff")
        self.j.recover(r)
        self.assertTrue(
            any(
                e["type"] == "journal.recovered" for e in self.j._events(self.j._run(r))
            )
        )

    def test_close_invariants_and_terminal(self):
        r = self.j.start()
        self.j.append(r, "requirement.updated", {"id": "J1", "status": "pending"})
        with self.assertRaises(run_journal.JournalError):
            self.j.close(r)
        self.j.append(r, "requirement.updated", {"id": "J1", "status": "passed"})
        self.j.close(r)
        with self.assertRaises(run_journal.JournalError):
            self.j.append(r, "command.completed", {"status": "completed"})

    def test_symlink_and_redaction(self):
        r = self.j.start()
        p = self.j._run(r) / "latest.json"
        p.unlink()
        p.symlink_to("/tmp/x")
        with self.assertRaises(run_journal.JournalError):
            self.j.status(r)
        r = self.j.start()
        self.j.append(
            r,
            "command.completed",
            {
                "output": "token=supersecretvalue01234567890123456789",
                "status": "completed",
            },
        )
        self.assertIn("[REDACTED]", (self.j._run(r) / "journal.jsonl").read_text())

    def test_resume_and_prune(self):
        r = self.j.start()
        self.j.append(r, "stage.planned", {"stageId": "a", "dependencies": []})
        self.assertEqual(self.j.resume(r)["readyStageIds"], ["a"])
        self.j.append(
            r,
            "dispatch.accepted",
            {"stageId": "a", "dispatchId": "a-1", "status": "completed"},
        )
        self.j.close(r)
        self.assertEqual(self.j.prune(keep=0), [r])

    def test_api_requirements_gates_and_verification(self):
        run = run_journal.start_run(
            self.repo,
            state_home=str(Path(self.temp.name) / "api"),
            requirements=("J1",),
            gates=("Q1",),
        )
        self.assertEqual(run.status()["requirements"]["J1"], "pending")
        run.append("verification.completed", data={"gateId": "Q1", "status": "passed"})
        self.assertEqual(run.status()["gates"]["Q1"], "passed")

    def test_state_root_symlink_rejected(self):
        target = Path(self.temp.name) / "target"
        target.mkdir()
        link = Path(self.temp.name) / "link"
        link.symlink_to(target)
        with self.assertRaises(run_journal.JournalError):
            run_journal.Journal(self.repo, link)

    def test_private_state_inside_repo_is_rejected_without_mutation(self):
        target = self.repo / ".private-state"
        with self.assertRaisesRegex(run_journal.JournalError, "outside checkout"):
            run_journal.Journal(self.repo, target)
        self.assertFalse(target.exists())

    def test_key_aware_redaction_and_dirty_drift(self):
        r = self.j.start(
            data={
                "metadata": {
                    "apiKey": "raw-value",
                    "url": "https://x.test/?token=raw-query",
                }
            }
        )
        text = (self.j._run(r) / "journal.jsonl").read_text()
        self.assertNotIn("raw-value", text)
        self.assertNotIn("raw-query", text)
        (self.repo / "a").write_text("changed")
        self.assertIn("dirtyDigest", self.j.resume(r)["drift"])

    def test_completed_close_rejects_failed_gate(self):
        r = self.j.start(data={"gates": ["Q1"]})
        self.j.append(r, "verification.completed", {"gateId": "Q1", "status": "failed"})
        with self.assertRaises(run_journal.JournalError):
            self.j.close(r)

    def test_sibling_worktree_resume_rejected(self):
        r = self.j.start()
        sibling = Path(self.temp.name) / "sibling"
        subprocess.run(
            ["git", "worktree", "add", "--detach", "-q", str(sibling), "HEAD"],
            cwd=self.repo,
            check=True,
        )
        other = run_journal.Journal(sibling, self.j.runs_root)
        with self.assertRaises(run_journal.JournalError):
            other.resume(r)

    def test_unborn_repository_is_supported(self):
        repo = Path(self.temp.name) / "unborn"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        j = run_journal.Journal(repo, Path(self.temp.name) / "unborn-state")
        r = j.start()
        self.assertEqual(j.identity["head"], "(unborn)")
        (repo / "new.txt").write_text("new")
        self.assertIn("dirtyDigest", j.resume(r)["drift"])

    def test_tampered_event_envelope_fails_closed(self):
        r = self.j.start()
        p = self.j._run(r) / "journal.jsonl"
        event = json.loads(p.read_text())
        event.pop("eventId")
        p.write_text(json.dumps(event) + "\n")
        with self.assertRaises(run_journal.JournalError):
            self.j.status(r)


if __name__ == "__main__":
    unittest.main()
