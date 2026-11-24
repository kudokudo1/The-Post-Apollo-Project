from dataclasses import replace
from pathlib import Path
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import cgroup_observation_i5 as M


class ParserTests(unittest.TestCase):
    def test_selection(self):
        self.assertEqual(M._parts("/system.slice/ollama.service"),
                         ("system.slice", "ollama.service"))

    def test_bad_selection_before_io(self):
        with patch.object(M.os, "open") as op:
            for path in ("/", "", "relative", "/../x", "/a/./b", "/a//b",
                         "/a/", "/a\nb", "/a\\b", "/"+("a"*129), None):
                with self.subTest(path=path), self.assertRaises(M.CgroupRefusal):
                    M.observe(path)
            op.assert_not_called()

    def test_bounds_before_io(self):
        with patch.object(M.os, "open") as op:
            for count, interval in ((1,100),(11,100),(2,99),(2,501),(True,100)):
                with self.assertRaises(M.CgroupRefusal):
                    M.observe("/group", samples=count, interval_ms=interval)
            op.assert_not_called()

    def test_mount_layout(self):
        self.assertEqual(M._mount_reference(
            b"32 25 0:28 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"),
            (b"32", b"0:28"))

    def test_mount_mismatch(self):
        for raw in (b"", b"32 25 0:28 /other /sys/fs/cgroup rw - cgroup2 cgroup rw",
                    b"32 25 0:28 / /sys/fs/cgroup rw - tmpfs tmpfs rw",
                    b"32 25 0:28 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"*2):
            with self.assertRaises(M.CgroupRefusal):
                M._mount_reference(raw)

    def test_scalar_unknown_zero_unlimited(self):
        self.assertIsNone(M._scalar(None))
        self.assertEqual(M._scalar(b"0\n"), 0)
        self.assertEqual(M._scalar(b"max\n", limit=True), "unlimited")
        with self.assertRaises(M.CgroupRefusal):
            M._scalar(b"max\n")

    def test_invalid_scalar(self):
        for raw in (b"-1", b"1 2", b"9223372036854775808", b"1.0", b""):
            with self.assertRaises(M.CgroupRefusal):
                M._scalar(raw)

    def test_table_known_only_missing_unknown(self):
        self.assertEqual(M._table(b"anon 10\nfile 20\nunrelated 99\n", (b"anon",b"file",b"shmem")),
                         (10,20,None))
        self.assertEqual(M._table(None,(b"anon",)),(None,))

    def test_bad_table(self):
        for raw in (b"anon 1\nanon 2\n", b"anon -1", b"anon", b"anon 1 2"):
            with self.assertRaises(M.CgroupRefusal):
                M._table(raw,(b"anon",))

    def test_fixed_counter_allowlist(self):
        with patch.object(M.os, "open") as op:
            with self.assertRaises(M.CgroupRefusal):
                M._read_counter(1,"cgroup.procs")
            op.assert_not_called()


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.a = M.Sample(100, 1000, 9000, 20, 10000, 5, (100,200,50), (10,6,4))
        self.b = M.Sample(200, 1200, 10000, 40, 10000, 6, (120,210,60), (30,20,10))

    def test_kernel_peak_and_sampled_peak_distinct(self):
        r = M._summary((self.a,self.b))
        self.assertEqual(r["charged_memory_sampled_max_bytes"],1200)
        self.assertEqual(r["charged_memory_sampled_increase_bytes"],200)
        self.assertEqual(r["kernel_memory_peak_last_bytes_reported"],10000)
        self.assertEqual(r["cpu_usage_usec_delta"],20)
        self.assertEqual(r["tasks_last_reported"],6)

    def test_missing_cpu_is_not_zero(self):
        r = M._summary((self.a,replace(self.b,cpu=(None,20,10))))
        self.assertIsNone(r["cpu_usage_usec_delta"])
        self.assertEqual(r["cpu_user_usec_delta"],14)

    def test_regression_and_changed_limit_refused(self):
        for b in (replace(self.b,timestamp_ns=99),
                  replace(self.b,local_limit=9000),
                  replace(self.b,cpu=(9,20,10))):
            with self.assertRaises(M.CgroupRefusal):
                M._summary((self.a,b))

    def test_unlimited_local_not_available_capacity(self):
        r = M._summary((replace(self.a,local_limit="unlimited"),
                        replace(self.b,local_limit="unlimited")))
        self.assertIsNone(r["local_memory_max_bytes"])
        self.assertEqual(r["local_memory_max_status"],"UNLIMITED")


class ObserverTests(unittest.TestCase):
    def fixture(self, root):
        g = Path(root)/"group"
        g.mkdir()
        for name, value in (
            ("memory.current","1024\n"), ("memory.peak","2048\n"),
            ("memory.max","max\n"), ("memory.stat","anon 100\nfile 200\nshmem 10\n"),
            ("cpu.stat","usage_usec 100\nuser_usec 60\nsystem_usec 40\n"),
            ("pids.current","3\n")):
            (g/name).write_text(value)
        return g

    def test_fixture_read_and_privacy(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixture(root)
            with patch.object(M,"ROOT",root), patch.object(M,"_mount",return_value=(b"1",b"0:1")):
                r = M.observe("/group",samples=2,interval_ms=100)
            self.assertEqual(r["charged_memory_first_bytes"],1024)
            self.assertEqual(r["charged_memory_sampled_increase_bytes"],0)
            self.assertIsNone(r["swap_last_bytes_reported"])
            self.assertNotIn(root,str(r))
            self.assertFalse(r["runtime_identity_verified"])
            self.assertFalse(r["resource_reserved"])
            self.assertFalse(r["physical_memory_deduplicated_verified"])
            self.assertFalse(r["generation_requested"])

    def test_symlink_group_refused(self):
        with tempfile.TemporaryDirectory() as root:
            g = self.fixture(root)
            (Path(root)/"alias").symlink_to(g,target_is_directory=True)
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")):
                with self.assertRaises(M.CgroupRefusal):
                    M.observe("/alias",samples=2,interval_ms=100)

    def test_symlink_counter_refused(self):
        with tempfile.TemporaryDirectory() as root:
            g = self.fixture(root)
            (g/"memory.current").unlink()
            (g/"memory.current").symlink_to(g/"memory.peak")
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")):
                with self.assertRaises(M.CgroupRefusal):
                    M.observe("/group",samples=2,interval_ms=100)

    def test_scope_replacement_discards_measurement(self):
        with tempfile.TemporaryDirectory() as root:
            g = self.fixture(root)
            def replace_group(_):
                g.rename(Path(root)/"old")
                self.fixture(root)
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")),patch.object(M.time,"sleep",side_effect=replace_group):
                with self.assertRaisesRegex(M.CgroupRefusal,"CGROUP_SCOPE_CHANGED"):
                    M.observe("/group",samples=2,interval_ms=100)

    def test_changed_mount_discards_measurement(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixture(root)
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",side_effect=[(b"1",b"0:1"),(b"2",b"0:1")]):
                with self.assertRaisesRegex(M.CgroupRefusal,"CGROUP_SCOPE_CHANGED"):
                    M.observe("/group",samples=2,interval_ms=100)

    def test_missing_required_counter_sanitizes(self):
        with tempfile.TemporaryDirectory() as root:
            g = self.fixture(root)
            (g/"memory.current").unlink()
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")),contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(M.main(["observe","--cgroup","/group","--samples","2"]),2)
            r = json.loads(out.getvalue())
            self.assertEqual(r["reason"],"CGROUP_OBSERVATION_UNAVAILABLE")
            self.assertNotIn("charged_memory_first_bytes",r)
            self.assertNotIn(root,out.getvalue())

    def test_oversized_counter_refused(self):
        with tempfile.TemporaryDirectory() as root:
            g = self.fixture(root)
            (g/"memory.current").write_bytes(b"1"*(M.MAX_BYTES+1))
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")):
                with self.assertRaisesRegex(M.CgroupRefusal,"OBSERVATION_TOO_LARGE"):
                    M.observe("/group",samples=2,interval_ms=100)

    def test_cancel_no_partial_data(self):
        with patch.object(M,"observe",side_effect=KeyboardInterrupt),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["observe","--cgroup","/group"]),2)
        self.assertEqual(json.loads(out.getvalue())["reason"],"CANCELLED")

    @unittest.skipUnless(sys.platform=="linux","Linux only")
    def test_native_kernel_counter_read(self):
        # Test harness reads the runner's existing cgroup, never creates or
        # changes one. Root is allowed only for this private helper test.
        self.assertTrue(M._mount())
        paths = [line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines()
                 if line.startswith("0::")]
        self.assertEqual(len(paths),1)
        parts = () if paths[0]=="/" else M._parts(paths[0])
        fd = M._open_group(parts)
        try:
            s = M._sample(fd)
            self.assertGreater(s.current,0)
            self.assertIsInstance(s.cpu[0],int)
        finally:
            os.close(fd)


if __name__ == "__main__":
    unittest.main()
