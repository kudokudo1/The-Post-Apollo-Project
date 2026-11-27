#!/usr/bin/env python3
"""Pure synthetic readback checks. Never create cgroups or start models."""
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_local_limit_readback_p0 as H
import cgroup_observation_i5 as I5


def level(memory=1024,swap=0,used=100,quota=100000,period=100000,pids=32,active=1):
    return H.Level(memory,swap,used,quota,period,pids,active)


class HeartLocalReadbackTests(unittest.TestCase):
    def test_finite_limit_hierarchy_is_observation_only(self):
        first=(level(memory=4096,used=100,quota=200000,pids=64),level())
        second=(level(memory=4096,used=110,quota=200000,pids=64),
                level(used=180,active=3))
        result=H._summary(first,second)
        self.assertEqual(result["leaf_memory_limit_bytes"],1024)
        self.assertEqual(result["leaf_swap_limit_bytes"],0)
        self.assertEqual(result["visible_cpu_quota_millicpu_floor"],1000)
        self.assertEqual(result["leaf_memory_used_bytes_sampled_max"],180)
        self.assertFalse(H._base()["safe_to_start_inference"])
        self.assertFalse(H._base()["permission_granted"])

    def test_refuse_unbounded_or_positive_swap_leaf(self):
        for candidate in [level(memory="unlimited"),level(swap=1024),
                          level(swap="unlimited"),level(quota=None),
                          level(pids="unlimited"),level(memory=0)]:
            with self.subTest(candidate=candidate), self.assertRaisesRegex(
                    I5.CgroupRefusal,"LEAF_NOT_FINITE_SWAP_FREE"):
                H._summary((candidate,),(candidate,))

    def test_refuse_limit_change_or_accounting_inconsistency(self):
        with self.assertRaisesRegex(I5.CgroupRefusal,"LIMITS_CHANGED"):
            H._summary((level(),),(level(memory=2048),))
        for candidate in [level(used=2048),level(active=40)]:
            with self.assertRaisesRegex(I5.CgroupRefusal,"LIMIT_COUNTER_INCONSISTENT"):
                H._summary((candidate,),(candidate,))
        with self.assertRaisesRegex(I5.CgroupRefusal,"INCOMPLETE_LIMIT_HIERARCHY"):
            H._summary((),())

    def test_only_fixed_readonly_kernel_counter_names(self):
        for name in ["cgroup.procs","memory.max/../../etc/shadow","cpu.stat", "../x"]:
            with self.assertRaisesRegex(I5.CgroupRefusal,"INVALID_LIMIT_COUNTER"):
                H._read(-1,name)

    def test_refusal_does_not_claim_any_host_permission(self):
        with patch.object(H,"observe",side_effect=I5.CgroupRefusal("LEAF_NOT_FINITE_SWAP_FREE")):
            out=StringIO()
            with redirect_stdout(out):
                self.assertEqual(H.main(["observe","--cgroup","/forest.test"]),2)
            output=out.getvalue()
            self.assertIn('"safe_to_start_inference":false',output)
            self.assertIn('"permission_granted":false',output)

if __name__=="__main__":
    unittest.main()
