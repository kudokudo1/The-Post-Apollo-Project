"""Actual FL3 owner host with disposable transports; no installed model."""
import sqlite3
import sys
import threading
import unittest
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import first_light_trial_host as fl
from ollama_chat_transport import stream_chat
from runtime_events_r3 import RuntimeEventRefusal
from test_ollama_chat_transport import FakeOllama, packet


class FirstLightHostTests(unittest.TestCase):
    def peer(self, lines):
        class Peer(FakeOllama):
            pass
        Peer.lines = lines
        Peer.observed = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.addCleanup(close)
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]

        def transport(**kw):
            # Only the test adapter substitutes the ephemeral peer endpoint.
            # Actual B2 encoding/streaming is exercised, not native custody.
            kw["endpoint"] = endpoint
            yield from stream_chat(**kw)
        return Peer, transport

    def test_fixed_public_exact_request_and_one_original_commit(self):
        peer, transport = self.peer([packet("RE"), packet("ADY", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        self.addCleanup(lambda: None if host._closed else host.close())
        with self.assertRaisesRegex(fl.FirstLightRefusal, "PUBLIC_INPUT_MISMATCH"):
            host.submit("other text")
        self.assertEqual(peer.observed, [])
        op = host.submit(fl.PROMPT)
        self.assertEqual(host.phase, "PREPARED")
        self.assertEqual(peer.observed, [])
        with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
            host.submit(fl.PROMPT)
        frames = list(host.run_internal())
        self.assertEqual([f.payload["event"] for f in frames],
                         ["REQUESTED", "RESERVED", "STARTED", "DELTA",
                          "DELTA", "COMMITTED"])
        self.assertTrue(all(f.operation == op for f in frames))
        self.assertEqual(frames[-1].payload["text"], "READY")
        self.assertEqual(peer.observed, [("POST", "/api/chat", {
            "model": fl.MODEL, "messages": [{"role": "user", "content": fl.PROMPT}],
            "stream": True, "options": {"num_predict": 32, "num_ctx": 2048}})])
        self.assertEqual(host.local_outcome(), "COMMITTED_LOCAL")
        self.assertEqual(host.phase, "LOCAL_COMMITTED")
        with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
            list(host.run_internal())
        self.assertEqual(host.close(), "COMMITTED_LOCAL")
        self.assertEqual(len(peer.observed), 1)

    def test_original_stop_and_local_abort_are_not_provider_settlement(self):
        peer, transport = self.peer([packet("partial"), packet(" more", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        op = host.submit(fl.PROMPT)
        gen = host.run_internal()
        try:
            for event in ("REQUESTED", "RESERVED", "STARTED", "DELTA"):
                frame = next(gen)
                self.assertEqual(frame.payload["event"], event)
            with self.assertRaisesRegex(RuntimeEventRefusal, "OPERATION_MISMATCH"):
                host.request_stop(replace(op, operation_id="other"), frame.attempt_id)
            self.assertEqual(host.request_stop(op, frame.attempt_id), "STOP_LATCHED")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "ORIGINAL_ACTIVE"):
                host.close()
            self.assertEqual(list(gen)[-1].payload["event"], "UNKNOWN_HOLD")
            self.assertEqual(host.phase, "UNKNOWN_HOLD")
            self.assertEqual(host.local_outcome(), "ABORTED_LOCAL")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                list(host.run_internal())
            self.assertEqual(len(peer.observed), 1)
        finally:
            gen.close()
            self.assertEqual(host.close(), "ABORTED_LOCAL")
        self.assertEqual(host.phase, "UNKNOWN_HOLD")

    def test_extra_turn_refused_before_body_read_or_transport(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        op = host.submit(fl.PROMPT)
        host._db.execute(
            "INSERT INTO forest_turns VALUES (?,?,?,?,?,?,?,?)",
            ("extra", op.context_ref.session_id, 2, "user", "", "", "extra", 3))
        host._db.commit()
        reads = []

        def authorizer(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table == "forest_turns" and column == "body":
                reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        host._db.set_authorizer(authorizer)
        try:
            self.assertEqual(list(host.run_internal())[-1].payload["event"], "UNKNOWN_HOLD")
            self.assertEqual(reads, [])
            self.assertEqual(calls, [])
            self.assertEqual(host.local_outcome(), "UNKNOWN_HOLD")
        finally:
            host._db.set_authorizer(None)
            host.close()

    def test_changed_prompt_same_metadata_refused_before_transport(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        op = host.submit(fl.PROMPT)
        host._db.execute("UPDATE forest_turns SET body=? WHERE turn_id=?",
                         ("changed", op.context_ref.user_turn_id))
        host._db.commit()
        try:
            self.assertEqual(list(host.run_internal())[-1].payload["event"], "UNKNOWN_HOLD")
            self.assertEqual(calls, [])
            self.assertEqual(host.local_outcome(), "ABORTED_LOCAL")
        finally:
            host.close()

    def test_worker_close_early_does_not_allow_retry(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        host.submit(fl.PROMPT)
        gen = host.run_internal()
        try:
            self.assertEqual(next(gen).payload["event"], "REQUESTED")
            self.assertEqual(next(gen).payload["event"], "RESERVED")
            gen.close()
            self.assertEqual(host.phase, "UNKNOWN_HOLD")
            self.assertEqual(host.local_outcome(), "ABORTED_LOCAL")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                host.submit(fl.PROMPT)
            self.assertEqual(calls, [])
        finally:
            gen.close()
            host.close()


if __name__ == "__main__":
    unittest.main()
