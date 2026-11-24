import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_cpu_constraints_h4 as H


class CpuTests(unittest.TestCase):
    def test_fractional_parent_limit(self):
        sample = (((150000, 100000), (300000, 100000)), ((0, 7),))
        result = H._summary(sample, sample)
        self.assertEqual(result["visible_cpu_time_ceiling_millicpu_floor"], 1500)
        self.assertEqual(result["effective_cpuset_cpu_count"], 8)

    def test_cpuset_bottleneck_and_unlimited(self):
        for quotas in (((None, 100000),), ((800000, 100000),)):
            sample = (quotas, ((1, 2),))
            result = H._summary(sample, sample)
            self.assertEqual(result["visible_cpu_time_ceiling_millicpu_floor"], 2000)
            self.assertEqual(result["finite_quota_levels"], int(quotas[0][0] is not None))

    def test_round_down(self):
        sample = (((1, 3),), ((0, 1),))
        self.assertEqual(H._summary(sample, sample)["visible_quota_millicpu_floor"], 333)

    def test_quota_parser(self):
        self.assertEqual(H._quota(b"max 100000\n"), (None, 100000))
        self.assertEqual(H._quota(b"50000 100000\n"), (50000, 100000))
        for raw in (b"", b"0 100000", b"max 0", b"1 1000001", b"-1 100000",
                    b"max max", b"1 2 3", b"1.0 100000"):
            with self.assertRaises(H.I5.CgroupRefusal):
                H._quota(raw)

    def test_cpuset_parser(self):
        self.assertEqual(H._cpuset(b"0-3,4,7-8\n"), ((0, 4), (7, 8)))
        for raw in (b"", b"2-1", b"0-3,3", b"2,1", b"0,,1", b"1-",
                    b"0-65536", b"1048576", b"1, 2"):
            with self.assertRaises(H.I5.CgroupRefusal):
                H._cpuset(raw)

    def test_same_count_changed_mask_refused(self):
        first = (((None, 100000),), ((0, 1),))
        for second in ((((None, 100000),), ((2, 3),)),
                       (((200000, 100000),), ((0, 1),))):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "CPU_CONSTRAINT_CHANGED"):
                H._summary(first, second)

    def test_real_fixture_reads_and_missing_counter(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            parent, child = p/"parent", p/"parent"/"child"
            child.mkdir(parents=True)
            (parent/"cpu.max").write_text("150000 100000\n")
            (child/"cpu.max").write_text("max 100000\n")
            (child/"cpuset.cpus.effective").write_text("0-3\n")
            def open_group(parts):
                return os.open(p.joinpath(*parts), os.O_RDONLY | os.O_DIRECTORY)
            with patch.object(H.I5, "_open_group", side_effect=open_group), \
                 patch.object(H.I5, "_mount", return_value=("mount", "device")):
                result = H.observe("/parent/child")
                self.assertEqual(result["visible_cpu_time_ceiling_millicpu_floor"], 1500)
                self.assertEqual(result["effective_cpuset_cpu_count"], 4)
                for key in ("runtime_identity_verified", "idle_cpu_capacity_established",
                            "runtime_thread_limit_enforced", "resource_reserved",
                            "safe_to_start_inference", "permission_granted", "production_authority"):
                    self.assertIs(result[key], False)
                self.assertNotIn(root, str(result))
                self.assertNotIn("/parent", str(result))
                (parent/"cpu.max").unlink()
                with self.assertRaisesRegex(H.I5.CgroupRefusal, "CPU_OBSERVATION_UNAVAILABLE"):
                    H.observe("/parent/child")

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p/"target").write_text("max 100000")
            (p/"cpu.max").symlink_to(p/"target")
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(OSError):
                    H._read(fd, "cpu.max", 64)
            finally:
                os.close(fd)

    def test_scope_and_time_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p/"cpu.max").write_text("max 100000")
            (p/"cpuset.cpus.effective").write_text("0-1")
            with patch.object(H.I5, "_open_group", side_effect=lambda _: os.open(root, os.O_RDONLY|os.O_DIRECTORY)):
                with patch.object(H.I5, "_mount", side_effect=[("a","b"),("c","d")]):
                    with self.assertRaisesRegex(H.I5.CgroupRefusal, "CGROUP_SCOPE_CHANGED"):
                        H.observe("/fixture")
                with patch.object(H.I5, "_mount", return_value=("a","b")), \
                     patch.object(H.time, "monotonic_ns", side_effect=[0, H.MAX_WINDOW_NS+1]):
                    with self.assertRaisesRegex(H.I5.CgroupRefusal, "OBSERVATION_WINDOW_EXCEEDED"):
                        H.observe("/fixture")

    def test_native_self_group_if_supported(self):
        if sys.platform != "linux":
            self.skipTest("Linux required")
        path = next((line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines()
                     if line.startswith("0::")), None)
        if not path or path == "/":
            self.skipTest("No explicit non-root group")
        try:
            result = H.observe(path)
        except H.I5.CgroupRefusal as exc:
            self.skipTest("Native CPU hierarchy unavailable: " + str(exc))
        self.assertGreater(result["effective_cpuset_cpu_count"], 0)
        self.assertFalse(result["safe_to_start_inference"])
