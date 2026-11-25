"""Fixed-public offline ordering tests; no OS operations."""
from dataclasses import replace
import unittest

from h14d_runtime_sequence import (
    Scope, Process, Limits, Plan, Launch, Terminal, check_sequence,
)
from h14d_resource_witness import CAP, QUOTA, TASK_CAP, MAX_NS, Hold


class SequenceTest(unittest.TestCase):
    def setUp(self):
        self.parent = Scope(1, 2, 3)
        self.outer = Scope(1, 2, 4)
        self.inner = Scope(1, 2, 5)
        self.process = Process("fixture-boot", "a" * 64, 50, 100)
        self.plan = Plan("fixture-boot", "sha256:" + "b" * 64,
                         self.parent, self.outer, (2, 3))
        self.launch = Launch(self.process, self.inner, self.outer,
                             self.plan.image_digest, 2_000_000_000,
                             2_100_000_000, 2_200_000_000,
                             Limits(CAP, 0, QUOTA, (2, 3), TASK_CAP),
                             2_300_000_000, 2_400_000_000)
        self.terminal = Terminal(self.process, self.outer, 0,
                                 3_000_000_000, 3_100_000_000, 3_200_000_000)

    def check(self, **overrides):
        kw = dict(plan=self.plan, parent_preflight_end_ns=1_900_000_000,
                  outer_baseline_end_ns=1_950_000_000, launch=self.launch,
                  terminal=self.terminal)
        kw.update(overrides)
        return check_sequence(**kw)

    def test_reference_never_grants_authority(self):
        result = self.check()
        self.assertEqual(result.pop("status"), "OFFLINE_SEQUENCE_REFERENCE")
        self.assertEqual(result.pop("safe_actions"), [])
        self.assertTrue(all(v is False for v in result.values()))

    def test_preselected_outer_and_mount(self):
        for outer in (self.parent, Scope(9, 2, 4), Scope(1, 8, 4)):
            with self.subTest(outer=outer), self.assertRaises(Hold):
                self.check(plan=replace(self.plan, outer=outer))

    def test_replaced_outer_inner_and_image(self):
        for launch in (replace(self.launch, outer=Scope(1, 2, 8)),
                       replace(self.launch, inner=self.outer),
                       replace(self.launch, image_digest="sha256:" + "c" * 64)):
            with self.subTest(launch=launch), self.assertRaises(Hold):
                self.check(launch=launch)

    def test_preflight_baseline_stale_or_future(self):
        for key in ("parent_preflight_end_ns", "outer_baseline_end_ns"):
            for value in (0, self.launch.launch_ns + 1):
                with self.subTest(key=key, value=value), self.assertRaises(Hold):
                    self.check(**{key: value})

    def test_release_requires_identity_limits_and_first_observation(self):
        for launch in (replace(self.launch, release_ns=self.launch.pinned_ns - 1),
                       replace(self.launch, release_ns=self.launch.limits_ns - 1),
                       replace(self.launch, first_active_ns=self.launch.release_ns + 1),
                       replace(self.launch, first_active_ns=self.launch.launch_ns + 1_000_000_001,
                               release_ns=self.launch.launch_ns + 1_000_000_001)):
            with self.subTest(launch=launch), self.assertRaises(Hold):
                self.check(launch=launch)

    def test_each_inner_limit_is_exact(self):
        for key, val in (("memory", CAP + 1), ("swap", 1),
                         ("quota", (100000, 100000)), ("cpus", (1, 2)),
                         ("tasks", TASK_CAP + 1)):
            with self.subTest(key=key), self.assertRaises(Hold):
                self.check(launch=replace(self.launch,
                                          limits=replace(self.launch.limits, **{key: val})))

    def test_terminal_replacement_not_original(self):
        for key, val in (("pid", 51), ("start_ticks", 101),
                         ("boot", "different"), ("container", "c" * 64)):
            with self.subTest(key=key), self.assertRaises(Hold):
                self.check(terminal=replace(self.terminal,
                                           process=replace(self.process, **{key: val})))

    def test_empty_is_not_enough(self):
        for terminal in (None, replace(self.terminal, exit_status=1),
                         replace(self.terminal, outer=Scope(1, 2, 8)),
                         replace(self.terminal, populated=1),
                         replace(self.terminal, tasks=1)):
            with self.subTest(terminal=terminal), self.assertRaises(Hold):
                self.check(terminal=terminal)

    def test_final_before_disposal_after_terminal_bounded(self):
        for terminal in (replace(self.terminal, final_ns=self.terminal.observed_ns - 1),
                         replace(self.terminal, disposed_ns=self.terminal.final_ns - 1),
                         replace(self.terminal, final_ns=self.launch.launch_ns + MAX_NS + 1,
                                 disposed_ns=self.launch.launch_ns + MAX_NS + 1)):
            with self.subTest(terminal=terminal), self.assertRaises(Hold):
                self.check(terminal=terminal)


if __name__ == "__main__":
    unittest.main()
