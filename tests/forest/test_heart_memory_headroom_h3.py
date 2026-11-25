import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_memory_headroom_h3 as H

M = 1024 * 1024


class HeadroomTests(unittest.TestCase):
    def test_parent_bottleneck(self):
        first = (H.Level(800*M, 1000*M, "unlimited"),
                 H.Level(100*M, 900*M, "unlimited"))
        second = (H.Level(850*M, 1000*M, "unlimited"), first[1])
        result = H._summarize(first, second, 800, 700)
        self.assertEqual(result["sampled_memory_headroom_hint_mib"], 150)
        self.assertEqual(result["visible_hard_limit_headroom_mib"], 150)

    def test_high_threshold_and_round_down(self):
        levels = (H.Level(10*M+1, 100*M, 20*M),)
        result = H._summarize(levels, levels, 100, 100)
        self.assertEqual(result["visible_high_threshold_headroom_mib"], 9)
        self.assertEqual(result["sampled_memory_headroom_hint_mib"], 9)

    def test_host_limit_and_unlimited_distinct(self):
        levels = (H.Level(10*M, "unlimited", "unlimited"),)
        result = H._summarize(levels, levels, 20, 19)
        self.assertIsNone(result["visible_hard_limit_headroom_mib"])
        self.assertIsNone(result["visible_high_threshold_headroom_mib"])
        self.assertEqual(result["sampled_memory_headroom_hint_mib"], 19)

    def test_over_limit_zero(self):
        levels = (H.Level(100*M, 90*M, 80*M),)
        self.assertEqual(H._summarize(levels, levels, 100, 100)
                         ["sampled_memory_headroom_hint_mib"], 0)

    def test_changed_limit_refused(self):
        with self.assertRaisesRegex(H.I5.CgroupRefusal, "MEMORY_LIMIT_CHANGED"):
            H._summarize((H.Level(1, 2, 3),), (H.Level(1, 3, 3),), 100, 100)

    def test_missing_host_refused(self):
        levels = (H.Level(1, 2, 3),)
        for value in (None, True, -1):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "HOST_MEMORY_UNAVAILABLE"):
                H._summarize(levels, levels, value, 100)

    def test_empty_hierarchy_refused(self):
        with self.assertRaisesRegex(H.I5.CgroupRefusal, "INCOMPLETE_HIERARCHY"):
            H._summarize((), (), 100, 100)

    def test_actual_fd_reads_and_invalid_counters(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / "memory.current").write_text("123\n")
            (path / "memory.max").write_text("max\n")
            (path / "memory.high").write_text("500\n")
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                self.assertEqual(H._read_level(fd), H.Level(123, "unlimited", 500))
                (path / "memory.high").write_text("garbage\n")
                with self.assertRaises(H.I5.CgroupRefusal):
                    H._read_level(fd)
                (path / "memory.high").unlink()
                (path / "memory.high").symlink_to(path / "memory.current")
                with self.assertRaises(OSError):
                    H._read_level(fd)
            finally:
                os.close(fd)

    def test_observe_real_fixture_directories(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            for level, current, limit in ((p/"parent", 50*M, 100*M),
                                          (p/"parent"/"child", 10*M, 80*M)):
                level.mkdir()
                (level/"memory.current").write_text(str(current))
                (level/"memory.max").write_text(str(limit))
                (level/"memory.high").write_text("max")
            def open_group(parts):
                return os.open(p.joinpath(*parts), os.O_RDONLY | os.O_DIRECTORY)
            with patch.object(H.I5, "_open_group", side_effect=open_group), \
                 patch.object(H.I5, "_mount", return_value=("mount", "device")), \
                 patch.object(H, "_host_memory_available_mib", return_value=1000):
                result = H.observe("/parent/child")
            self.assertEqual(result["sampled_memory_headroom_hint_mib"], 50)
            self.assertEqual(result["visible_nonroot_levels_sampled"], 2)
            for key in ("runtime_identity_verified", "complete_host_hierarchy_verified",
                        "atomic_snapshot", "allocatable_memory_established",
                        "safe_to_start_inference", "resource_reserved", "permission_granted",
                        "production_authority"):
                self.assertIs(result[key], False)
            self.assertNotIn("/parent", str(result))
            self.assertNotIn(root, str(result))

    def test_invalid_group_refused(self):
        for path in ("/", "/../bad", "relative", "/a//b"):
            with self.assertRaises(H.I5.CgroupRefusal):
                H.observe(path)

    def test_mount_change_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            for name, content in (("memory.current", "10"), ("memory.max", "100"),
                                  ("memory.high", "max")):
                (p/name).write_text(content)
            with patch.object(H.I5, "_open_group",
                              side_effect=lambda _: os.open(root, os.O_RDONLY | os.O_DIRECTORY)), \
                 patch.object(H.I5, "_mount", side_effect=[("a","b"),("c","d")]), \
                 patch.object(H, "_host_memory_available_mib", return_value=100):
                with self.assertRaisesRegex(H.I5.CgroupRefusal, "CGROUP_SCOPE_CHANGED"):
                    H.observe("/fixture")

    def test_native_self_group_read_if_supported(self):
        if sys.platform != "linux":
            self.skipTest("Linux only")
        path = next((line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines()
                     if line.startswith("0::")), None)
        if not path or path == "/":
            self.skipTest("No explicit non-root self group")
        try:
            result = H.observe(path)
        except H.I5.CgroupRefusal as exc:
            self.skipTest("Native hierarchy unsupported: " + str(exc))
        self.assertGreaterEqual(result["sampled_memory_headroom_hint_mib"], 0)
        self.assertFalse(result["safe_to_start_inference"])


class PressureTests(unittest.TestCase):
    PSI = b"some avg10=0.25 avg60=1.10 avg300=0.00 total=100\nfull avg10=0.00 avg60=0.10 avg300=0.00 total=20\n"
    EVENTS = b"low 0\nhigh 1\nmax 2\noom 0\noom_kill 0\n"

    def test_exact_parse_units_and_optional_events(self):
        first = (H._pressure(self.PSI), H._events(self.EVENTS))
        second = (H._pressure(self.PSI.replace(b"total=100", b"total=150")),
                  H._events(self.EVENTS.replace(b"high 1", b"high 3")))
        out = H._pressure_summary(first, second)
        self.assertEqual(out["psi"]["some"]["avg10_hundredths_percent"], 25)
        self.assertEqual(out["psi"]["some"]["avg60_hundredths_percent"], 110)
        self.assertEqual(out["psi"]["some"]["observed_delta_us"], 50)
        self.assertEqual(out["events_observed_delta"]["high"], 2)
        self.assertIsNone(out["events_total"]["oom_group_kill"])
        self.assertFalse(out["pressure_free_established"])

    def test_malformed_pressure_refused(self):
        for raw in (b"", self.PSI.splitlines()[0], self.PSI+self.PSI,
                    self.PSI.replace(b"0.25", b"100.01"),
                    self.PSI.replace(b"0.25", b"nan"),
                    self.PSI.replace(b"total=100", b"total=-1"),
                    self.PSI.replace(b"total=100", b"total=9223372036854775808")):
            with self.subTest(raw=raw), self.assertRaises(H.I5.CgroupRefusal):
                H._pressure(raw)

    def test_invalid_events_refused(self):
        for raw in (b"", self.EVENTS.replace(b"oom_kill 0\n", b""),
                    self.EVENTS+self.EVENTS, self.EVENTS.replace(b"max 2", b"max -1"),
                    self.EVENTS.replace(b"max 2", b"max 9223372036854775808")):
            with self.subTest(raw=raw), self.assertRaises(H.I5.CgroupRefusal):
                H._events(raw)

    def test_counter_reset_and_key_change_refused(self):
        first = (H._pressure(self.PSI), H._events(self.EVENTS))
        for second in (
            (H._pressure(self.PSI.replace(b"total=100", b"total=99")), first[1]),
            (first[0], H._events(self.EVENTS.replace(b"max 2", b"max 1"))),
            (first[0], H._events(self.EVENTS+b"oom_group_kill 0\n")),
        ):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "MEMORY_COUNTER_CONTINUITY_LOST"):
                H._pressure_summary(first, second)

    def test_existing_observer_opt_in_and_fd_boundaries(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            for name, value in (("memory.current", b"10"), ("memory.max", b"100"),
                                ("memory.high", b"max"), ("memory.pressure", self.PSI),
                                ("memory.events", self.EVENTS)):
                (path/name).write_bytes(value)
            with patch.object(H.I5, "_open_group",
                              side_effect=lambda _: os.open(root, os.O_RDONLY | os.O_DIRECTORY)), \
                 patch.object(H.I5, "_mount", return_value=("mount","device")), \
                 patch.object(H, "_host_memory_available_mib", return_value=100):
                ordinary = H.observe("/fixture")
                observed = H.observe("/fixture", pressure=True)
                self.assertNotIn("selected_cgroup_pressure", ordinary)
                self.assertEqual(observed["selected_cgroup_pressure"]["events_observed_delta"]["oom"], 0)
                self.assertFalse(observed["safe_to_start_inference"])
                self.assertNotIn(root, str(observed))
                (path/"memory.pressure").unlink()
                with self.assertRaises(H.I5.CgroupRefusal):
                    H.observe("/fixture", pressure=True)
                (path/"memory.pressure").symlink_to(path/"memory.events")
                with self.assertRaises(H.I5.CgroupRefusal):
                    H.observe("/fixture", pressure=True)
                self.assertNotIn("selected_cgroup_pressure", H.observe("/fixture"))

    def test_native_pressure_optional(self):
        if sys.platform != "linux":
            self.skipTest("Linux only")
        path = next((line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines()
                     if line.startswith("0::")), None)
        if not path or path == "/":
            self.skipTest("No explicit non-root self group")
        try:
            observed = H.observe(path, pressure=True)
        except H.I5.CgroupRefusal as exc:
            self.skipTest("Native pressure unsupported: " + str(exc))
        self.assertGreaterEqual(observed["selected_cgroup_pressure"]["events_total"]["oom"], 0)
        self.assertFalse(observed["safe_to_start_inference"])
