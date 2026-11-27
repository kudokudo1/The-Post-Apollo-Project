"""FL5 actual owner delivery path; disposable B2 peer, no native grants."""
import sys
import json
import subprocess
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
from first_light_delivery import FirstLightDelivery, DeliveryRefusal
from first_light_trial_host import PROMPT
import test_first_light_trial_host as host_tests
from test_ollama_chat_transport import packet


class DeliveryTests(unittest.TestCase):
    peer = host_tests.FirstLightHostTests.peer

    def setup_trial(self, lines):
        peer, transport = self.peer(lines)
        d = FirstLightDelivery(test_transport=transport)
        self.addCleanup(d.close)
        view = object()
        d.observe_view(view)
        d.submit(view, PROMPT)
        return d, view, peer

    def finish(self, d):
        for _ in range(12):
            if d.owner_outcome()[0] in ("LOCAL_COMMITTED", "UNKNOWN_HOLD"):
                return
            d.advance()
        self.fail("trial did not finish")

    def test_actual_public_response_one_row_and_terminal_after_exhaustion(self):
        d, view, peer = self.setup_trial([packet("RE"), packet("ADY", done=True)])
        prepared = d.take(view)
        self.assertEqual(prepared.status, "PREPARED")
        self.assertFalse(prepared.native_admitted)
        self.assertIsNone(d.take(view))
        for _ in range(4):
            d.advance()
        partial = d.take(view)
        self.assertEqual((partial.text, partial.status, partial.provisional),
                         ("RE", "GENERATING", True))
        self.assertGreater(partial.sequence, prepared.sequence)
        self.finish(d)
        final = d.take(view)
        self.assertEqual((final.text, final.status, final.provisional, final.local_outcome),
                         ("READY", "LOCAL_COMMITTED", False, "COMMITTED_LOCAL"))
        self.assertFalse(final.native_admitted)
        self.assertGreater(final.sequence, partial.sequence)
        self.assertIsNone(d.take(view))
        self.assertEqual(len(peer.observed), 1)
        with self.assertRaisesRegex(DeliveryRefusal, "SUBMIT_UNAVAILABLE"):
            d.submit(view, PROMPT)

    def test_queued_delta_withdrawal_and_aba_do_not_retarget_original(self):
        d, view, peer = self.setup_trial([packet("first"), packet(" last", done=True)])
        for _ in range(4):
            d.advance()
        replacement = object()
        d.observe_view(replacement)
        self.assertIsNone(d.take(view))
        self.assertIsNone(d.take(replacement))
        self.assertEqual(d.request_stop(replacement), "STOP_UNAVAILABLE")
        d.observe_view(view)
        self.assertIsNone(d.take(view))
        self.assertEqual(d.request_stop(view), "STOP_UNAVAILABLE")
        self.finish(d)
        self.assertEqual(d.owner_outcome(), ("LOCAL_COMMITTED", "COMMITTED_LOCAL"))
        self.assertIsNone(d.take(view))
        self.assertEqual(len(peer.observed), 1)

    def test_stop_is_separate_from_original_local_terminal(self):
        d, view, peer = self.setup_trial([packet("partial"), packet(" more", done=True)])
        for _ in range(4):
            d.advance()
        self.assertEqual(d.request_stop(view), "STOP_LATCHED")
        stop = d.take(view)
        self.assertEqual((stop.status, stop.local_outcome, stop.provisional),
                         ("STOP_REQUESTED", "UNKNOWN_HOLD", True))
        self.finish(d)
        final = d.take(view)
        self.assertEqual((final.status, final.local_outcome, final.text),
                         ("UNKNOWN_HOLD", "ABORTED_LOCAL", ""))
        self.assertEqual(len(peer.observed), 1)
        self.assertEqual(d.request_stop(view), "STOP_UNAVAILABLE")

    def test_foreign_worker_cannot_advance_or_close(self):
        d, view, peer = self.setup_trial([packet("READY", done=True)])
        rejected = []

        def foreign():
            for action in (d.advance, d.close):
                try:
                    action()
                except DeliveryRefusal as exc:
                    rejected.append(str(exc))

        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(rejected, ["OWNER_ACTION_UNAVAILABLE"] * 2)
        self.assertEqual(peer.observed, [])
        self.finish(d)
        self.assertEqual(d.take(view).status, "LOCAL_COMMITTED")

    def test_recycled_numeric_identity_cannot_take_over_delivery(self):
        d, view, peer = self.setup_trial([packet("READY", done=True)])
        original = threading.current_thread()
        self.assertIs(d._owner_thread, original)
        with patch("first_light_delivery.threading.current_thread", return_value=object()):
            for action in (d.advance, d.close, d.owner_outcome):
                with self.assertRaisesRegex(DeliveryRefusal, "OWNER_ACTION_UNAVAILABLE"):
                    action()
        self.assertEqual(peer.observed, [])
        self.finish(d)
        self.assertEqual(d.take(view).status, "LOCAL_COMMITTED")

    def child_commands(self, commands):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("first_light_delivery_child.py"))],
            input="".join(json.dumps(c) + "\n" for c in commands),
            capture_output=True, text=True, timeout=15, check=True)
        self.assertEqual(result.stderr, "")
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_actual_child_control_snapshot_and_no_retarget(self):
        commands = [
            {"op": "OBSERVE", "epoch": 1, "visible": True},
            {"op": "SUBMIT", "epoch": 1, "prompt": "wrong"},
            {"op": "SUBMIT", "epoch": 1, "prompt": PROMPT},
            {"op": "TAKE", "epoch": 1},
            *[{"op": "STEP"} for _ in range(4)],
            {"op": "TAKE", "epoch": 1},
            {"op": "OBSERVE", "epoch": 2, "visible": False},
            {"op": "OBSERVE", "epoch": 3, "visible": True},
            {"op": "TAKE", "epoch": 1},
            {"op": "TAKE", "epoch": 3},
            {"op": "STOP", "epoch": 3},
            {"op": "STEP"}, {"op": "STEP"}, {"op": "OUTCOME"},
            {"op": "TAKE", "epoch": 3}, {"op": "CLOSE"},
        ]
        replies = self.child_commands(commands)
        self.assertEqual(len(replies), len(commands))
        self.assertFalse(replies[1]["ok"])
        self.assertEqual(replies[3]["snapshot"]["status"], "PREPARED")
        partial = replies[8]
        self.assertEqual(partial["epoch"], 1)
        self.assertEqual(partial["snapshot"]["text"], "RE")
        self.assertTrue(partial["snapshot"]["provisional"])
        self.assertFalse(partial["snapshot"]["native_admitted"])
        self.assertEqual(set(partial["snapshot"]),
                         {"sequence", "status", "text", "local_outcome",
                          "provisional", "native_admitted"})
        self.assertFalse(replies[11]["ok"])
        self.assertIsNone(replies[12]["snapshot"])
        self.assertEqual(replies[13]["ack"], "STOP_UNAVAILABLE")
        self.assertEqual(replies[16]["status"], "LOCAL_COMMITTED")
        self.assertIsNone(replies[17]["snapshot"])
        self.assertEqual(replies[18]["local_outcome"], "COMMITTED_LOCAL")

    def test_actual_child_contextual_stop_and_terminal(self):
        commands = [
            {"op": "OBSERVE", "epoch": 1, "visible": True},
            {"op": "SUBMIT", "epoch": 1, "prompt": PROMPT},
            *[{"op": "STEP"} for _ in range(4)],
            {"op": "STOP", "epoch": 1}, {"op": "TAKE", "epoch": 1},
            {"op": "STEP"}, {"op": "TAKE", "epoch": 1}, {"op": "CLOSE"},
        ]
        replies = self.child_commands(commands)
        self.assertEqual(replies[6]["ack"], "STOP_LATCHED")
        self.assertEqual(replies[7]["snapshot"]["status"], "STOP_REQUESTED")
        self.assertEqual(replies[9]["snapshot"]["status"], "UNKNOWN_HOLD")
        self.assertEqual(replies[9]["snapshot"]["local_outcome"], "ABORTED_LOCAL")
        self.assertEqual(replies[9]["snapshot"]["text"], "")
        self.assertEqual(replies[10]["local_outcome"], "ABORTED_LOCAL")

    def test_independent_control_stops_actual_blocked_b2_read(self):
        from first_light_delivery_child import OwnerWorker, Control, ControlRefusal
        from test_ollama_chat_transport import FakeOllama
        from ollama_chat_transport import stream_chat

        blocked = threading.Event()
        release = threading.Event()
        observed = []

        class Peer(FakeOllama):
            def do_POST(self):
                size = int(self.headers["Content-Length"])
                observed.append(json.loads(self.rfile.read(size)))
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.end_headers()
                    self.wfile.write(packet("partial"))
                    self.wfile.flush()
                    blocked.set()
                    release.wait(8)
                    self.wfile.write(packet(" later", done=True))
                    self.wfile.flush()
                except OSError:
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        peer_thread = threading.Thread(target=server.serve_forever, daemon=True)
        peer_thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]

        def transport(**kw):
            kw["endpoint"] = endpoint
            yield from stream_chat(**kw)

        owner = OwnerWorker(transport)
        control = Control(owner)
        try:
            control.command({"op": "OBSERVE", "epoch": 1, "visible": True})
            control.command({"op": "SUBMIT", "epoch": 1, "prompt": PROMPT})
            for _ in range(4):
                control.command({"op": "STEP"})
            self.assertTrue(blocked.wait(2))
            partial = control.command({"op": "TAKE", "epoch": 1})["snapshot"]
            self.assertEqual(partial["text"], "partial")
            control.command({"op": "STEP_BEGIN"})
            self.assertFalse(control.command({"op": "STEP_POLL"})["done"])
            for op in ("STEP", "STEP_BEGIN", "OUTCOME", "CLOSE"):
                with self.assertRaises(ControlRefusal):
                    control.command({"op": op})
            self.assertEqual(control.command({"op": "STOP", "epoch": 1})["ack"],
                             "STOP_LATCHED")
            # Peer has not completed/released its response. Cancellation
            # must interrupt B2 independently of the blocked owner read.
            owner.pending.result(timeout=3)
            self.assertFalse(release.is_set())
            self.assertTrue(control.command({"op": "STEP_POLL"})["done"])
            final = control.command({"op": "TAKE", "epoch": 1})["snapshot"]
            self.assertEqual((final["status"], final["local_outcome"], final["text"]),
                             ("UNKNOWN_HOLD", "ABORTED_LOCAL", ""))
            self.assertEqual(len(observed), 1)
            self.assertFalse(final["native_admitted"])
            self.assertEqual(control.command({"op": "CLOSE"})["local_outcome"],
                             "ABORTED_LOCAL")
        finally:
            release.set()
            owner.dispose()
            server.shutdown()
            server.server_close()
            peer_thread.join(timeout=2)

    def test_wrong_prompt_is_unknown_not_admission_or_retry(self):
        calls = []
        d = FirstLightDelivery(test_transport=lambda **kw: calls.append(kw))
        self.addCleanup(d.close)
        view = object()
        d.observe_view(view)
        d.submit(view, "other")
        s = d.take(view)
        self.assertEqual((s.status, s.text, s.native_admitted),
                         ("UNKNOWN_HOLD", "", False))
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(DeliveryRefusal, "SUBMIT_UNAVAILABLE"):
            d.submit(view, PROMPT)


if __name__ == "__main__":
    unittest.main()
