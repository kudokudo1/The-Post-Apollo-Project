#!/usr/bin/env python3
"""DOC 3 // Provisional Forest DELTA disclosure can precede C5 terminal refusal.

This tests the real (UNCHANGED) Forest B3/B4f synthetic writer with disposable
SQLite and a fake model stream. It demonstrates a confidentiality/consent
ordering question, NOT a live disclosure, policy approval or native authority.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/forest"))
import session_journal_v0 as b1
import turn_bridge_b3 as b3
import local_terminal_outbox_b4f as b4f

SECRET = "SYNTHETIC_PRIVATE_PROVISIONAL_TEXT"
REQUEST = "forest_c5_stream_test_request_0001"


class FakePermit:
    """In-process fixture, NOT a protected C5 permit or native issuer."""
    def __init__(self, binding, *, result=True, raises=False):
        self.binding = binding
        self.result = result
        self.raises = raises
        self.called = 0

    def __enter__(self):
        return self

    def terminal(self, _reply):
        self.called += 1
        if self.raises:
            raise RuntimeError("synthetic terminal transport unavailable")
        return self.result

    def __exit__(self, *_):
        return False


class ForestC5StreamingDisclosureNegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="forest-c5-stream-negative-")
        self.db = sqlite3.connect(Path(self.tmp.name) / "synthetic.sqlite")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        b4f.bootstrap_local_terminal_outbox_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.session = self.journal.create_session(
            "principal_a", "CHERRY", "SYNTHETIC_PRIVATE_TITLE", now_ms=100)["session_id"]
        self.user = self.journal.append_turn(
            "principal_a", self.session, expected_revision=0,
            role="user", body="SYNTHETIC_PRIVATE_QUESTION", now_ms=101)["turn_id"]
        self.model_calls = 0
        self.before_commit = 0
        self.revoke = False
        self.stream_mode = "complete"
        self.permits = []

        def fake_model_stream(*, model, messages, **_):
            self.model_calls += 1
            self.assertEqual(model, "qwen3:1.7b")
            self.assertEqual(messages[-1]["content"], "SYNTHETIC_PRIVATE_QUESTION")
            yield {"event": "STARTED", "provider": "ollama", "model": model}
            yield {"event": "DELTA", "text": SECRET}
            if self.stream_mode == "incomplete":
                return
            if self.stream_mode == "invalid_complete":
                yield {"event": "COMPLETE", "provider": "ollama",
                       "model": model, "text": "DIFFERENT"}
            else:
                yield {"event": "COMPLETE", "provider": "ollama",
                       "model": model, "text": SECRET}

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: 200,
            streamer=fake_model_stream, synthetic_terminal_outbox=True)
        self.inspector = b4f.ForestLocalTerminalOutboxInspector(self.journal)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def final_policy(self):
        self.before_commit += 1
        return not self.revoke

    def exchange(self, **kwargs):
        return self.bridge.exchange(
            owner="principal_a", session_id=self.session,
            expected_revision=1, model="qwen3:1.7b", **kwargs)

    def consume(self, **kwargs):
        shown = []
        error = None
        try:
            for item in self.exchange(**kwargs):
                shown.append(item)
        except b3.BridgeRefusal as exc:
            error = exc.code
        return shown, error

    def attempt(self):
        return self.db.execute(
            "SELECT attempt_id,status,reply_turn_id FROM forest_attempts_b3 "
            "WHERE session_id=?", (self.session,)).fetchone()

    def outbox(self):
        attempt = self.attempt()
        if attempt is None:
            return None
        return self.inspector.inspect(
            owner="principal_a", session_id=self.session,
            attempt_id=attempt[0])

    def check_disclosed(self, shown):
        events = [item["event"] for item in shown]
        self.assertIn("DELTA", events)
        self.assertNotIn("COMMITTED", events)
        part = next(x for x in shown if x["event"] == "DELTA")
        self.assertTrue(part["provisional"])
        self.assertEqual(part["text"], SECRET)
        self.assertLess(events.index("DELTA"), len(events))

    def check_local_abort(self):
        attempt = self.attempt()
        self.assertEqual(attempt[1:], ("ABORTED", None))
        view = self.outbox()
        self.assertEqual(view["localTerminalEvent"], "LOCAL_ABORTED")
        self.assertEqual(view["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(view["safeToRetryInference"])
        self.assertFalse(view["safeToReleaseRevocation"])
        self.assertFalse(view["terminalReceiptAuthenticated"])
        self.assertEqual(len(self.journal.turns("principal_a", self.session)), 1)

    def test_01_final_policy_denied_after_provisional_text_disclosed(self):
        self.revoke = True
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error, "PRE_COMMIT_AUTHORIZATION_DENIED")
        self.check_disclosed(shown)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 1)

    def test_02_revocation_after_first_delta_still_cannot_retract_it(self):
        stream = self.exchange(pre_commit=self.final_policy)
        seen = [next(stream), next(stream), next(stream)]
        self.assertEqual(seen[-1]["event"], "DELTA")
        self.assertEqual(self.before_commit, 0)
        self.revoke = True
        with self.assertRaisesRegex(b3.BridgeRefusal,
                                     "PRE_COMMIT_AUTHORIZATION_DENIED"):
            seen.extend(stream)
        self.check_disclosed(seen)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 1)

    def test_03_generator_cancel_after_delta_aborts_db_not_disclosure(self):
        stream = self.exchange(pre_commit=self.final_policy)
        shown = [next(stream), next(stream), next(stream)]
        stream.close()
        self.check_disclosed(shown)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 0)

    def test_04_incomplete_model_after_delta_aborts_no_retraction(self):
        self.stream_mode = "incomplete"
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error, "INCOMPLETE_STREAM")
        self.check_disclosed(shown)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 0)

    def test_05_invalid_complete_after_delta_aborts_no_retraction(self):
        self.stream_mode = "invalid_complete"
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error, "INVALID_STREAM_COMPLETION")
        self.check_disclosed(shown)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 0)

    def test_06_lost_terminal_ack_after_commit_disclosed_delta_no_confirmation(self):
        def permit(binding):
            obj = FakePermit(binding, result=False)
            self.permits.append(obj)
            return obj
        shown, error = self.consume(
            pre_commit=self.final_policy, fence_factory=permit,
            fence_request_id=REQUEST)
        self.assertEqual(error, "UNKNOWN_HOLD")
        self.check_disclosed(shown)
        attempt = self.attempt()
        self.assertEqual(attempt[1], "COMMITTED")
        self.assertIsNotNone(attempt[2])
        self.assertEqual(self.outbox()["localTerminalEvent"], "LOCAL_COMMITTED")
        self.assertEqual(self.outbox()["c5Settlement"], "UNKNOWN_HOLD")
        self.assertEqual(self.permits[0].called, 1)
        self.assertFalse(self.outbox()["safeToRetryInference"])

    def test_07_terminal_transport_exception_after_commit_same_unknown(self):
        def permit(binding):
            obj = FakePermit(binding, raises=True)
            self.permits.append(obj)
            return obj
        shown, error = self.consume(
            pre_commit=self.final_policy, fence_factory=permit,
            fence_request_id=REQUEST)
        self.assertEqual(error, "UNKNOWN_HOLD")
        self.check_disclosed(shown)
        self.assertEqual(self.attempt()[1], "COMMITTED")
        self.assertEqual(self.outbox()["c5Settlement"], "UNKNOWN_HOLD")

    def test_08_permit_acquisition_refused_after_delta_leaves_abort(self):
        def refuse(_binding):
            raise RuntimeError("synthetic permit acquisition unavailable")
        shown, error = self.consume(
            pre_commit=self.final_policy, fence_factory=refuse,
            fence_request_id=REQUEST)
        self.assertEqual(error, "FENCE_UNAVAILABLE")
        self.check_disclosed(shown)
        self.check_local_abort()
        self.assertEqual(self.before_commit, 0)

    def test_09_even_successful_local_commit_exposes_delta_earlier(self):
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertIsNone(error)
        self.assertEqual([x["event"] for x in shown],
                         ["RESERVED", "STARTED", "DELTA", "COMMITTED"])
        self.assertTrue(shown[2]["provisional"])
        self.assertEqual(self.before_commit, 1)
        self.assertEqual(self.outbox()["localTerminalEvent"], "LOCAL_COMMITTED")
        self.assertEqual(self.outbox()["c5Settlement"], "UNKNOWN_HOLD")

    def test_10_denied_attempt_cannot_be_automatically_reexecuted(self):
        self.revoke = True
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error, "PRE_COMMIT_AUTHORIZATION_DENIED")
        self.check_disclosed(shown)
        self.check_local_abort()
        called = self.model_calls
        shown2, error2 = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error2, "ATTEMPT_ALREADY_EXISTS")
        self.assertEqual(shown2, [])
        self.assertEqual(self.model_calls, called)

    def test_11_outbox_is_private_text_free_even_after_disclosure(self):
        self.revoke = True
        shown, error = self.consume(pre_commit=self.final_policy)
        self.assertEqual(error, "PRE_COMMIT_AUTHORIZATION_DENIED")
        self.check_disclosed(shown)
        view = self.outbox()
        for value in ("SYNTHETIC_PRIVATE_TITLE", "SYNTHETIC_PRIVATE_QUESTION", SECRET):
            self.assertNotIn(value, str(view))
        self.assertNotIn("body", view)
        self.assertNotIn("reply", view)

    def test_12_final_commit_check_runs_after_delta_yield_not_before(self):
        stream = self.exchange(pre_commit=self.final_policy)
        self.assertEqual(next(stream)["event"], "RESERVED")
        self.assertEqual(next(stream)["event"], "STARTED")
        delta = next(stream)
        self.assertEqual(delta["event"], "DELTA")
        self.assertEqual(self.before_commit, 0)
        self.revoke = True
        with self.assertRaisesRegex(b3.BridgeRefusal,
                                     "PRE_COMMIT_AUTHORIZATION_DENIED"):
            next(stream)
        self.assertEqual(self.before_commit, 1)
        self.check_local_abort()


if __name__ == "__main__":
    unittest.main()
