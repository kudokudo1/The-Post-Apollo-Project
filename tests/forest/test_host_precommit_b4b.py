"""Forest B4b // synthetic pre-COMMIT revocation and identity continuity tests."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import session_journal_v0 as b1  # noqa: E402
import turn_bridge_b3 as b3  # noqa: E402
import host_admission_b4a as b4  # noqa: E402


class RecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b4b-synthetic-")
        self.db = sqlite3.connect(Path(self.temp.name) / "synthetic.db")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        sess = self.journal.create_session("owner_a", "CHERRY", "fixture", now_ms=100)
        self.sid = sess["session_id"]
        self.journal.append_turn(
            "owner_a", self.sid, expected_revision=0,
            role="user", body="synthetic prompt", now_ms=101)
        self.peer = b4.KernelPeer(pid=8765, uid=1000, gid=1000)
        self.now = 200
        self.owner = "owner_a"
        self.pid = 8765
        self.uid = 1000
        self.lease_until = 500
        self.allowed = True
        self.verify_error = None
        self.policy_error = None
        self.verify_count = 0
        self.policy_count = 0
        self.inference_count = 0
        self.interrupt_after_delta = None
        self.interrupt_after_complete = None
        self.commit_observation = None

        def verify(peer, now):
            self.verify_count += 1
            if self.verify_error:
                raise self.verify_error
            return b4.VerifiedCaller(owner_key=self.owner, peer_pid=self.pid,
                                     peer_uid=self.uid,
                                     valid_until_ms=self.lease_until)

        def policy(principal, action, session, model, now):
            self.policy_count += 1
            if self.policy_error:
                raise self.policy_error
            return self.allowed

        def fake_streamer(*, model, messages, **kwargs):
            self.inference_count += 1
            yield {"event": "STARTED", "provider": "ollama", "model": model}
            yield {"event": "DELTA", "text": "synthetic reply"}
            if self.interrupt_after_delta:
                self.interrupt_after_delta()
            yield {"event": "COMPLETE", "provider": "ollama",
                   "model": model, "text": "synthetic reply"}
            if self.interrupt_after_complete:
                self.interrupt_after_complete()

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: self.now,
            streamer=fake_streamer)
        self.host = b4.ForestHostAdmission(
            self.journal, self.bridge, clock_ms=lambda: self.now,
            verified_peer=verify, approved_intent=policy)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def wire(self):
        return json.dumps({
            "schema": b4.SCHEMA, "action": "GENERATE",
            "requestId": "forest_test_b4b_123456",
            "sessionId": self.sid, "model": "qwen3:1.7b",
            "expectedRevision": 1
        }, separators=(",", ":")).encode("utf-8")

    def events(self):
        return list(self.host.generate(self.wire(), peer=self.peer))

    def status(self):
        return self.db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 "
            "WHERE session_id=?", (self.sid,)
        ).fetchone()

    def assert_unsaved(self):
        self.assertEqual(self.status(), ("ABORTED", None))
        self.assertEqual(self.journal.session("owner_a", self.sid)["revision"], 1)
        self.assertEqual(
            [t["role"] for t in self.journal.turns("owner_a", self.sid)], ["user"])

    def test_valid_initial_and_precommit_checks_allow_single_durable_reply(self):
        events = self.events()
        self.assertEqual([e["event"] for e in events],
                         ["RESERVED", "STARTED", "DELTA", "COMMITTED"])
        self.assertEqual(self.verify_count, 2)
        self.assertEqual(self.policy_count, 2)
        self.assertEqual(self.inference_count, 1)
        self.assertEqual(self.status()[0], "COMMITTED")
        self.assertEqual(self.journal.session("owner_a", self.sid)["revision"], 2)
        self.assertEqual(self.journal.turns("owner_a", self.sid)[-1]["body"],
                         "synthetic reply")

    def test_revoke_after_delta_prevents_final_database_commit(self):
        generator = self.host.generate(self.wire(), peer=self.peer)
        self.assertEqual(next(generator)["event"], "RESERVED")
        self.assertEqual(next(generator)["event"], "STARTED")
        self.assertEqual(next(generator)["event"], "DELTA")
        self.allowed = False
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            list(generator)
        self.assert_unsaved()
        self.assertEqual(self.policy_count, 2)

    def test_loss_of_permission_on_last_stream_packet_refuses_save(self):
        self.interrupt_after_complete = lambda: setattr(self, "allowed", False)
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()

    def test_host_owner_swap_rejected_even_if_new_owner_policy_passes(self):
        self.interrupt_after_complete = lambda: setattr(self, "owner", "owner_b")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()
        self.assertEqual(self.verify_count, 2)

    def test_verified_pid_drift_rejected_at_final_check(self):
        self.interrupt_after_complete = lambda: setattr(self, "pid", 8766)
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()

    def test_verified_uid_drift_rejected_at_final_check(self):
        self.interrupt_after_complete = lambda: setattr(self, "uid", 1001)
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()

    def test_expired_host_lease_rejected_at_final_check(self):
        self.interrupt_after_complete = lambda: setattr(self, "now", 501)
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()

    def test_verifier_crash_after_inference_fails_closed(self):
        self.interrupt_after_complete = lambda: setattr(
            self, "verify_error", RuntimeError("sensitive host details"))
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE") as e:
            self.events()
        self.assertNotIn("sensitive host details", str(e.exception))
        self.assert_unsaved()

    def test_policy_crash_after_inference_fails_closed(self):
        self.interrupt_after_complete = lambda: setattr(
            self, "policy_error", RuntimeError("sensitive policy details"))
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()

    def test_precommit_hook_is_inside_transaction_before_insert(self):
        def observe():
            row = self.status()
            self.commit_observation = (
                self.db.in_transaction, row,
                len(self.journal.turns("owner_a", self.sid)))
            return True

        events = list(self.bridge.exchange(
            owner="owner_a", session_id=self.sid,
            expected_revision=1, model="qwen3:1.7b",
            pre_commit=observe))
        self.assertEqual(events[-1]["event"], "COMMITTED")
        self.assertEqual(self.commit_observation,
                         (True, ("RESERVED", None), 1))

    def test_precommit_false_and_truthy_nonboolean_refuse(self):
        for answer in (False, None, 1, "yes"):
            with self.subTest(answer=answer):
                # Each subtest uses a distinct synthetic session+turn.
                sess = self.journal.create_session(
                    "owner_a", "MAPLE", "temp", now_ms=100)
                sid = sess["session_id"]
                self.journal.append_turn(
                    "owner_a", sid, expected_revision=0,
                    role="user", body="test", now_ms=101)
                with self.assertRaisesRegex(
                        b3.BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED"):
                    list(self.bridge.exchange(
                        owner="owner_a", session_id=sid,
                        expected_revision=1, model="qwen3:1.7b",
                        pre_commit=lambda: answer))
                row = self.db.execute(
                    "SELECT status FROM forest_attempts_b3 WHERE session_id=?",
                    (sid,)).fetchone()
                self.assertEqual(row[0], "ABORTED")
                self.assertEqual(len(self.journal.turns("owner_a", sid)), 1)

    def test_precommit_hook_exception_fails_without_leaking_it(self):
        def broken():
            raise RuntimeError("private session details")
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED") as e:
            list(self.bridge.exchange(
                owner="owner_a", session_id=self.sid,
                expected_revision=1, model="qwen3:1.7b",
                pre_commit=broken))
        self.assertNotIn("private session details", str(e.exception))
        self.assert_unsaved()

    def test_noncallable_precommit_refuses_before_reservation(self):
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "INVALID_PRE_COMMIT_HOOK"):
            list(self.bridge.exchange(
                owner="owner_a", session_id=self.sid,
                expected_revision=1, model="qwen3:1.7b",
                pre_commit=True))
        self.assertIsNone(self.status())
        self.assertEqual(self.inference_count, 0)

    def test_cancellation_does_not_fire_precommit_hook(self):
        gen = self.host.generate(self.wire(), peer=self.peer)
        next(gen)
        next(gen)
        next(gen)
        gen.close()
        self.assert_unsaved()
        self.assertEqual(self.verify_count, 1)
        self.assertEqual(self.policy_count, 1)

    def test_refusal_must_not_trigger_reinference(self):
        self.interrupt_after_complete = lambda: setattr(self, "allowed", False)
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assert_unsaved()
        self.allowed = True
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.events()
        self.assertEqual(self.inference_count, 1)

    def test_failed_authorization_does_not_resurface_completed_output(self):
        self.interrupt_after_complete = lambda: setattr(self, "allowed", False)
        gen = self.host.generate(self.wire(), peer=self.peer)
        observed = []
        with self.assertRaises(b4.AdmissionRefusal):
            for event in gen:
                observed.append(event)
        self.assertIn("DELTA", [e["event"] for e in observed])
        self.assertNotIn("COMMITTED", [e["event"] for e in observed])
        self.assert_unsaved()


if __name__ == "__main__":
    unittest.main()
