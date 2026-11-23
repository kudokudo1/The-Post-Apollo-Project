"""Forest Performance P0 // disposable loopback and parser regressions.

All HTTP responses are fake local fixtures; no model is started or queried
for inference, and no installed Ollama or user files are used.
"""
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
import performance_snapshot_p0 as p0


class Handler(BaseHTTPRequestHandler):
    calls = []
    version_status = 200
    ps_status = 200
    content_type = "application/json"
    version_body = b'{"version":"0.32.14"}'
    ps_body = b'{"models":[]}'
    post_count = 0

    def do_GET(self):
        type(self).calls.append((self.command, self.path))
        path = self.path
        status = type(self).version_status if path == "/api/version" else type(self).ps_status
        body = type(self).version_body if path == "/api/version" else type(self).ps_body
        self.send_response(status)
        self.send_header("Content-Type", type(self).content_type)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        type(self).post_count += 1
        self.send_response(405)
        self.end_headers()

    def log_message(self, *_):
        pass


class PerformanceSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        Handler.calls = []
        Handler.post_count = 0
        Handler.version_status = 200
        Handler.ps_status = 200
        Handler.content_type = "application/json"
        Handler.version_body = b'{"version":"0.32.14"}'
        Handler.ps_body = b'{"models":[]}'
        self.memory = patch.object(p0, "_host_memory_available_mib", return_value=3400)
        self.cpu = patch.object(p0.os, "cpu_count", return_value=8)
        self.memory.start()
        self.cpu.start()
        self.addCleanup(self.memory.stop)
        self.addCleanup(self.cpu.stop)

    def set_ps(self, models):
        Handler.ps_body = json.dumps({"models": models}).encode("utf-8")

    def test_observes_version_residency_and_host_hints_without_inference(self):
        self.set_ps([
            {"name": "qwen3:1.7b", "model": "qwen3:1.7b",
             "size": 1000, "size_vram": 750, "context_length": 4096},
            {"name": "granite4:small", "size": 3000,
             "size_vram": 0, "context_length": 64000},
        ])
        x = p0.snapshot(self.url)
        self.assertEqual(x["status"], "OBSERVED")
        self.assertEqual(x["version"], "0.32.14")
        self.assertEqual(x["resident_model_count"], 2)
        self.assertEqual(x["vram_bytes_reported_total"], 750)
        self.assertEqual(x["host_visible_cpu_threads"], 8)
        self.assertEqual(x["host_mem_available_mib"], 3400)
        self.assertEqual(
            [r["model"] for r in x["resident_models"]],
            ["granite4:small", "qwen3:1.7b"])
        self.assertIs(x["generation_requested"], False)
        self.assertIs(x["model_load_requested"], False)
        self.assertIs(x["inference_latency_measured"], False)
        self.assertIs(x["production_authority"], False)
        self.assertEqual(x["governor_decision"], "NOT_EVALUATED")
        self.assertEqual(Handler.calls, [
            ("GET", "/api/version"), ("GET", "/api/ps")])
        self.assertEqual(Handler.post_count, 0)

    def test_no_models_is_a_valid_observation(self):
        x = p0.snapshot(self.url)
        self.assertEqual(x["resident_models"], [])
        self.assertEqual(x["vram_bytes_reported_total"], 0)

    def test_optional_residency_fields_stay_unknown(self):
        self.set_ps([{"model": "qwen3:1.7b", "size": 11}])
        x = p0.snapshot(self.url)
        self.assertIsNone(x["resident_models"][0]["vram_bytes_reported"])
        self.assertIsNone(x["resident_models"][0]["context_length_reported"])
        self.assertIsNone(x["vram_bytes_reported_total"])

    def test_version_failure_never_fetches_residency(self):
        Handler.version_body = b'{"version":3}'
        with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_VERSION_INVALID"):
            p0.snapshot(self.url)
        self.assertEqual(Handler.calls, [("GET", "/api/version")])

    def test_non_loopback_endpoints_denied_before_any_network(self):
        for value in (
            "https://127.0.0.1:11434", "http://example.com:11434",
            "http://localhost.evil.com:11434",
            "http://user:pass@127.0.0.1:11434",
            "http://127.0.0.1:11434/api/ps",
            "http://127.0.0.1:11434/?token=x",
        ):
            with self.subTest(endpoint=value):
                with self.assertRaises(p0.ProbeFailure):
                    p0.snapshot(value)
        self.assertEqual(Handler.calls, [])

    def test_localhost_is_normalized_to_loopback(self):
        x = p0.snapshot(self.url.replace("127.0.0.1", "localhost"))
        self.assertEqual(x["status"], "OBSERVED")
        self.assertEqual(len(Handler.calls), 2)

    def test_redirects_refused_without_following(self):
        Handler.version_status = 302
        with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_HTTP_ERROR"):
            p0.snapshot(self.url)
        self.assertEqual(Handler.calls, [("GET", "/api/version")])

    def test_bad_content_type_refused(self):
        Handler.content_type = "text/html"
        with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_CONTENT_TYPE"):
            p0.snapshot(self.url)

    def test_duplicate_json_keys_and_nonfinite_values_refused(self):
        for body in (
            b'{"models":[],"models":[]}',
            b'{"models": NaN}',
            b'\xff',
        ):
            Handler.ps_body = body
            with self.subTest(body=body):
                with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_INVALID_JSON"):
                    p0.snapshot(self.url)

    def test_response_bound_applies_to_version_and_residency(self):
        for field in ("version_body", "ps_body"):
            setattr(Handler, field, b" " * (p0.MAX_BODY_BYTES + 1))
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        p0.ProbeFailure, "OLLAMA_RESPONSE_TOO_LARGE"):
                    p0.snapshot(self.url)
            Handler.version_body = b'{"version":"0.32.14"}'
            Handler.ps_body = b'{"models":[]}'

    def test_invalid_ps_schema_fails_closed(self):
        for value in (b'{}', b'[]', b'{"models":{}}',
                      b'{"models":[null]}', b'{"models":[1]}'):
            Handler.ps_body = value
            with self.subTest(payload=value):
                with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_RESIDENCY_INVALID"):
                    p0.snapshot(self.url)

    def test_duplicate_or_mismatched_model_identity_refused(self):
        for models in (
            [{"name": "a", "size": 1}, {"name": "a", "size": 1}],
            [{"name": "a", "model": "b", "size": 1}],
            [{"name": "../bad", "size": 1}],
        ):
            self.set_ps(models)
            with self.subTest(models=models):
                with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_RESIDENCY_INVALID"):
                    p0.snapshot(self.url)

    def test_model_numbers_refuse_booleans_negative_or_forged_types(self):
        for item in (
            {"name": "ok", "size": True},
            {"name": "ok", "size": -1},
            {"name": "ok", "size": 1, "size_vram": "100"},
            {"name": "ok", "size": 1, "context_length": 0},
            {"name": "ok", "size": 2**64},
            {"name": "ok", "size": 1, "size_vram": False},
        ):
            self.set_ps([item])
            with self.subTest(item=item):
                with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_RESIDENCY_INVALID"):
                    p0.snapshot(self.url)

    def test_model_count_limit(self):
        self.set_ps([{"name": "model%d" % i, "size": 1} for i in range(257)])
        with self.assertRaisesRegex(p0.ProbeFailure, "OLLAMA_RESIDENCY_LIMIT"):
            p0.snapshot(self.url)

    def test_parse_mem_available_is_explicit_about_missing_data(self):
        self.assertEqual(p0._parse_mem_available(
            "MemTotal:   8192000 kB\nMemAvailable: 2048000 kB\n"), 2000)
        for text in ("MemFree: 1024 kB\n", "MemAvailable: bad kB\n",
                     "MemAvailable: 1024 kB\nMemAvailable: 2048 kB\n",
                     123, "A" * (p0.MAX_MEMINFO_BYTES + 1)):
            with self.subTest(text=str(text)[:20]):
                self.assertIsNone(p0._parse_mem_available(text))

    def test_cpu_thread_hint_is_optional_not_a_governor_budget(self):
        with patch.object(p0.os, "cpu_count", return_value=None):
            x = p0.snapshot(self.url)
        self.assertIsNone(x["host_visible_cpu_threads"])
        self.assertEqual(x["governor_decision"], "NOT_EVALUATED")

    def test_output_excludes_untrusted_paths_and_prompts(self):
        self.set_ps([{"name": "qwen3:1.7b", "size": 9,
                      "digest": "private fake path",
                      "details": {"model_path": "/private/fake/model"}}])
        data = json.dumps(p0.snapshot(self.url))
        self.assertNotIn("private fake path", data)
        self.assertNotIn("/private/fake/model", data)
        self.assertNotIn("content", data)

    def test_cli_failure_has_fixed_code_and_no_endpoint_leak(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = p0.main(["snapshot", "--endpoint", "http://secret.example:11434"])
        data = json.loads(stream.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(data["status"], "UNAVAILABLE")
        self.assertEqual(data["reason"], "NON_LOOPBACK_ENDPOINT")
        self.assertNotIn("secret.example", stream.getvalue())
        self.assertEqual(Handler.calls, [])

    def test_no_http_post_and_no_server_process_start(self):
        text = (Path(__file__).resolve().parents[2] /
                "scripts/forest/performance_snapshot_p0.py").read_text()
        for forbidden in ("/api/chat", "/api/generate", "/api/pull",
                          "subprocess", "Popen", "os.system(", "Authorization"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(Handler.post_count, 0)


if __name__ == "__main__":
    unittest.main()
