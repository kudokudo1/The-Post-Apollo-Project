from dataclasses import replace
from pathlib import Path
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import process_observation_i4 as M


def stat_line(pid=123, start=900, user=12, system=4, threads=3, state=b"S"):
    fields = [state] + [b"0"] * 49
    for index, value in ((11, user), (12, system), (17, threads), (19, start)):
        fields[index] = str(value).encode()
    return str(pid).encode() + b" (weird ) name\nwith parentheses) " + b" ".join(fields)


class ParserTests(unittest.TestCase):
    def test_stat_comm_with_parentheses_and_newline(self):
        self.assertEqual(M._parse_stat(stat_line(), 123), M.ProcessStat(900, 12, 4, 3))

    def test_wrong_pid_truncated_or_zombie_refused(self):
        for data in (stat_line(pid=124), b"123 (x) S", stat_line(state=b"Z")):
            with self.assertRaises(M.ObservationRefusal):
                M._parse_stat(data, 123)

    def test_invalid_stat_counters(self):
        for raw in (stat_line(user=-1), stat_line(threads=0),
                    stat_line(start=2**63), stat_line(system="x")):
            with self.assertRaises(M.ObservationRefusal):
                M._parse_stat(raw, 123)

    def test_memory_units_and_missing(self):
        self.assertEqual(M._parse_status(b"VmRSS:\t1024 kB\nVmHWM: 2048 kB\nName: private\n"),
                         (1048576, 2097152, None, None, None, None))

    def test_duplicate_invalid_units_negative_and_overflow(self):
        for raw in (b"VmRSS: 1 kB\nVmRSS: 2 kB", b"VmRSS: 4 MB",
                    b"VmRSS: -1 kB", b"VmRSS: 9223372036854775807 kB"):
            with self.assertRaises(M.ObservationRefusal):
                M._parse_status(raw)

    def test_bounded_parser(self):
        with self.assertRaises(M.ObservationRefusal):
            M._parse_status(b"x" * (M.MAX_PROC_BYTES + 1))
        with self.assertRaises(M.ObservationRefusal):
            M._parse_stat(b"x" * (M.MAX_PROC_BYTES + 1), 123)

    def test_sample_checks_start_before_after(self):
        with patch.object(M, "_read_proc", side_effect=[
                stat_line(), b"VmRSS: 5 kB", stat_line(start=901)]):
            with self.assertRaisesRegex(M.ObservationRefusal, "PROCESS_INSTANCE_CHANGED"):
                M._sample(1, 123)

    def test_sample_rejects_cpu_regression(self):
        with patch.object(M, "_read_proc", side_effect=[
                stat_line(), b"VmRSS: 5 kB", stat_line(user=11)]):
            with self.assertRaisesRegex(M.ObservationRefusal, "CPU_COUNTER_REGRESSED"):
                M._sample(1, 123)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.a = M.Sample(100, M.ProcessStat(900, 12, 4, 3),
                          (100, 999, 80, 20, None, 0))
        self.b = M.Sample(200, M.ProcessStat(900, 15, 7, 2),
                          (300, 1000, 200, 100, None, 0))

    def test_sample_max_not_lifetime_highwater(self):
        p = M._summarize((self.a, self.b), 100)
        self.assertEqual(p["rss_sampled_max_bytes"], 300)
        self.assertEqual(p["rss_sampled_increase_bytes"], 200)
        self.assertEqual(p["rss_lifetime_high_water_bytes_reported"], 1000)
        self.assertEqual(p["user_cpu_ticks_delta"], 3)
        self.assertEqual(p["system_cpu_ticks_delta"], 3)

    def test_missing_rss_invalidates_aggregate(self):
        b = replace(self.b, memory=(None, 1000, 200, 100, None, 0))
        p = M._summarize((self.a, b), 100)
        self.assertIsNone(p["rss_sampled_max_bytes"])
        self.assertIsNone(p["rss_sampled_increase_bytes"])

    def test_zero_increase_distinct_from_unknown(self):
        b = replace(self.b, memory=(90, 1000, None, None, None, None))
        self.assertEqual(M._summarize((self.a, b), 100)["rss_sampled_increase_bytes"], 0)

    def test_instance_or_clock_or_tick_regression(self):
        for b in (replace(self.b, stat=replace(self.b.stat, start_ticks=901)),
                  replace(self.b, time_ns=99),
                  replace(self.b, stat=replace(self.b.stat, system_ticks=3))):
            with self.assertRaises(M.ObservationRefusal):
                M._summarize((self.a, b), 100)


class ObservationTests(unittest.TestCase):
    def test_bounds_before_open(self):
        with patch.object(M.os, "open") as op:
            for pid, count, interval in ((True, 2, 100), (0, 2, 100),
                    (123, 1, 100), (123, 21, 100), (123, 2, 99),
                    (123, 2, 501), (123, True, 100)):
                with self.assertRaises(M.ObservationRefusal):
                    M.observe(pid, samples=count, interval_ms=interval)
            op.assert_not_called()

    def test_fixed_fields_only(self):
        with patch.object(M.os, "open") as op:
            with self.assertRaises(M.ObservationRefusal):
                M._read_proc(1, "cmdline")
            op.assert_not_called()

    def test_interruption_closes_directory_and_discards_result(self):
        with patch.object(M.os, "open", return_value=55), \
             patch.object(M.os, "close") as close, \
             patch.object(M.os, "sysconf", return_value=100), \
             patch.object(M, "_sample", side_effect=OSError("private path")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["observe", "--pid", "123", "--samples", "2"]), 2)
        close.assert_called_once_with(55)
        report = json.loads(out.getvalue())
        self.assertEqual(report["reason"], "PROCESS_OBSERVATION_UNAVAILABLE")
        self.assertNotIn("private path", out.getvalue())
        self.assertNotIn("rss_sampled_max_bytes", report)

    def test_cancel_does_not_return_partial_data(self):
        with patch.object(M, "observe", side_effect=KeyboardInterrupt), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["observe", "--pid", "123"]), 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "CANCELLED")

    @unittest.skipUnless(sys.platform == "linux", "native Linux required")
    def test_real_existing_process_observation(self):
        report = M.observe(os.getpid(), samples=2, interval_ms=100)
        self.assertEqual(report["status"], "OBSERVED")
        self.assertEqual(report["sample_count"], 2)
        self.assertGreater(report["rss_first_bytes"], 0)
        self.assertGreaterEqual(report["rss_sampled_max_bytes"], report["rss_first_bytes"])
        self.assertGreater(report["elapsed_ns"], 0)
        for flag in ("process_instance_authenticated", "executable_identity_verified",
                     "model_binding_verified", "workload_isolation_verified",
                     "measurement_coverage_complete", "accelerator_mapping_verified",
                     "runtime_requirements_established", "resource_availability_established",
                     "resource_reserved", "generation_requested", "model_load_requested",
                     "permission_granted", "production_authority"):
            self.assertFalse(report[flag])
        self.assertNotIn("pid", report)

    @unittest.skipUnless(sys.platform == "linux", "native Linux required")
    def test_real_disposable_child_rss_change(self):
        # Test harness alone launches a synthetic child; observer never does.
        script = (
            "import sys\n"
            "print('READY', flush=True)\n"
            "sys.stdin.readline()\n"
            "a=bytearray(24*1024*1024)\n"
            "for i in range(0,len(a),4096): a[i]=1\n"
            "print('ALLOCATED', flush=True)\n"
            "sys.stdin.readline()\n"
        )
        p = subprocess.Popen([sys.executable, "-I", "-B", "-u", "-c", script],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
        try:
            self.assertEqual(p.stdout.readline().strip(), "READY")
            first = M.observe(p.pid, samples=2, interval_ms=100)
            p.stdin.write("allocate\n"); p.stdin.flush()
            self.assertEqual(p.stdout.readline().strip(), "ALLOCATED")
            second = M.observe(p.pid, samples=2, interval_ms=100)
            self.assertGreaterEqual(second["rss_first_bytes"] - first["rss_first_bytes"],
                                    16*1024*1024)
        finally:
            p.stdin.close()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=3)
            p.stdout.close()

    @unittest.skipUnless(sys.platform == "linux", "native Linux required")
    def test_exited_process_refuses(self):
        p = subprocess.Popen([sys.executable, "-I", "-B", "-c", "pass"])
        p.wait(timeout=3)
        with self.assertRaises(M.ObservationRefusal):
            M.observe(p.pid, samples=2, interval_ms=100)


if __name__ == "__main__":
    unittest.main()
