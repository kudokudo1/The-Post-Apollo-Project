"""Forest B2 // disposable loopback streaming tests; no real Ollama needed."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import ollama_chat_transport as chat  # noqa: E402


def packet(content="", *, done=False, message=None, **extra):
    msg = {"role": "assistant", "content": content} if message is None else message
    return (json.dumps({"message": msg, "done": done, **extra}) + "\n").encode()


class FakeOllama(BaseHTTPRequestHandler):
    response_status = 200
    response_type = "application/x-ndjson"
    lines = [packet("Hello", done=False), packet(" world", done=True)]
    observed: list[tuple[str, str, dict]] = []

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size)
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {}
        type(self).observed.append((self.command, self.path, parsed))
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", type(self).response_type)
        self.end_headers()
        try:
            for line in type(self).lines:
                self.wfile.write(line)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.endpoint = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        FakeOllama.response_status = 200
        FakeOllama.response_type = "application/x-ndjson"
        FakeOllama.lines = [packet("Hello"), packet(" world", done=True)]
        FakeOllama.observed = []

    def run_chat(self, **kwargs):
        params = dict(model="qwen3:1.7b",
                      messages=[{"role": "user", "content": "hi"}],
                      endpoint=self.endpoint)
        params.update(kwargs)
        return list(chat.stream_chat(**params))

    def test_stream_has_provisional_deltas_and_final_complete(self):
        events = self.run_chat()
        self.assertEqual([e["event"] for e in events],
                         ["STARTED", "DELTA", "DELTA", "COMPLETE"])
        self.assertEqual(events[1]["text"], "Hello")
        self.assertEqual(events[-1]["text"], "Hello world")
        self.assertEqual(events[-1]["provider"], "ollama")
        self.assertEqual(FakeOllama.observed[0][0:2], ("POST", "/api/chat"))

    def test_request_contains_only_allowed_options_and_explicit_history(self):
        self.run_chat(model="ibm/granite4:small-h", max_predict=64, num_ctx=2048,
                      messages=[{"role": "user", "content": "one"},
                                {"role": "assistant", "content": "two"},
                                {"role": "user", "content": "three"}])
        data = FakeOllama.observed[0][2]
        self.assertEqual(set(data), {"model", "messages", "stream", "options"})
        self.assertEqual(data["model"], "ibm/granite4:small-h")
        self.assertIs(data["stream"], True)
        self.assertEqual(data["options"], {"num_predict": 64, "num_ctx": 2048})
        self.assertEqual([m["content"] for m in data["messages"]],
                         ["one", "two", "three"])
        for forbidden in ("tools", "think", "system", "format", "keep_alive"):
            self.assertNotIn(forbidden, data)

    def test_no_network_for_bad_model_prompt_or_history(self):
        cases = [
            dict(model="bad model"), dict(model="../../bad"),
            dict(messages=[]),
            dict(messages=[{"role": "assistant", "content": "x"}]),
            dict(messages=[{"role": "system", "content": "act"}]),
            dict(messages=[{"role": "user", "content": "a", "tools": []}]),
            dict(messages=[{"role": "user", "content": "x" * 4097}]),
            dict(messages=[{"role": "user", "content": "\x00"}]),
            dict(messages=[{"role": "user", "content": "\ud800"}]),
            dict(max_predict=0), dict(max_predict=True), dict(max_predict=513),
            dict(num_ctx=256), dict(num_ctx="4096"),
        ]
        for case in cases:
            with self.subTest(case=str(case)[:60]):
                with self.assertRaises(chat.ChatRefusal):
                    self.run_chat(**case)
        self.assertEqual(FakeOllama.observed, [])

    def test_endpoint_stays_loopback_and_rejects_redirect_host(self):
        for endpoint in ("http://example.com:11434",
                         "http://0.0.0.0:11434",
                         "http://localhost.evil.com:11434",
                         "https://127.0.0.1:11434",
                         "http://127.0.0.1:11434/api/chat"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(chat.ChatRefusal):
                    self.run_chat(endpoint=endpoint)
        self.assertEqual(FakeOllama.observed, [])

    def test_http_error_and_redirect_fail_without_inference_retry(self):
        for status in (302, 404, 500):
            FakeOllama.response_status = status
            with self.subTest(status=status):
                with self.assertRaisesRegex(chat.ChatRefusal, "OLLAMA_HTTP_ERROR"):
                    self.run_chat()
        self.assertEqual(len(FakeOllama.observed), 3)

    def test_refuses_invalid_content_type(self):
        FakeOllama.response_type = "text/html"
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_STREAM_CONTENT_TYPE"):
            self.run_chat()

    def test_accepts_json_stream_content_type(self):
        FakeOllama.response_type = "application/json; charset=utf-8"
        self.assertEqual(self.run_chat()[-1]["text"], "Hello world")

    def test_rejects_truncated_stream_without_complete(self):
        FakeOllama.lines = [packet("Partial", done=False)]
        events = []
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_STREAM_TRUNCATED"):
            for event in chat.stream_chat(
                    model="qwen3:1.7b",
                    messages=[{"role": "user", "content": "hi"}],
                    endpoint=self.endpoint):
                events.append(event)
        self.assertEqual(events[-1]["event"], "DELTA")
        self.assertNotIn("COMPLETE", [e["event"] for e in events])

    def test_rejects_tool_call_even_when_server_ignores_disabled_tools(self):
        FakeOllama.lines = [packet(message={
            "role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": "exec"}}],
        }, done=True)]
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_TOOLS_UNAUTHORIZED"):
            self.run_chat()

    def test_rejects_empty_thinking_only_response(self):
        FakeOllama.lines = [packet(message={
            "role": "assistant", "content": "", "thinking": "private trace",
        }, done=True)]
        with self.assertRaisesRegex(chat.ChatRefusal, "OLLAMA_EMPTY_RESPONSE"):
            self.run_chat()

    def test_thinking_field_never_leaks_to_events(self):
        FakeOllama.lines = [
            packet("Hi", message={"role": "assistant", "content": "Hi",
                                  "thinking": "private internal trace"},
                   done=True)]
        response = json.dumps(self.run_chat())
        self.assertNotIn("private internal trace", response)
        self.assertIn("Hi", response)

    def test_refuses_invalid_json_duplicate_fields_and_nan(self):
        for line in (b"garbage\n", b'{"done":false,"done":true}\n',
                     b'{"done":NaN}\n', b"\xff\n"):
            with self.subTest(line=line[:30]):
                FakeOllama.lines = [line]
                with self.assertRaisesRegex(chat.ChatRefusal,
                                            "INVALID_STREAM_JSON"):
                    self.run_chat()

    def test_refuses_missing_done_wrong_role_and_non_text_content(self):
        for line in (b'{"message":{"role":"assistant","content":"Hi"}}\n',
                     packet("x", message={"role": "system", "content": "x"}),
                     packet("x", message={"role": "assistant", "content": 25})):
            with self.subTest(line=line[:30]):
                FakeOllama.lines = [line]
                with self.assertRaisesRegex(chat.ChatRefusal,
                                            "OLLAMA_STREAM_SCHEMA"):
                    self.run_chat()

    def test_refuses_oversize_line_or_total_response(self):
        FakeOllama.lines = [b"x" * (chat.MAX_CHUNK_BYTES + 4) + b"\n"]
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_STREAM_LINE_LIMIT"):
            self.run_chat()
        FakeOllama.lines = [
            packet("a" * 3000) for _ in range(15)
        ] + [packet(done=True)]
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_OUTPUT_TOO_LARGE"):
            self.run_chat()

    def test_success_requires_real_done_not_just_a_server_close(self):
        FakeOllama.lines = []
        with self.assertRaisesRegex(chat.ChatRefusal,
                                    "OLLAMA_STREAM_TRUNCATED"):
            self.run_chat()

    def test_generator_can_be_cancelled_without_complete(self):
        generator = chat.stream_chat(
            model="qwen3:1.7b",
            messages=[{"role": "user", "content": "hi"}],
            endpoint=self.endpoint)
        self.assertEqual(next(generator)["event"], "STARTED")
        generator.close()
        self.assertEqual(len(FakeOllama.observed), 1)

    def test_pre_cancelled_or_invalid_event_never_dispatches(self):
        token = threading.Event()
        token.set()
        with self.assertRaisesRegex(chat.ChatRefusal, "OLLAMA_CANCELLED"):
            self.run_chat(cancel_event=token)
        with self.assertRaisesRegex(chat.ChatRefusal, "INVALID_CANCEL_EVENT"):
            self.run_chat(cancel_event=True)
        self.assertEqual(FakeOllama.observed, [])

    def _stalled_exchange(self, *, headers, cancel):
        reached = threading.Event()
        release = threading.Event()
        token = threading.Event()
        events = []
        errors = []

        class Stalled(FakeOllama):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                try:
                    if headers:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-ndjson")
                        self.end_headers()
                        self.wfile.write(packet("partial"))
                        self.wfile.write(b'{"message":')
                        self.wfile.flush()
                    reached.set()
                    release.wait(5)
                except OSError:
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Stalled)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]

        def consume():
            try:
                events.extend(chat.stream_chat(
                    model="qwen3:1.7b", endpoint=endpoint,
                    messages=[{"role": "user", "content": "public fixture"}],
                    cancel_event=token))
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=consume, daemon=True)
        try:
            worker.start()
            self.assertTrue(reached.wait(2), "fixture did not receive request")
            if cancel:
                token.set()
            worker.join(2)
            self.assertFalse(worker.is_alive(), "blocked exchange not interrupted")
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], chat.ChatRefusal)
            self.assertEqual(errors[0].code, "OLLAMA_CANCELLED" if cancel
                             else "OLLAMA_STREAM_DEADLINE")
            self.assertNotIn("COMPLETE", [e["event"] for e in events])
        finally:
            release.set()
            worker.join(7)
            server.shutdown()
            server.server_close()
            serving.join(2)

    def test_cancel_interrupts_wait_for_headers(self):
        self._stalled_exchange(headers=False, cancel=True)

    def test_cancel_interrupts_partial_line(self):
        self._stalled_exchange(headers=True, cancel=True)
        # A separate operation must still succeed.
        self.assertEqual(self.run_chat()[-1]["event"], "COMPLETE")

    def test_deadline_interrupts_blocked_read_before_socket_timeout(self):
        with patch.object(chat, "TOTAL_SECONDS", 0.5):
            self._stalled_exchange(headers=True, cancel=False)

    def test_cancel_after_delta_prevents_complete(self):
        token = threading.Event()
        generator = chat.stream_chat(
            model="qwen3:1.7b",
            messages=[{"role": "user", "content": "hi"}],
            endpoint=self.endpoint, cancel_event=token)
        try:
            self.assertEqual(next(generator)["event"], "STARTED")
            self.assertEqual(next(generator)["event"], "DELTA")
            token.set()
            with self.assertRaisesRegex(chat.ChatRefusal, "OLLAMA_CANCELLED"):
                next(generator)
        finally:
            generator.close()

    def test_stop_isolates_overlapping_chunked_exchanges(self):
        # Both requests use one server and one model. Distinct connections
        # and host-owned tokens are the only cancellation boundary here.
        tokens = {key: threading.Event() for key in ("A", "B")}
        received = {key: threading.Event() for key in tokens}
        started = {key: threading.Event() for key in tokens}
        release = threading.Event()
        events = {key: [] for key in tokens}
        errors = {key: [] for key in tokens}

        class Chunked(FakeOllama):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                data = json.loads(self.rfile.read(
                    int(self.headers["Content-Length"])))
                key = data["messages"][-1]["content"]

                def chunk(data):
                    self.wfile.write(("%x\\r\\n" % len(data)).encode()
                                     + data + b"\\r\\n")
                    self.wfile.flush()

                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    chunk(packet(key + " partial"))
                    received[key].set()
                    if release.wait(5):
                        chunk(packet(" complete", done=True))
                        self.wfile.write(b"0\\r\\n\\r\\n")
                        self.wfile.flush()
                except OSError:
                    pass
                finally:
                    self.close_connection = True

        server = ThreadingHTTPServer(("127.0.0.1", 0), Chunked)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]

        def consume(key):
            try:
                for event in chat.stream_chat(
                        model="qwen3:1.7b", endpoint=endpoint,
                        messages=[{"role": "user", "content": key}],
                        cancel_event=tokens[key]):
                    events[key].append(event)
                    if event["event"] == "DELTA":
                        started[key].set()
            except Exception as exc:
                errors[key].append(exc)

        workers = {key: threading.Thread(target=consume, args=(key,),
                                         daemon=True) for key in tokens}
        before = {t.ident for t in threading.enumerate()
                  if t.name == "forest-b2-watch"}
        try:
            for worker in workers.values():
                worker.start()
            for key in tokens:
                self.assertTrue(received[key].wait(2))
                self.assertTrue(started[key].wait(2))
            tokens["A"].set()
            workers["A"].join(2)
            self.assertFalse(workers["A"].is_alive())
            self.assertEqual(len(errors["A"]), 1)
            self.assertIsInstance(errors["A"][0], chat.ChatRefusal)
            self.assertEqual(errors["A"][0].code, "OLLAMA_CANCELLED")
            self.assertNotIn("COMPLETE", [e["event"] for e in events["A"]])
            self.assertTrue(workers["B"].is_alive())
            self.assertFalse(tokens["B"].is_set())
            release.set()
            workers["B"].join(2)
            self.assertFalse(workers["B"].is_alive())
            self.assertEqual(errors["B"], [])
            self.assertEqual(events["B"][-1]["text"], "B partial complete")
            self.assertEqual(events["B"][-1]["event"], "COMPLETE")
            after = {t.ident for t in threading.enumerate()
                     if t.name == "forest-b2-watch"}
            self.assertEqual(after, before)
        finally:
            release.set()
            for worker in workers.values():
                if worker.ident is not None:
                    worker.join(7)
            server.shutdown()
            server.server_close()
            serving.join(2)

    def test_cancel_after_final_packet_delta_prevents_complete(self):
        FakeOllama.lines = [packet("final", done=True)]
        token = threading.Event()
        generator = chat.stream_chat(
            model="qwen3:1.7b",
            messages=[{"role": "user", "content": "hi"}],
            endpoint=self.endpoint, cancel_event=token)
        try:
            self.assertEqual(next(generator)["event"], "STARTED")
            self.assertEqual(next(generator)["event"], "DELTA")
            token.set()
            with self.assertRaisesRegex(chat.ChatRefusal, "OLLAMA_CANCELLED"):
                next(generator)
        finally:
            generator.close()

    def test_cli_streams_json_and_does_not_require_user_files(self):
        input_stream = io.StringIO("hello")
        output_stream = io.StringIO()
        with contextlib.redirect_stdout(output_stream):
            previous_stdin = sys.stdin
            try:
                sys.stdin = input_stream
                code = chat.main(["chat", "--model", "qwen3:1.7b",
                                  "--prompt-stdin", "--endpoint", self.endpoint])
            finally:
                sys.stdin = previous_stdin
        events = [json.loads(s) for s in output_stream.getvalue().splitlines()]
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["event"], "COMPLETE")
        self.assertEqual(events[-1]["text"], "Hello world")


if __name__ == "__main__":
    unittest.main()
