#!/usr/bin/env python3
from __future__ import annotations

import unittest

import plan_fleet


class PlanFleetTests(unittest.TestCase):
    def test_broad_read_wave_uses_six_independent_slots(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad", runtime_child_cap=8, ready_reads=9, ready_writers=0
        )
        self.assertEqual((plan.active_children, plan.read_slots), (6, 6))
        self.assertEqual(plan.deferred_reads, 3)

    def test_live_runtime_cap_wins(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad", runtime_child_cap=4, ready_reads=9, ready_writers=0
        )
        self.assertEqual(plan.active_children, 4)

    def test_standard_mode_stays_at_three(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="standard", runtime_child_cap=6, ready_reads=8, ready_writers=0
        )
        self.assertEqual(plan.active_children, 3)

    def test_qualified_team_read_wave_can_use_eight(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="team",
            runtime_child_cap=8,
            ready_reads=9,
            ready_writers=0,
            team_qualified=True,
            routes_attested=True,
            lanes_independent=True,
            paired_comparison=True,
        )
        self.assertEqual((plan.active_children, plan.read_slots), (8, 8))
        self.assertEqual(plan.deferred_reads, 1)

    def test_team_mode_fails_closed_without_qualification(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit qualification"):
            plan_fleet.plan_fleet(
                mode="team", runtime_child_cap=8, ready_reads=8, ready_writers=0
            )

    def test_team_mode_rejects_writers_and_small_shards(self) -> None:
        with self.assertRaisesRegex(ValueError, "read-only"):
            plan_fleet.plan_fleet(
                mode="team",
                runtime_child_cap=8,
                ready_reads=7,
                ready_writers=1,
                team_qualified=True,
                routes_attested=True,
                lanes_independent=True,
                paired_comparison=True,
            )
        with self.assertRaisesRegex(ValueError, "at least seven"):
            plan_fleet.plan_fleet(
                mode="team",
                runtime_child_cap=8,
                ready_reads=6,
                ready_writers=0,
                team_qualified=True,
                routes_attested=True,
                lanes_independent=True,
                paired_comparison=True,
            )

    def test_team_mode_requires_each_admission_attestation(self) -> None:
        base = {
            "mode": "team",
            "runtime_child_cap": 8,
            "ready_reads": 8,
            "ready_writers": 0,
            "team_qualified": True,
            "routes_attested": True,
            "lanes_independent": True,
            "paired_comparison": True,
        }
        for key, message in (
            ("routes_attested", "route attestation"),
            ("lanes_independent", "decision-bearing lanes"),
            ("paired_comparison", "paired outcome comparison"),
        ):
            kwargs = {**base, key: False}
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, message):
                    plan_fleet.plan_fleet(**kwargs)

    def test_team_mode_rejects_pressure_failures_and_insufficient_capacity(
        self,
    ) -> None:
        base = {
            "mode": "team",
            "runtime_child_cap": 8,
            "ready_reads": 8,
            "ready_writers": 0,
            "team_qualified": True,
            "routes_attested": True,
            "lanes_independent": True,
            "paired_comparison": True,
        }
        with self.assertRaisesRegex(ValueError, "resource pressure"):
            plan_fleet.plan_fleet(**base, resource_pressure=True)
        with self.assertRaisesRegex(ValueError, "below 20%"):
            plan_fleet.plan_fleet(**base, previous_failure_rate=0.20)
        with self.assertRaisesRegex(ValueError, "live capacity"):
            plan_fleet.plan_fleet(**{**base, "runtime_child_cap": 6})

    def test_shared_writer_is_serialized_with_two_readers(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad", runtime_child_cap=6, ready_reads=8, ready_writers=3
        )
        self.assertEqual(
            (plan.writer_slots, plan.read_slots, plan.active_children), (1, 2, 3)
        )
        self.assertEqual(plan.deferred_writers, 2)

    def test_isolated_writers_allow_two_plus_two_readers(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad",
            runtime_child_cap=6,
            ready_reads=8,
            ready_writers=3,
            writers_isolated=True,
        )
        self.assertEqual(
            (plan.writer_slots, plan.read_slots, plan.active_children), (2, 2, 4)
        )

    def test_pressure_and_failure_rate_shrink_waves(self) -> None:
        pressure = plan_fleet.plan_fleet(
            mode="broad",
            runtime_child_cap=6,
            ready_reads=8,
            ready_writers=0,
            resource_pressure=True,
        )
        failures = plan_fleet.plan_fleet(
            mode="broad",
            runtime_child_cap=6,
            ready_reads=8,
            ready_writers=0,
            previous_failure_rate=0.20,
        )
        self.assertEqual(pressure.active_children, 2)
        self.assertEqual(failures.active_children, 3)

    def test_rejects_invalid_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            plan_fleet.plan_fleet(
                mode="broad", runtime_child_cap=-1, ready_reads=1, ready_writers=0
            )
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            plan_fleet.plan_fleet(
                mode="broad",
                runtime_child_cap=1,
                ready_reads=1,
                ready_writers=0,
                previous_failure_rate=1.5,
            )

    def test_invalidate_gates_supports_exact_glob_and_global_scopes(self) -> None:
        result = plan_fleet.invalidate_gates(
            ["src/app.py", "docs/readme.md"],
            {
                "exact": ["src/app.py"],
                "glob": ["docs/*.md"],
                "all": ["global"],
                "unknown": ["unknown"],
                "safe": ["tests/*"],
            },
        )
        self.assertEqual(result, ("all", "exact", "glob", "safe", "unknown"))
        self.assertEqual(
            plan_fleet.invalidate_gates([], {"all": ["global"], "safe": ["tests/*"]}),
            (),
        )

    def test_resume_is_byte_stable_and_requeues_invalidated_gates(self) -> None:
        stages = [
            {"id": "format", "kind": "read"},
            {"id": "test", "kind": "read", "deps": ["format"]},
            {"id": "build", "kind": "write", "deps": ["format"], "scope": "dist"},
        ]
        truth = {"format": True, "test": True, "build": True}
        first = plan_fleet.resume_plan(
            stages, truth, ["src/x.py"], {"test": ["src/*.py"]}
        )
        second = plan_fleet.resume_plan(
            list(reversed(stages)), truth, ["src/x.py"], {"test": ["src/*.py"]}
        )
        self.assertEqual(first, second)
        self.assertEqual(first["ready"], ("test",))
        self.assertEqual((first["ready_reads"], first["ready_writers"]), (1, 0))

    def test_resume_blocks_failed_dependencies_and_rejects_bad_graphs_and_writers(
        self,
    ) -> None:
        blocked = plan_fleet.resume_plan(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}], {"a": {"status": "failed"}}
        )
        self.assertEqual(blocked["ready"], ())
        self.assertEqual(blocked["blocked"], ("a", "b"))
        with self.assertRaisesRegex(ValueError, "missing dependency"):
            plan_fleet.resume_plan([{"id": "a", "deps": ["none"]}], {})
        with self.assertRaisesRegex(ValueError, "cycle"):
            plan_fleet.resume_plan(
                [{"id": "a", "deps": ["b"]}, {"id": "b", "deps": ["a"]}], {}
            )
        with self.assertRaisesRegex(ValueError, "overlapping"):
            plan_fleet.resume_plan(
                [
                    {"id": "a", "kind": "write", "scope": "src/*"},
                    {"id": "b", "kind": "write", "scope": "src/x.py"},
                ],
                {},
            )
        with self.assertRaisesRegex(ValueError, "path scopes"):
            plan_fleet.resume_plan(
                [{"id": "a", "kind": "write", "writer_scopes": []}], {}
            )
        self.assertEqual(
            plan_fleet.resume_plan([{"id": "a", "required_gates": ["missing"]}], {})[
                "deferred"
            ],
            ("a",),
        )


if __name__ == "__main__":
    unittest.main()
