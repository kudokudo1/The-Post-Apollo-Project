"""Forest B0 // disposable loopback-server tests. No installed Ollama required."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/forest/ollama_inventory.py"
spec = importlib.util.spec_from_file_location("forest_ollama_inventory_b0", SCRIPT)
assert spec and spec.loader
forest = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = forest
spec.loader.exec_module(forest)


class Handler(BaseHTTPRequestHandler):
    status_code = 200
    content_type = "application/json"
    body = b'{"models":[]}'
    calls: list[tuple[str, str]] = []

    def do_GET(self):
        type(self).calls.append((self.command, self.path))
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", type(self).content_type)
        self.end_headers()
        try:
            self.wfile.write(type(self).body)
        except BrokenPipeError:
            pass

    def log_message(self, fmt, *args):
        pass


class InventoryTests(unittest.TestCase):
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
        Handler.status_code = 200
        Handler.content_type = "application/json"
        Handler.body = b'{"models":[]}'
        Handler.calls = []

    def payload(self, models):
        Handler.body = json.dumps({"models": models}).encode("utf-8")

    def test_inventory_sorts_models_without_claiming_execution(self):
        self.payload([
            {"name": "qwen3:1.7b", "size": 1400000000},
            {"name": "ibm/granite4:small-h", "size": 19000000000},
        ])
        report = forest.inventory(self.endpoint)
        self.assertEqual(report["status"], "REACHABLE")
        self.assertEqual(report["model_count"], 2)
        self.assertEqual(
            [row["name"] for row in report["models"]],
            ["ibm/granite4:small-h", "qwen3:1.7b"]
        )
        self.assertEqual(report["capabilities"], ["list_models"])
        for key in ("generation_enabled", "tools_enabled", "sessions_enabled"):
            self.assertIs(report[key], False)
        self.assertEqual(Handler.calls, [("GET", "/api/tags")])

    def test_empty_inventory_not_offline(self):
        report = forest.inventory(self.endpoint)
        self.assertEqual(report["model_count"], 0)
        self.assertEqual(report["status"], "REACHABLE")
        self.assertEqual(report["models"], [])

    def test_localhost_normalized_to_literal_loopback(self):
        alternate = self.endpoint.replace("127.0.0.1", "localhost")
        self.assertEqual(forest.inventory(alternate)["status"], "REACHABLE")
        self.assertEqual(Handler.calls, [("GET", "/api/tags")])

    def test_endpoint_rejects_non_loopback_and_untrusted_url_parts(self):
        bad = [
            "https://127.0.0.1:11434", "http://example.org:11434",
            "http://0.0.0.0:11434", "http://127.0.0.2:11434",
            "http://127.0.0.1:11434/api/tags",
            "http://127.0.0.1:11434/?token=test",
            "http://127.0.0.1:11434/#part",
            "http://user:pass@127.0.0.1:11434",
            "http://127.0.0.1:99999", "file:///etc/passwd",
            "http://localhost.evil.example:11434", "127.0.0.1:11434",
            "http://[::ffff:127.0.0.1]:11434",
        ]
        for endpoint in bad:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(forest.InventoryFailure):
                    forest.inventory(endpoint)
        self.assertEqual(Handler.calls, [])

    def test_redirect_is_refused_not_followed(self):
        Handler.status_code = 302
        with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_HTTP_ERROR"):
            forest.inventory(self.endpoint)
        self.assertEqual(Handler.calls, [("GET", "/api/tags")])

    def test_non_json_response_refused(self):
        Handler.content_type = "text/html"
        with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_CONTENT_TYPE"):
            forest.inventory(self.endpoint)

    def test_accepts_json_with_charset(self):
        Handler.content_type = "application/json; charset=utf-8"
        self.assertEqual(forest.inventory(self.endpoint)["model_count"], 0)

    def test_malformed_utf8_and_json_refused(self):
        for body in (b"\xff", b"{not-json}"):
            Handler.body = body
            with self.subTest(body=body):
                with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_INVALID_JSON"):
                    forest.inventory(self.endpoint)

    def test_bounded_payload(self):
        Handler.body = b'{"models":[],"extra":"' + b"x" * forest.MAX_BODY_BYTES + b'"}'
        with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_RESPONSE_TOO_LARGE"):
            forest.inventory(self.endpoint)

    def test_missing_models_key_and_wrong_types_refused(self):
        for body in (b"[]", b"{}", b'{"models":{}}',
                     b'{"models":[null]}', b'{"models":["x"]}'):
            Handler.body = body
            with self.subTest(body=body):
                with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_INVALID_SCHEMA"):
                    forest.inventory(self.endpoint)

    def test_name_and_size_validation(self):
        rows = [
            {"name": "bad model name", "size": 99},
            {"name": "../secret", "size": 3},
            {"name": "x", "size": True},
            {"name": "x", "size": "99"},
            {"name": "x", "size": -1},
            {"name": "x", "size": 2**64},
        ]
        for row in rows:
            self.payload([row])
            with self.subTest(model=row):
                with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_INVALID_SCHEMA"):
                    forest.inventory(self.endpoint)

    def test_duplicate_names_refused(self):
        self.payload([{"name": "qwen3:1.7b", "size": 5},
                      {"name": "qwen3:1.7b", "size": 5}])
        with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_INVALID_SCHEMA"):
            forest.inventory(self.endpoint)

    def test_model_count_limit(self):
        self.payload([{"name": "m%d" % n, "size": n} for n in range(257)])
        with self.assertRaisesRegex(forest.InventoryFailure, "OLLAMA_MODEL_LIMIT"):
            forest.inventory(self.endpoint)

    def test_cli_emits_machine_readable_failure_without_secrets(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = forest.main(["list-models", "--endpoint", "http://not-loopback:11434"])
        result = json.loads(stream.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["reason"], "NON_LOOPBACK_ENDPOINT")
        self.assertNotIn("not-loopback", stream.getvalue())
        self.assertFalse(result["generation_enabled"])
        self.assertEqual(Handler.calls, [])

    def test_no_inference_calls_or_access_to_external_services(self):
        script = SCRIPT.read_text()
        for unsafe in ("subprocess", "exec(", "/api/chat", "/api/generate",
                       "Hospital", "/api/pull", "Authorization", "api_key"):
            with self.subTest(term=unsafe):
                if unsafe == "Hospital":
                    self.assertIn("Hospital/PX", script)  # comment only
                else:
                    self.assertNotIn(unsafe, script)
        self.assertEqual(forest._target(self.endpoint)[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
