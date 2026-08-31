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

    def test_shared_writer_is_serialized_with_two_readers(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad", runtime_child_cap=6, ready_reads=8, ready_writers=3
        )
        self.assertEqual((plan.writer_slots, plan.read_slots, plan.active_children), (1, 2, 3))
        self.assertEqual(plan.deferred_writers, 2)

    def test_isolated_writers_allow_two_plus_two_readers(self) -> None:
        plan = plan_fleet.plan_fleet(
            mode="broad",
            runtime_child_cap=6,
            ready_reads=8,
            ready_writers=3,
            writers_isolated=True,
        )
        self.assertEqual((plan.writer_slots, plan.read_slots, plan.active_children), (2, 2, 4))

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


if __name__ == "__main__":
    unittest.main()
