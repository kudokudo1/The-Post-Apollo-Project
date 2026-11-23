"""P2C disposable read-only preflight tests; never run real model inference."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import performance_capacity_p2c as p2c
import performance_snapshot_p0 as p0

MODEL = "granite4:small-h"


class Handler(BaseHTTPRequestHandler):
    calls = []
    post_count = 0
    get_status = 200
    models = [{"name": MODEL, "size": 1000000000}]
    resident = []
    version = {"version": "0.32.14"}
    raw_response = None

    def do_GET(self):
        type(self).calls.append((self.command, self.path))
        if type(self).raw_response is not None:
            data = type(self).raw_response
        else:
            if self.path == "/api/tags":
                payload = {"models": type(self).models}
            elif self.path == "/api/ps":
                payload = {"models": type(self).resident}
            elif self.path == "/api/version":
                payload = type(self).version
            else:
                payload = {}
            data = json.dumps(payload).encode("utf-8")
        self.send_response(type(self).get_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        type(self).post_count += 1
        self.send_response(405)
        self.end_headers()

    def log_message(self, *_):
        pass


class CapacityP2CTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.worker = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.worker.start()
        cls.endpoint = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def setUp(self):
        Handler.calls = []
        Handler.post_count = 0
        Handler.get_status = 200
        Handler.raw_response = None
        Handler.models = [{"name": MODEL, "size": 1000000000}]
        Handler.resident = []
        Handler.version = {"version": "0.32.14"}
        # Fake the host for observer tests, but do NOT shadow the exact
        # helper functions under test in the dedicated CPU/GPU cases.
        patches = [
            patch.object(p0, "_host_memory_available_mib", return_value=2280),
            patch.object(p0.os, "cpu_count", return_value=16),
        ]
        if not self._testMethodName.startswith("test_affinity_"):
            patches.append(patch.object(
                p2c, "_process_affinity_threads", return_value=8
            ))
        if not (self._testMethodName.startswith("test_gpu_")
                or self._testMethodName.startswith("test_multiple_cards_")):
            patches.append(patch.object(p2c, "_gpu_devices", return_value=[]))
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def inspect(self, **kwargs):
        return p2c.inspect_capacity(endpoint=self.endpoint, **kwargs)

    def test_observer_uses_get_only_and_no_inference(self):
        report = self.inspect()
        self.assertEqual(Handler.calls, [
            ("GET", "/api/tags"),
            ("GET", "/api/version"),
            ("GET", "/api/ps"),
        ])
        self.assertEqual(Handler.post_count, 0)
        for key in ("generation_requested", "model_load_requested",
                    "benchmark_permitted", "permission_granted",
                    "production_authority", "resource_budget_established"):
            self.assertIs(report[key], False)
        self.assertEqual(report["c5_authority"], "NOT_EVALUATED")

    def test_selected_installed_not_resident(self):
        report = self.inspect(model=MODEL)
        selected = report["selected_model"]
        self.assertEqual(selected["model"], MODEL)
        self.assertIs(selected["installed"], True)
        self.assertIs(selected["resident"], False)
        self.assertEqual(selected["installed_artifact_bytes_reported"],
                         1000000000)
        self.assertIsNone(selected["resident_memory_bytes_reported"])
        self.assertIs(selected["runtime_requirement_calibrated"], False)

    def test_selected_resident_reports_used_not_free_vram(self):
        Handler.resident = [{
            "name": MODEL, "model": MODEL, "size": 500000000,
            "size_vram": 400000000, "context_length": 2048,
        }]
        report = self.inspect(model=MODEL)
        self.assertTrue(report["selected_model"]["resident"])
        self.assertEqual(report["selected_model"]["resident_vram_bytes_reported"],
                         400000000)
        self.assertIs(report["gpu_metrics_are_free_allocatable_vram"], False)
        self.assertIs(report["model_requirements_established"], False)

    def test_selected_model_must_match_exact_name(self):
        report = self.inspect(model="granite4:small")
        self.assertFalse(report["selected_model"]["installed"])
        self.assertFalse(report["selected_model"]["resident"])

    def test_no_selected_model_is_valid(self):
        report = self.inspect()
        self.assertIsNone(report["selected_model"])
        self.assertEqual(report["installed_model_count"], 1)

    def test_host_memory_and_process_affinity_are_separate_hints(self):
        report = self.inspect()
        self.assertEqual(report["host_mem_available_mib"], 2280)
        self.assertEqual(report["host_visible_cpu_threads"], 16)
        self.assertEqual(report["process_affinity_cpu_threads"], 8)
        self.assertFalse(report["exclusive_capacity_reserved"])

    def test_missing_gpu_metrics_is_not_proof_of_no_gpu(self):
        report = self.inspect()
        self.assertEqual(report["gpu_devices"], [])
        self.assertEqual(report["gpu_sysfs_status"], "UNAVAILABLE")
        self.assertFalse(report["ollama_device_mapping_verified"])

    def test_reported_gpu_counters_are_not_authority(self):
        device = {
            "card": "card0",
            "vram_total_bytes_reported": 4 * 1024**3,
            "vram_used_bytes_reported": 3 * 1024**3,
            "vram_headroom_bytes_estimated": 1024**3,
            "measurement_scope": "DRM_SYSFS_DIAGNOSTIC_ONLY",
            "ollama_device_mapping_verified": False,
        }
        with patch.object(p2c, "_gpu_devices", return_value=[device]):
            report = self.inspect(model=MODEL)
        self.assertEqual(report["gpu_devices"], [device])
        self.assertEqual(report["gpu_sysfs_status"], "COUNTERS_OBSERVED")
        self.assertFalse(report["benchmark_permitted"])
        self.assertFalse(report["gpu_metrics_are_free_allocatable_vram"])

    def test_invalid_model_rejected_before_network(self):
        for value in ("../secret", "name with spaces", "", 123, False):
            with self.subTest(model=value):
                with self.assertRaisesRegex(p2c.CapacityFailure, "INVALID_MODEL"):
                    self.inspect(model=value)
        self.assertEqual(Handler.calls, [])

    def test_non_loopback_endpoints_refuse_before_network(self):
        for endpoint in ("http://example.com:11434",
                         "https://127.0.0.1:11434",
                         self.endpoint + "/api/chat",
                         "http://user:secret@127.0.0.1:11434",
                         "http://localhost.bad.org:11434"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(p2c.CapacityFailure):
                    p2c.inspect_capacity(endpoint=endpoint)
        self.assertEqual(Handler.calls, [])

    def test_failed_tags_refuses_before_snapshot(self):
        Handler.get_status = 302
        with self.assertRaisesRegex(
            p2c.CapacityFailure, "LOCAL_OBSERVATION_UNAVAILABLE"
        ):
            self.inspect()
        self.assertEqual(Handler.calls, [("GET", "/api/tags")])

    def test_malformed_tags_refused_with_safe_code(self):
        Handler.raw_response = b'{"models": null}'
        with self.assertRaisesRegex(
            p2c.CapacityFailure, "LOCAL_OBSERVATION_UNAVAILABLE"
        ):
            self.inspect()
        self.assertEqual(Handler.post_count, 0)

    def test_malformed_snapshot_refused_safely(self):
        Handler.version = {"version": 100}
        with self.assertRaisesRegex(
            p2c.CapacityFailure, "LOCAL_OBSERVATION_UNAVAILABLE"
        ):
            self.inspect()
        self.assertEqual(Handler.post_count, 0)

    def test_cli_outputs_one_json_without_persistence(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = p2c.main(["inspect", "--endpoint", self.endpoint,
                           "--model", MODEL])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().count("\n"), 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "OBSERVED")
        self.assertEqual(Handler.post_count, 0)

    def test_cli_error_redacts_endpoint_and_model(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = p2c.main([
                "inspect", "--model", "private:model",
                "--endpoint", "http://sensitive.example.invalid:11434",
            ])
        self.assertEqual(rc, 2)
        report = json.loads(out.getvalue())
        self.assertEqual(report["status"], "UNAVAILABLE")
        self.assertNotIn("sensitive.example", out.getvalue())
        self.assertNotIn("private:model", out.getvalue())
        self.assertFalse(report["benchmark_permitted"])

    def test_sysfs_uint_strict_valid_decimal_only(self):
        def fake_open(path, mode):
            self.assertEqual(mode, "rb")
            self.assertEqual(path, "/safe/counter")
            return io.BytesIO(b"4294967296\n")
        with patch("builtins.open", side_effect=fake_open):
            self.assertEqual(p2c._sysfs_uint("/safe/counter"), 4294967296)

    def test_sysfs_uint_malformed_or_missing_stays_unknown(self):
        for raw in (b"", b"-1\n", b"true", b"3.2\n",
                    b" 123\n", b"1 2", b"12\n34",
                    b"1" * 65, str(2**64).encode("ascii")):
            with self.subTest(raw=raw[:20]):
                with patch("builtins.open", return_value=io.BytesIO(raw)):
                    self.assertIsNone(p2c._sysfs_uint("/safe"))
        with patch("builtins.open", side_effect=FileNotFoundError()):
            self.assertIsNone(p2c._sysfs_uint("/safe"))

    def test_gpu_device_one_counter_missing_yields_null_headroom(self):
        values = {
            "/virtual/card0/device/mem_info_vram_total": 4 * 1024**3,
            "/virtual/card0/device/mem_info_vram_used": None,
        }
        with patch.object(p2c, "_sysfs_uint",
                          side_effect=lambda p: values.get(p)):
            rows = p2c._gpu_devices(root="/virtual")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["vram_used_bytes_reported"])
        self.assertIsNone(rows[0]["vram_headroom_bytes_estimated"])

    def test_gpu_device_used_exceeds_total_never_negative_free(self):
        def reader(path):
            if path.endswith("mem_info_vram_total"):
                return 1024
            if path.endswith("mem_info_vram_used"):
                return 2048
            return None
        with patch.object(p2c, "_sysfs_uint", side_effect=reader):
            rows = p2c._gpu_devices(root="/virtual")
        self.assertTrue(rows)
        self.assertTrue(all(
            row["vram_headroom_bytes_estimated"] is None for row in rows
        ))

    def test_gpu_device_free_difference_is_diagnostic_only(self):
        def reader(path):
            if "card1/" not in path:
                return None
            return 1024 if path.endswith("mem_info_vram_total") else 256
        with patch.object(p2c, "_sysfs_uint", side_effect=reader):
            rows = p2c._gpu_devices(root="/virtual")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["card"], "card1")
        self.assertEqual(rows[0]["vram_headroom_bytes_estimated"], 768)
        self.assertIs(rows[0]["ollama_device_mapping_verified"], False)

    def test_multiple_cards_are_not_summed_into_ollama_capacity(self):
        def reader(path):
            if "card0/" in path or "card1/" in path:
                return 2048 if path.endswith("mem_info_vram_total") else 1024
            return None
        with patch.object(p2c, "_sysfs_uint", side_effect=reader):
            rows = p2c._gpu_devices(root="/virtual")
        self.assertEqual(len(rows), 2)
        self.assertFalse(any("combined_free" in row for row in rows))

    def test_gpu_scan_is_bounded_and_never_scans_card8(self):
        examined = []
        def reader(path):
            examined.append(path)
            return None
        with patch.object(p2c, "_sysfs_uint", side_effect=reader):
            self.assertEqual(p2c._gpu_devices(root="/virtual"), [])
        self.assertEqual(len(examined), p2c.MAX_GPU_CARDS * 2)
        self.assertFalse(any("card8" in path for path in examined))

    def test_affinity_unavailable_is_null_not_zero(self):
        with patch.object(p2c.os, "sched_getaffinity",
                          side_effect=OSError()):
            self.assertIsNone(p2c._process_affinity_threads())

    def test_affinity_count_is_schedulable_not_free(self):
        with patch.object(p2c.os, "sched_getaffinity",
                          return_value={2, 3, 4}):
            self.assertEqual(p2c._process_affinity_threads(), 3)

    def test_no_runtime_imports_scheduler_or_model_posts(self):
        path = (Path(__file__).resolve().parents[2]
                / "scripts/forest/performance_capacity_p2c.py")
        source = path.read_text()
        for forbidden in ("subprocess", "Popen(", "os.system", "/api/chat",
                          "/api/generate", "POST", "keep_alive", "systemctl",
                          "sqlite3", "start_scheduler", "requests.post",
                          "write("):
            with self.subTest(word=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
