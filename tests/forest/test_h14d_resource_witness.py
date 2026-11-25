"""Offline H14-D Heart resource tests; no Docker/kernel/host calls."""
from dataclasses import replace
import unittest
from h14d_resource_witness import (
    CAP, GIB, QUOTA, Hold, Level, Sample, evaluate, preflight,
)


class ResourceWitnessTests(unittest.TestCase):
    def setUp(self):
        self.ancestor = Level((1, 10), GIB, "unlimited", "unlimited",
                              (None, 100000), ((0, 3),), 12,
                              "unlimited", (0,) * 6)
        self.child = Level((1, 11), 16*1024**2, CAP, "unlimited",
                           QUOTA, ((0, 1),), 2, 128, (0,) * 6)
        self.psi = ((0, 0, 0, 10), (0, 0, 0, 5))
        self.parent = Sample(1, 100, (self.ancestor,), 12000,
                             self.psi, None, None, None, None, None)
        self.active = Sample(300, 400, (self.ancestor, self.child),
                             12000, self.psi, 32*1024**2, 0, 0, 100, 1)
        self.final = replace(self.active, start_ns=500, end_ns=600,
                             levels=(self.ancestor, replace(self.child, tasks=0)),
                             cpu_usec=200, populated=0)

    def check(self, parent=None, samples=None, selected=(0, 1), launch_ns=200):
        return evaluate(self.parent if parent is None else parent,
                        (self.active, self.final) if samples is None else samples,
                        selected=selected, launch_ns=launch_ns)

    def changed(self, **fields):
        return replace(self.active, levels=(self.ancestor, replace(self.child, **fields)))

    def test_exact_reference_no_authority(self):
        r = self.check()
        self.assertEqual(r["status"], "RESOURCE_ENVELOPE_OBSERVED")
        self.assertEqual(r["samples"], 2)
        self.assertEqual(r["kernel_peak_reported_bytes"], 32*1024**2)
        self.assertEqual(r["cpu_usage_usec_observed_delta"], 100)
        self.assertEqual(r["safe_actions"], [])
        for k in ("terminal_verified", "device_isolation_verified",
                  "measurement_coverage_complete", "resource_requirements_established",
                  "resource_reserved", "safe_to_start_inference", "permission_granted",
                  "production_authority"):
            self.assertIs(r[k], False)

    def test_parent_headroom_age_and_cpu(self):
        for bad in (
            replace(self.parent, host_available_mib=10239),
            replace(self.parent, levels=(replace(self.ancestor, hard=10*GIB),)),
            replace(self.parent, levels=(replace(self.ancestor, high=10*GIB),)),
            replace(self.parent, levels=(replace(self.ancestor, quota=(199999, 100000)),)),
            replace(self.parent, levels=(replace(self.ancestor, pids_max=139),)),
            replace(self.parent, levels=(replace(self.ancestor, cpus=((0, 2),)),)),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(parent=bad)
        with self.assertRaises(Hold):
            preflight(self.parent, selected=(0, 1), now_ns=1_000_000_101)
        for bad in ((0, 0), (False, 1), (0, 4), (1, 0)):
            with self.subTest(selected=bad), self.assertRaises(Hold):
                self.check(selected=bad)

    def test_child_limits_and_accounting(self):
        for bad in (
            self.changed(hard=CAP+1), self.changed(quota=(200001, 100000)),
            self.changed(cpus=((0, 2),)), self.changed(pids_max=129),
            self.changed(high=CAP-1), self.changed(events=(0, 0, 1, 0, 0, 0)),
            replace(self.active, swap=1), replace(self.active, swap_max=1),
            replace(self.active, peak=CAP+1), replace(self.active, peak=0),
            replace(self.active, host_available_mib=4096),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(samples=(bad, self.final))

    def test_identity_and_ancestor_changes(self):
        for bad in (
            replace(self.final, levels=(self.ancestor, replace(self.child, identity=(1, 12), tasks=0))),
            replace(self.final, levels=(replace(self.ancestor, identity=(1, 20)), self.final.levels[-1])),
            replace(self.final, levels=(replace(self.ancestor, hard=20*GIB), self.final.levels[-1])),
            replace(self.final, levels=(replace(self.ancestor, events=(0, 1, 0, 0, 0, 0)), self.final.levels[-1])),
            replace(self.final, levels=(self.final.levels[-1],)),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(samples=(self.active, bad))

    def test_stall_gap_and_counter_regression(self):
        for bad in (
            replace(self.final, host_pressure=((0, 0, 0, 11), self.psi[1])),
            replace(self.final, host_pressure=((1, 0, 0, 10), self.psi[1])),
            replace(self.final, start_ns=1_000_000_401, end_ns=1_000_000_500),
            replace(self.final, start_ns=399),
            replace(self.final, cpu_usec=99),
            replace(self.final, peak=self.active.peak-1),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(samples=(self.active, bad))

    def test_quiescence_required_not_terminal_authority(self):
        for bad in (
            replace(self.final, populated=1),
            replace(self.final, levels=(self.ancestor, self.child)),
            replace(self.final, populated=None),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(samples=(self.active, bad))
        with self.assertRaises(Hold):
            self.check(samples=(self.active,))
        self.assertFalse(self.check()["terminal_verified"])

    def test_invalid_types_do_not_coerce(self):
        for bad in (
            replace(self.active, swap=False),
            replace(self.active, levels=(self.ancestor, replace(self.child, tasks=True))),
            replace(self.active, host_available_mib=True),
            replace(self.active, levels=(self.ancestor, replace(self.child, cpus=((0, 0), (1, 1))))),
        ):
            with self.subTest(bad=bad), self.assertRaises(Hold):
                self.check(samples=(bad, self.final))


if __name__ == "__main__":
    unittest.main(verbosity=2)
