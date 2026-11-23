"""Forest P2B // fake-loopback tests. NO real Ollama inference is executed."""
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
import performance_benchmark_p2b as bench
import performance_snapshot_p0 as p0

MODEL = "test:small"
OTHER = "other:big"


def resident(name=MODEL, vram=500):
    return {"name": name, "model": name, "size": 1500000,
            "size_vram": vram, "context_length": bench.NUM_CTX}


def final(**overrides):
    packet = {
        "model": MODEL, "done": True,
        "message": {"role": "assistant", "content": ""},
        "done_reason": "stop",
        "total_duration": 2500000000,
        "load_duration": 800000000,
        "prompt_eval_count": 23,
        "prompt_eval_duration": 120000000,
        "eval_count": 10,
        "eval_duration": 1000000000,
    }
    packet.update(overrides)
    return packet


def stream(*packets):
    return b"".join(json.dumps(p).encode("utf-8") + b"\n" for p in packets)


class Handler(BaseHTTPRequestHandler):
    calls = []
    post_payloads = []
    ps_calls = 0
    ps_rows = [[resident()], [resident()]]
    tags = [{"name": MODEL, "size": 1500000}]
    post_body = stream(
        {"model": MODEL, "done": False,
         "message": {"role": "assistant", "content": "READY"}},
        final(),
    )
    post_status = 200
    post_media = "application/x-ndjson"
    get_status = 200
    fragment_stream = False
    post_partial_headers = False

    def do_GET(self):
        type(self).calls.append(("GET", self.path))
        if self.path == "/api/tags":
            body = json.dumps({"models": type(self).tags}).encode("utf-8")
        elif self.path == "/api/version":
            body = b'{"version":"0.32.14"}'
        elif self.path == "/api/ps":
            i = min(type(self).ps_calls, len(type(self).ps_rows) - 1)
            body = json.dumps({"models": type(self).ps_rows[i]}).encode("utf-8")
            type(self).ps_calls += 1
        else:
            body = b'{}'
        self.send_response(type(self).get_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        type(self).calls.append(("POST", self.path))
        data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        type(self).post_payloads.append(data)
        if type(self).post_partial_headers:
            self.wfile.write(
                b"HTTP/1.0 200 OK\r\nContent-Type: application/x-ndjson\r\n"
            )
            self.wfile.flush()
            return
        self.send_response(type(self).post_status)
        self.send_header("Content-Type", type(self).post_media)
        self.end_headers()
        try:
            if type(self).fragment_stream:
                body = type(self).post_body
                for offset in range(0, len(body), 11):
                    self.wfile.write(body[offset:offset + 11])
                    self.wfile.flush()
            else:
                self.wfile.write(type(self).post_body)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def log_message(self, *_):
        pass


class BenchmarkP2BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        Handler.calls = []
        Handler.post_payloads = []
        Handler.ps_calls = 0
        Handler.ps_rows = [[resident()], [resident()]]
        Handler.tags = [{"name": MODEL, "size": 1500000}]
        Handler.post_body = stream(
            {"model": MODEL, "done": False,
             "message": {"role": "assistant", "content": "READY"}},
            final(),
        )
        Handler.post_status = 200
        Handler.post_media = "application/x-ndjson"
        Handler.get_status = 200
        Handler.fragment_stream = False
        Handler.post_partial_headers = False
        self.mem = patch.object(p0, "_host_memory_available_mib",
                                return_value=8192)
        self.mem.start()
        self.addCleanup(self.mem.stop)

    def opts(self, **changes):
        args = dict(model=MODEL, scenario="warm", endpoint=self.endpoint,
                    operator_approved=True, capacity_reviewed=True,
                    no_competing_inference=True,
                    required_host_mib=1536,
                    required_accelerator_mib=512,
                    verified_free_accelerator_mib=1024,
                    expected_runtime="gpu")
        args.update(changes)
        return args

    def run_one(self, **changes):
        return bench.benchmark_one(**self.opts(**changes))

    def test_warm_metadata_only_and_one_post(self):
        result = self.run_one()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["scenario"], "warm")
        self.assertEqual(result["ollama_version"], "0.32.14")
        self.assertEqual(result["provider_generated_tokens_per_second"], 10.0)
        self.assertEqual(result["provider_load_ms"], 800.0)
        self.assertIsNone(result["provider_prompt_cached_count"])
        self.assertTrue(0 <= result["headers_latency_ms"]
                        <= result["first_visible_content_ms"]
                        <= result["client_complete_ms"])
        self.assertEqual([p for p in Handler.calls if p[0] == "POST"],
                         [("POST", "/api/chat")])
        self.assertIs(result["permission_granted"], False)
        self.assertIs(result["production_authority"], False)
        self.assertEqual(result["c5_authority"], "NOT_EVALUATED")
        encoded = json.dumps(result)
        for secret in ("READY", "Reply with", '"thinking":', "/private", '"tools":'):
            self.assertNotIn(secret, encoded)

    def test_post_uses_fixed_synthetic_prompt_without_tool_or_unload(self):
        self.run_one()
        body = json.loads(Handler.post_payloads[0])
        self.assertEqual(body["messages"], [{
            "role": "user", "content": bench.PROMPT
        }])
        self.assertEqual(body["model"], MODEL)
        self.assertEqual(body["options"]["num_ctx"], 2048)
        self.assertEqual(body["options"]["num_predict"], 32)
        self.assertIs(body["think"], False)
        self.assertIs(body["stream"], True)
        self.assertNotIn("keep_alive", body)
        self.assertNotIn("tools", body)
        self.assertNotIn("system", body)

    def test_cold_absent_then_present_uses_single_request(self):
        Handler.ps_rows = [[], [resident()]]
        result = self.run_one(scenario="cold")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(result["before_resident"])
        self.assertTrue(result["after_resident"])
        self.assertEqual(len(Handler.post_payloads), 1)

    def test_refuses_without_operator_approval_before_any_http(self):
        for field in ("operator_approved", "capacity_reviewed",
                      "no_competing_inference"):
            with self.subTest(flag=field):
                with self.assertRaisesRegex(
                    bench.BenchmarkRefusal, "OPERATOR_APPROVAL_REQUIRED"
                ):
                    self.run_one(**{field: False})
        self.assertEqual(Handler.calls, [])

    def test_refuses_missing_capacity_facts_before_any_http(self):
        for field in ("required_host_mib", "required_accelerator_mib",
                      "verified_free_accelerator_mib"):
            with self.subTest(field=field):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one(**{field: None})
        self.assertEqual(Handler.calls, [])

    def test_refuses_insufficient_reviewed_gpu_headroom_before_http(self):
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "CAPACITY_NOT_ESTABLISHED"
        ):
            self.run_one(verified_free_accelerator_mib=511)
        self.assertEqual(Handler.calls, [])

    def test_cpu_gpu_requirements_cannot_be_silently_swapped(self):
        for changes in (
            {"expected_runtime": "cpu", "required_accelerator_mib": 512},
            {"expected_runtime": "gpu", "required_accelerator_mib": 0},
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(
                    bench.BenchmarkRefusal, "CAPACITY_NOT_ESTABLISHED"
                ):
                    self.run_one(**changes)
        self.assertEqual(Handler.calls, [])

    def test_host_mem_available_is_not_just_visible_cpu_count(self):
        with patch.object(p0, "_host_memory_available_mib",
                          return_value=2000):
            with self.assertRaisesRegex(
                bench.BenchmarkRefusal, "HOST_CAPACITY_NOT_ESTABLISHED"
            ):
                self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_unknown_host_mem_availability_holds(self):
        with patch.object(p0, "_host_memory_available_mib",
                          return_value=None):
            with self.assertRaisesRegex(
                bench.BenchmarkRefusal, "HOST_CAPACITY_NOT_ESTABLISHED"
            ):
                self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_cold_does_not_evict_resident_model(self):
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "COLD_MODEL_ALREADY_RESIDENT"
        ):
            self.run_one(scenario="cold")
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_warm_does_not_force_load_absent_model(self):
        Handler.ps_rows = [[], []]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "WARM_MODEL_NOT_RESIDENT"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_refuses_competing_resident_models(self):
        Handler.ps_rows = [[resident(), resident(OTHER)], [resident()]]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "OTHER_RESIDENT_MODELS"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_model_must_be_installed(self):
        Handler.tags = [{"name": "different", "size": 15}]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "MODEL_NOT_INSTALLED"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_refuses_remote_endpoint_and_credentials_before_http(self):
        for endpoint in (
            "http://example.com:11434", "https://127.0.0.1:11434",
            "http://localhost.evil.com:11434",
            "http://user:pass@127.0.0.1:11434",
            self.endpoint + "/api/chat",
            self.endpoint + "/?token=private",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one(endpoint=endpoint)
        self.assertEqual(Handler.calls, [])

    def test_invalid_model_and_scenario_refused_before_http(self):
        for changes in (
            {"model": "../secret"}, {"model": ""},
            {"model": 1}, {"scenario": "parallel"},
            {"expected_runtime": "TPU"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one(**changes)
        self.assertEqual(Handler.calls, [])

    def test_get_redirect_does_not_trigger_post(self):
        Handler.get_status = 302
        with self.assertRaises(bench.BenchmarkRefusal):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_post_redirect_is_refused(self):
        Handler.post_status = 302
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "OLLAMA_HTTP_ERROR"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 1)

    def test_bad_stream_content_type_refused(self):
        Handler.post_media = "text/html"
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "OLLAMA_STREAM_CONTENT_TYPE"
        ):
            self.run_one()

    def test_invalid_json_duplicate_keys_and_nonfinite_refused(self):
        for bad in (
            b'{"done":false,"done":true}\n',
            b'{"done":NaN}\n',
            b'\xff\n',
        ):
            Handler.post_body = bad
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                    bench.BenchmarkRefusal, "INVALID_STREAM_JSON"
                ):
                    self.run_one()
        self.assertEqual(len(Handler.post_payloads), 3)

    def test_incomplete_or_truncated_stream_fails_without_retry(self):
        for bad in (
            b"",
            stream({"model": MODEL, "done": False,
                    "message": {"content": "READY"}}),
            b'{"done":false,"message":{"content":"READY"}}',
        ):
            Handler.post_body = bad
            with self.subTest(bad=bad[:24]):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one()
        self.assertEqual(len(Handler.post_payloads), 3)

    def test_multiple_or_trailing_terminal_frames_refused(self):
        for data in (
            stream({"model": MODEL, "done": False,
                    "message": {"content": "READY"}},
                   final(), final()),
            stream({"model": MODEL, "done": False,
                    "message": {"content": "READY"}},
                   final(), {"done": False, "message": {"content": "tail"}}),
        ):
            Handler.post_body = data
            with self.subTest(length=len(data)):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one()

    def test_model_identity_mismatch_fails(self):
        for data in (
            stream({"model": OTHER, "done": False,
                    "message": {"content": "READY"}}, final()),
            stream({"model": MODEL, "done": False,
                    "message": {"content": "READY"}},
                   final(model=OTHER)),
        ):
            Handler.post_body = data
            with self.subTest(data=data[:40]):
                with self.assertRaisesRegex(
                    bench.BenchmarkRefusal, "MODEL_MISMATCH"
                ):
                    self.run_one()

    def test_tool_calls_and_thinking_output_refused(self):
        for message in (
            {"content": "READY", "tool_calls": [{"function": {}}]},
            {"content": "READY", "thinking": "PRIVATE CHAIN"},
        ):
            Handler.post_body = stream(
                {"model": MODEL, "done": False, "message": message},
                final(),
            )
            with self.subTest(message=message):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one()

    def test_empty_visible_content_is_not_first_token(self):
        Handler.post_body = stream(
            {"model": MODEL, "done": False, "message": {"content": ""}},
            final(),
        )
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "EMPTY_VISIBLE_OUTPUT"
        ):
            self.run_one()

    def test_done_reason_length_is_not_full_completion(self):
        Handler.post_body = stream(
            {"model": MODEL, "done": False,
             "message": {"content": "READY"}},
            final(done_reason="length"),
        )
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "OUTPUT_TRUNCATED"
        ):
            self.run_one()

    def test_missing_invalid_or_boolean_provider_metrics_refused(self):
        for metric in ("total_duration", "load_duration",
                       "prompt_eval_duration", "eval_duration",
                       "prompt_eval_count", "eval_count"):
            for value in (None, True, -1, "42", 2**64):
                Handler.post_body = stream(
                    {"model": MODEL, "done": False,
                     "message": {"content": "READY"}},
                    final(**{metric: value}),
                )
                with self.subTest(metric=metric, value=value):
                    with self.assertRaises(bench.BenchmarkRefusal):
                        self.run_one()

    def test_zero_eval_duration_has_null_not_infinite_rate(self):
        Handler.post_body = stream(
            {"model": MODEL, "done": False,
             "message": {"content": "READY"}},
            final(eval_duration=0),
        )
        result = self.run_one()
        self.assertIsNone(result["provider_generated_tokens_per_second"])

    def test_cached_count_optional_but_bad_type_refused(self):
        good = final(prompt_eval_cached_count=5)
        Handler.post_body = stream(
            {"model": MODEL, "done": False,
             "message": {"content": "READY"}}, good
        )
        self.assertEqual(self.run_one()["provider_prompt_cached_count"], 5)
        for value in (False, -1, "yes", 2**64):
            Handler.post_body = stream(
                {"model": MODEL, "done": False,
                 "message": {"content": "READY"}},
                final(prompt_eval_cached_count=value),
            )
            with self.subTest(value=value):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one()

    def test_oversized_output_and_stream_line_refused(self):
        for body in (
            stream({"model": MODEL, "done": False,
                    "message": {"content": "X" * (bench.MAX_OUTPUT_BYTES + 1)}},
                   final()),
            b'{"done":false,"more":"' + b"X" * (bench.MAX_LINE + 1) + b'"}\n',
        ):
            Handler.post_body = body
            with self.subTest(size=len(body)):
                with self.assertRaises(bench.BenchmarkRefusal):
                    self.run_one()

    def test_post_snapshot_wrong_residency_invalidates_result(self):
        Handler.ps_rows = [[resident()], []]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "WARM_MODEL_NOT_RESIDENT"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 1)

    def test_wrong_runtime_vram_rejected(self):
        Handler.ps_rows = [[resident(vram=0)], [resident(vram=0)]]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "RUNTIME_MISMATCH"
        ):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_cpu_only_case_is_explicitly_distinct(self):
        Handler.ps_rows = [[resident(vram=0)], [resident(vram=0)]]
        result = self.run_one(
            expected_runtime="cpu", required_accelerator_mib=0,
            verified_free_accelerator_mib=0
        )
        self.assertEqual(result["status"], "COMPLETE")

    def test_network_fragmentation_reassembles_valid_ndjson(self):
        Handler.fragment_stream = True
        result = self.run_one()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(len(Handler.post_payloads), 1)
        self.assertIsNotNone(result["first_visible_content_ms"])

    def test_incomplete_response_headers_never_complete(self):
        Handler.post_partial_headers = True
        with self.assertRaises(bench.BenchmarkRefusal):
            self.run_one()
        self.assertEqual(len(Handler.post_payloads), 1)

    def test_cpu_runtime_mismatch_is_refused_before_post(self):
        Handler.ps_rows = [[resident(vram=200)], [resident(vram=200)]]
        with self.assertRaisesRegex(
            bench.BenchmarkRefusal, "RUNTIME_MISMATCH"
        ):
            self.run_one(expected_runtime="cpu",
                         required_accelerator_mib=0,
                         verified_free_accelerator_mib=0)
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_residency_skip_is_distinct_from_refusal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = bench.main([
                "one", "--model", MODEL, "--scenario", "cold",
                "--endpoint", self.endpoint, "--operator-approved",
                "--capacity-reviewed", "--no-competing-inference",
                "--required-host-mib", "1536",
                "--required-accelerator-mib", "512",
                "--verified-free-accelerator-mib", "1024",
            ])
        result = json.loads(out.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(result["status"], "SKIPPED")
        self.assertEqual(result["reason"], "COLD_MODEL_ALREADY_RESIDENT")
        self.assertFalse(result["inference_complete"])
        self.assertEqual(len(Handler.post_payloads), 0)

    def test_cli_denial_is_json_and_never_networks(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = bench.main([
                "one", "--model", MODEL, "--scenario", "warm",
                "--endpoint", self.endpoint,
            ])
        result = json.loads(out.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(result["reason"], "OPERATOR_APPROVAL_REQUIRED")
        self.assertEqual(Handler.calls, [])

    def test_cli_does_not_leak_endpoint_or_model_on_refusal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = bench.main([
                "one", "--model", "veryprivate:model",
                "--scenario", "cold",
                "--endpoint", "http://secret.invalid:11434",
                "--operator-approved", "--capacity-reviewed",
                "--no-competing-inference",
                "--required-host-mib", "100",
                "--required-accelerator-mib", "512",
                "--verified-free-accelerator-mib", "1024",
            ])
        self.assertEqual(status, 2)
        data = json.loads(out.getvalue())
        self.assertEqual(data["status"], "REFUSED")
        self.assertNotIn("secret.invalid", out.getvalue())
        self.assertNotIn("veryprivate:model", out.getvalue())

    def test_keyboard_interrupt_maps_to_cancelled_and_no_stacktrace(self):
        with patch.object(bench, "benchmark_one", side_effect=KeyboardInterrupt):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = bench.main(["one", "--model", MODEL,
                                     "--scenario", "warm"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "CANCELLED")

    def test_no_auto_loop_subprocess_service_restart_or_file_writer(self):
        src = (Path(__file__).resolve().parents[2] /
               "scripts/forest/performance_benchmark_p2b.py").read_text()
        for forbidden in ("subprocess", "Popen(", "os.system",
                          "/api/pull", "/api/generate",
                          "systemctl", "keep_alive", "open(", "sqlite3",
                          "logging.", "requests.", "threading"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, src)
        self.assertFalse(hasattr(bench, "start_scheduler"))


if __name__ == "__main__":
    unittest.main()
