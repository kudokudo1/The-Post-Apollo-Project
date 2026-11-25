"""Fixed-public offline ordering tests; no OS operations."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from h14d_runtime_sequence import (
    Scope, Process, Limits, Plan, Launch, Terminal, check_sequence,
    ReaderRef, Observation, JoinedLaunch, IsolationRef, TerminalRef,
    ISOLATION_CHECKS, begin_join, finish_join,
)
from h14d_resource_witness import CAP, QUOTA, TASK_CAP, MAX_NS, Hold, GIB, Level, Sample, validate_prefix, evaluate


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
                             self.outer, 2_250_000_000, 2_300_000_000, 2_400_000_000)
        self.terminal = Terminal(self.process, self.outer, 0,
                                 3_000_000_000, 3_100_000_000,
                                 populated=0, tasks=0, disposed_ns=3_200_000_000)

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

    def test_numeric_coercion_refused(self):
        for key, val in (("memory", float(CAP)), ("swap", False),
                         ("quota", (float(QUOTA[0]), QUOTA[1])),
                         ("cpus", (2.0, 3)), ("tasks", float(TASK_CAP)),
                         ("quota", [QUOTA[0], QUOTA[1]]), ("cpus", (2, 3, 4))):
            with self.subTest(key=key, val=val), self.assertRaises(Hold):
                self.check(launch=replace(self.launch,
                                          limits=replace(self.launch.limits, **{key: val})))
        for scope in (replace(self.outer, mount_id=True),
                      replace(self.outer, device=2.0),
                      replace(self.outer, inode=4.0)):
            with self.subTest(scope=scope), self.assertRaises(Hold):
                self.check(launch=replace(self.launch, outer=scope))
            with self.subTest(scope=scope), self.assertRaises(Hold):
                self.check(terminal=replace(self.terminal, outer=scope))

    def test_first_active_observation_bound_to_pinned_outer(self):
        for launch in (replace(self.launch, first_active_scope=self.inner),
                       replace(self.launch, first_active_scope=replace(self.outer, inode=4.0)),
                       replace(self.launch, first_active_start_ns=self.launch.pinned_ns - 1),
                       replace(self.launch, first_active_start_ns=self.launch.first_active_ns)):
            with self.subTest(launch=launch), self.assertRaises(Hold):
                self.check(launch=launch)

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


class JoinedTests(unittest.TestCase):
    def setUp(self):
        parent = Scope(1, 1, 10)
        outer = Scope(1, 1, 11)
        inner = Scope(1, 1, 12)
        self.plan = Plan("boot-fixture", "sha256:" + "b"*64, parent, outer, (0, 1))
        process = Process(self.plan.boot, "a"*64, 50, 100)
        self.pr = ReaderRef(self.plan.boot, parent, "parent")
        self.orr = ReaderRef(self.plan.boot, outer, "outer")
        ancestor = Level((1, 10), GIB, "unlimited", "unlimited",
                         (None, 100000), ((0, 3),), 12, "unlimited", (0,)*6)
        child = Level((1, 11), 16*1024**2, CAP, "unlimited",
                      QUOTA, ((0, 1),), 2, TASK_CAP, (0,)*6)
        psi = ((0, 0, 0, 10), (0, 0, 0, 5))
        p = Sample(1, 100, (ancestor,), 12000, psi, None, None, None, None, None)
        f = Sample(300, 400, (ancestor, child), 12000, psi, 32*1024**2, 0, 0, 100, 1)
        b = replace(f, start_ns=110, end_ns=150,
                    levels=(ancestor, replace(child, tasks=0, current=4*1024**2)),
                    peak=8*1024**2, cpu_usec=10, populated=0)
        end = replace(f, start_ns=500, end_ns=600,
                      levels=(ancestor, replace(child, tasks=0)), cpu_usec=200, populated=0)
        self.parent = Observation(self.pr, p)
        self.baseline = Observation(self.orr, b)
        self.first = Observation(self.orr, f)
        self.final = Observation(self.orr, end)
        self.launch = JoinedLaunch(process, inner, self.plan.image_digest, 200, 250, 270,
                                   Limits(CAP, 0, QUOTA, (0, 1), TASK_CAP), 410)
        self.iso = IsolationRef(process, inner, 280, ISOLATION_CHECKS)
        self.terminal = TerminalRef(process, 0, 450, 610)

    def begin(self, **kw):
        args = dict(plan=self.plan, parent_reader=self.pr, outer_reader=self.orr,
                    parent=self.parent, baseline=self.baseline, first=self.first,
                    launch=self.launch, isolation=self.iso)
        args.update(kw)
        return begin_join(**args)

    def finish(self, prefix, **kw):
        args = dict(parent=self.parent, baseline=self.baseline,
                    observations=(self.first, self.final), terminal=self.terminal, isolation=self.iso)
        args.update(kw)
        return finish_join(prefix, **args)

    def test_shared_prefix_and_final_receive_exact_sample_objects(self):
        with patch("h14d_runtime_sequence.validate_prefix", wraps=validate_prefix) as pre, \
             patch("h14d_runtime_sequence.evaluate", wraps=evaluate) as final:
            prefix = self.begin()
            self.assertIs(pre.call_args.args[0], self.parent.sample)
            self.assertIs(pre.call_args.args[1], self.first.sample)
            self.assertIs(pre.call_args.kwargs["baseline"], self.baseline.sample)
            final.assert_not_called()
            result = self.finish(prefix)
            self.assertIs(final.call_args.args[0], self.parent.sample)
            self.assertIs(final.call_args.args[1][0], self.first.sample)
            self.assertIs(final.call_args.args[1][-1], self.final.sample)
            self.assertIs(final.call_args.kwargs["baseline"], self.baseline.sample)
        self.assertEqual(result.pop("status"), "JOINED_OFFLINE_REFERENCE")
        self.assertEqual(result.pop("safe_actions"), [])
        self.assertTrue(all(v is False for v in result.values()))

    def test_independently_pinned_reader_provenance_and_scope(self):
        for ref in (replace(self.orr), replace(self.orr, boot="other"),
                    replace(self.orr, scope=self.plan.parent), replace(self.orr, key="")):
            with self.subTest(ref=ref), self.assertRaises(Hold):
                self.begin(outer_reader=ref)
        with self.assertRaises(Hold):
            self.begin(plan=replace(self.plan, parent=Scope(1, 1, 99)),
                       parent_reader=replace(self.pr, scope=Scope(1, 1, 99)),
                       parent=Observation(replace(self.pr, scope=Scope(1, 1, 99)), self.parent.sample))
        other = replace(self.pr, scope=Scope(1, 1, 99))
        with self.assertRaisesRegex(Hold, "PARENT_IDENTITY_MISMATCH"):
            self.begin(plan=replace(self.plan, parent=other.scope),
                       parent_reader=other, parent=Observation(other, self.parent.sample))
        with self.assertRaises(Hold):
            self.finish(self.begin(), observations=(self.first, replace(self.final, reader=replace(self.orr))))

    def test_invalid_prefix_holds_before_simulated_progression(self):
        for key, obs, changes in (
                ("baseline", self.baseline, dict(populated=1)),
                ("first", self.first, dict(swap=1)),
                ("first", self.first, dict(populated=0)),
                ("first", self.first, dict(host_available_mib=4096)),
                ("first", self.first, dict(end_ns=1_000_000_201))):
            with self.subTest(key=key, changes=changes), self.assertRaises(Hold):
                self.begin(**{key: replace(obs, sample=replace(obs.sample, **changes))})
        for launch in (replace(self.launch, pinned_ns=301, limits_ns=302),
                       replace(self.launch, release_ns=399),
                       replace(self.launch, release_ns=1_000_000_201)):
            with self.subTest(launch=launch), self.assertRaises(Hold):
                self.begin(launch=launch)

    def test_independent_inner_and_isolation_reference(self):
        for isolation in (None, replace(self.iso, checks=ISOLATION_CHECKS[:-1]),
                          replace(self.iso, observed_ns=411),
                          replace(self.iso, inner=self.plan.outer),
                          replace(self.iso, process=replace(self.iso.process, pid=51))):
            with self.subTest(isolation=isolation), self.assertRaises(Hold):
                self.begin(isolation=isolation)
        with self.assertRaises(Hold):
            self.begin(launch=replace(self.launch, limits=replace(self.launch.limits, swap=False)))

    def test_final_revalidates_isolation_reference(self):
        prefix = self.begin()
        for bad in (None, replace(self.iso, checks=ISOLATION_CHECKS[:-1]),
                    replace(self.iso, observed_ns=411),
                    replace(self.iso, observed_ns=False),
                    replace(self.iso, inner=self.plan.outer),
                    replace(self.iso, process=replace(self.iso.process, pid=51))):
            with self.subTest(bad=bad), self.assertRaisesRegex(Hold, "ISOLATION_REFERENCE_MISMATCH"):
                self.finish(replace(prefix, isolation=bad), isolation=bad)

    def test_final_refuses_replaced_even_valid_isolation_reference(self):
        prefix = self.begin()
        for replacement in (replace(self.iso), replace(self.iso, observed_ns=281)):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(
                    Hold, "ISOLATION_REFERENCE_REPLACED"):
                self.finish(replace(prefix, isolation=replacement))
            with self.subTest(replacement=replacement), self.assertRaisesRegex(
                    Hold, "ISOLATION_REFERENCE_REPLACED"):
                self.finish(prefix, isolation=replacement)
        with self.assertRaisesRegex(Hold, "ISOLATION_REFERENCE_REPLACED"):
            self.finish(prefix, isolation=None)

    def test_equal_value_prefix_replacement_refused(self):
        prefix = self.begin()
        for key, obs in (("parent", self.parent), ("baseline", self.baseline)):
            with self.subTest(key=key), self.assertRaisesRegex(Hold, "PREFIX_REPLACED"):
                self.finish(prefix, **{key: replace(obs, sample=replace(obs.sample))})
        with self.assertRaisesRegex(Hold, "PREFIX_REPLACED"):
            self.finish(prefix, observations=(replace(self.first, sample=replace(self.first.sample)), self.final))

    def test_original_terminal_before_final_start_and_disposal(self):
        prefix = self.begin()
        for terminal in (None, replace(self.terminal, process=replace(self.terminal.process, start_ticks=101)),
                         replace(self.terminal, observed_ns=500),
                         replace(self.terminal, observed_ns=550),
                         replace(self.terminal, disposed_ns=599)):
            with self.subTest(terminal=terminal), self.assertRaises(Hold):
                self.finish(prefix, terminal=terminal)
        for sample in (replace(self.final.sample, populated=1),
                       replace(self.final.sample, levels=self.first.sample.levels)):
            with self.subTest(sample=sample), self.assertRaises(Hold):
                self.finish(prefix, observations=(self.first, replace(self.final, sample=sample)))


if __name__ == "__main__":
    unittest.main()
