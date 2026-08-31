from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import cache_gates


class CacheGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True
        )
        (self.repo / "package.json").write_text('{"name":"test"}')
        (self.repo / "tracked.txt").write_text("one")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-qm", "initial"], check=True
        )
        self.cache = cache_gates.GateCache(self.repo, Path(self.temp.name) / "state")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def key(self, argv=("python", "-m", "pytest"), cwd=None, env=None) -> str:
        return cache_gates.command_truth_key(
            argv,
            cwd or self.repo,
            env or {"CI": "1"},
            repo=self.repo,
            allowed_env=("CI",),
        )

    def entry(self):
        digest = "a" * 64
        environment_digest = hashlib.sha256(b"1").hexdigest()
        return {
            "schema_version": cache_gates.SCHEMA_VERSION,
            "key": self.key(),
            "command": {
                "argv": ["python", "-m", "pytest"],
                "cwd": ".",
                "scope_paths": [],
                "allowlisted_env": {"CI": environment_digest},
                "repository_fingerprint": cache_gates.repository_fingerprint(self.repo),
            },
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": 0,
            "status": "passed",
            "timed_out": False,
            "complete": True,
            "stdout": {"sha256": digest, "truncated": False},
            "stderr": {"sha256": digest, "truncated": False},
        }

    def test_fingerprint_tracks_head_staged_unstaged_untracked_and_truth_files(
        self,
    ) -> None:
        base = cache_gates.repository_fingerprint(self.repo)
        (self.repo / "tracked.txt").write_text("two")
        self.assertNotEqual(base, cache_gates.repository_fingerprint(self.repo))
        subprocess.run(["git", "-C", str(self.repo), "add", "tracked.txt"], check=True)
        staged = cache_gates.repository_fingerprint(self.repo)
        (self.repo / "new.txt").write_text("new")
        self.assertNotEqual(staged, cache_gates.repository_fingerprint(self.repo))
        (self.repo / "package.json").write_text('{"name":"changed"}')
        self.assertNotEqual(staged, cache_gates.repository_fingerprint(self.repo))

    def test_command_key_tracks_argv_scope_and_allowed_environment(self) -> None:
        (self.repo / "sub").mkdir()
        base = self.key()
        self.assertNotEqual(base, self.key(("python", "other")))
        self.assertNotEqual(base, self.key(cwd=self.repo / "sub"))
        self.assertNotEqual(base, self.key(env={"CI": "2"}))
        self.assertEqual(
            base,
            cache_gates.command_truth_key(
                ["python", "-m", "pytest"],
                self.repo,
                {"CI": "1", "NOISE": "x"},
                repo=self.repo,
                allowed_env=("CI",),
            ),
        )
        self.assertEqual(
            cache_gates.command_truth_key(
                ["python", "-m", "pytest"],
                self.repo,
                {"CI": "1"},
                repo=self.repo,
                allowed_env=("CI",),
                scope_paths=("sub",),
            ),
            cache_gates.command_truth_key(
                ["python", "-m", "pytest"],
                self.repo,
                {"CI": "1"},
                repo=self.repo,
                allowed_env=("CI",),
                scope_paths=(self.repo / "sub",),
            ),
        )

    def test_cache_only_reuses_complete_success_and_rejects_corruption(self) -> None:
        key = self.key()
        self.cache.put(key, self.entry())
        self.assertIsNotNone(self.cache.get(key))
        for update in (
            {"exit_code": 1},
            {"status": "timeout"},
            {"timed_out": True},
            {"complete": False},
        ):
            self.cache.put(key, {**self.entry(), **update})
            self.assertIsNone(self.cache.get(key))
        self.cache._entry_path(key).write_text("not json")
        self.assertIsNone(self.cache.get(key))
        self.cache.put(
            key, {**self.entry(), "stdout": {"sha256": "a" * 64, "truncated": True}}
        )
        self.assertIsNone(self.cache.get(key))

    def test_cache_rejects_key_command_mismatch_and_reversed_timestamps(self) -> None:
        entry = self.entry()
        entry["command"] = {**entry["command"], "argv": ["python", "other"]}
        with self.assertRaisesRegex(ValueError, "malformed"):
            self.cache.put(self.key(), entry)
        entry = self.entry()
        entry["started_at"] = "2026-08-31T12:00:01+00:00"
        entry["ended_at"] = "2026-08-31T12:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "malformed"):
            self.cache.put(self.key(), entry)

    def test_unborn_repository_has_a_stable_content_fingerprint(self) -> None:
        repo = Path(self.temp.name) / "unborn"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        base = cache_gates.repository_fingerprint(repo)
        (repo / "new.txt").write_text("new")
        self.assertNotEqual(base, cache_gates.repository_fingerprint(repo))

    def test_cache_is_outside_checkout_and_records_are_private(self) -> None:
        self.assertNotEqual(self.cache.directory.parent.resolve(), self.repo.resolve())
        self.assertEqual(self.cache.directory.stat().st_mode & 0o777, 0o700)
        key = self.key()
        self.cache.put(key, self.entry())
        self.assertEqual(self.cache._entry_path(key).stat().st_mode & 0o777, 0o600)
        in_repo = self.repo / ".cache" / "gate-state"
        with self.assertRaisesRegex(ValueError, "outside checkout"):
            cache_gates.GateCache(self.repo, in_repo)
        self.assertFalse((self.repo / ".cache").exists())

    def test_sibling_worktree_identity_differs_when_content_differs(self) -> None:
        other = Path(self.temp.name) / "other"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "worktree",
                "add",
                "-q",
                "-b",
                "other",
                str(other),
            ],
            check=True,
        )
        (other / "tracked.txt").write_text("worktree change")
        self.assertNotEqual(
            cache_gates.repository_fingerprint(self.repo),
            cache_gates.repository_fingerprint(other),
        )

    def test_clean_sibling_worktrees_share_namespace_and_symlinked_state_is_rejected(
        self,
    ) -> None:
        other = Path(self.temp.name) / "other"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "worktree",
                "add",
                "-q",
                "-b",
                "clean-other",
                str(other),
            ],
            check=True,
        )
        self.assertEqual(
            self.cache.directory,
            cache_gates.GateCache(other, Path(self.temp.name) / "state").directory,
        )
        link = Path(self.temp.name) / "link-state"
        link.symlink_to(Path(self.temp.name) / "state")
        with self.assertRaisesRegex(ValueError, "symlink"):
            cache_gates.GateCache(self.repo, link)
        parent = Path(self.temp.name) / "state-parent"
        parent.mkdir()
        intermediate = Path(self.temp.name) / "intermediate"
        intermediate.symlink_to(parent)
        with self.assertRaisesRegex(ValueError, "symlink"):
            cache_gates.GateCache(self.repo, intermediate / "nested")


if __name__ == "__main__":
    unittest.main()
