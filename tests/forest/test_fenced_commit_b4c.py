"""Forest B4c: disposable two-store held-permit consumer tests.

All issuer/caller/consent/receipt evidence is deliberately forgeable.
This demonstrates Forest-side ordering ONLY. It grants no real authority.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import session_journal_v0 as b1
import turn_bridge_b3 as b3
import host_admission_b4a as b4


class UntrustedPermit:
    """Fake issuer lease. Never ship this as a production C5 permit."""
    def __init__(self, issuer, binding):
        self.issuer = issuer
        self.binding = binding
        self.finished = False

    def __enter__(self):
        self.issuer.enter_count += 1
        if self.issuer.invalid_binding:
            self.binding = "malicious-other-attempt"
        if self.issuer.revoked or self.issuer.revoking:
            raise RuntimeError("fixture grant revoked")
        self.issuer.db.execute(
            "INSERT INTO synthetic_permits(attempt_id, status) VALUES(?,?)",
            (self.binding.attempt_id if isinstance(
                self.binding, b3.SyntheticCommitBinding) else "malicious", "PENDING"))
        self.issuer.db.commit()
        if self.issuer.on_enter:
            self.issuer.on_enter()
        return self

    def terminal(self, reply):
        # This tests call ordering, not authenticated terminal proof.
        assert not self.issuer.forest_db.in_transaction
        self.issuer.terminals += 1
        actual = self.issuer.forest_db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 "
            "WHERE attempt_id=?", (self.binding.attempt_id,)).fetchone()
        if actual != ("COMMITTED", reply["turn_id"]):
            raise RuntimeError("synthetic Forest commit not observed")
        self.issuer.last_terminal = reply
        if self.issuer.terminal_crashes:
            raise RuntimeError("lost synthetic terminal ACK")
        if self.issuer.terminal_missing:
            self.issuer.db.execute(
                "UPDATE synthetic_permits SET status='UNKNOWN_HOLD' "
                "WHERE attempt_id=?", (self.binding.attempt_id,))
            self.issuer.db.commit()
            return False
        self.finished = True
        self.issuer.db.execute(
            "UPDATE synthetic_permits SET status='COMMIT_CONFIRMED' "
            "WHERE attempt_id=?", (self.binding.attempt_id,))
        self.issuer.db.commit()
        if self.issuer.revoking:
            self.issuer.revoked = True
            self.issuer.revoking = False
        return True

    def __exit__(self, exc_type, exc, tb):
        self.issuer.exit_count += 1
        if not self.finished and isinstance(self.binding, b3.SyntheticCommitBinding):
            self.issuer.db.execute(
                "UPDATE synthetic_permits SET status='UNKNOWN_HOLD' "
                "WHERE attempt_id=? AND status='PENDING'",
                (self.binding.attempt_id,))
            self.issuer.db.commit()
        if self.issuer.exit_crashes:
            raise RuntimeError("lost final fixture receipt")
        return False


class FakeTwoStoreIssuer:
    def __init__(self, forest_db, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE synthetic_permits("
                        "attempt_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        self.db.commit()
        self.forest_db = forest_db
        self.enter_count = 0
        self.exit_count = 0
        self.terminals = 0
        self.invalid_binding = False
        self.revoked = False
        self.revoking = False
        self.terminal_missing = False
        self.terminal_crashes = False
        self.exit_crashes = False
        self.on_enter = None
        self.last_binding = None
        self.last_principal = None
        self.last_terminal = None

    def factory(self, principal, binding):
        self.last_principal = principal
        self.last_binding = binding
        return UntrustedPermit(self, binding)

    def revoke(self):
        if self.db.execute(
                "SELECT COUNT(*) FROM synthetic_permits "
                "WHERE status IN ('PENDING','UNKNOWN_HOLD')").fetchone()[0]:
            self.revoking = True
            return "REVOKING"  # NOT revocation-complete
        self.revoked = True
        return "REVOKED"

    def permit_status(self):
        row = self.db.execute(
            "SELECT status FROM synthetic_permits").fetchone()
        return None if row is None else row[0]

    def close(self):
        self.db.close()


class FencedConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b4c-fence-fixture-")
        root = Path(self.temp.name)
        self.db = sqlite3.connect(root / "forest.db", timeout=2)
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.session = self.journal.create_session(
            "owner_a", "CHERRY", "synthetic", now_ms=100)["session_id"]
        self.journal.append_turn("owner_a", self.session, expected_revision=0,
                                 role="user", body="synthetic prompt", now_ms=101)
        self.issuer = FakeTwoStoreIssuer(self.db, root / "issuer.db")
        self.peer = b4.KernelPeer(pid=1008, uid=1000, gid=1000)
        self.now = 200
        self.verified_owner = "owner_a"
        self.allowed = {"PREPARE_GENERATE", "COMMIT_GENERATE"}
        self.actions = []
        self.generated = 0

        def verifier(peer, timestamp):
            return b4.VerifiedCaller(
                owner_key=self.verified_owner, peer_pid=peer.pid,
                peer_uid=peer.uid, valid_until_ms=timestamp + 1000)

        def policy(principal, action, session, model, now):
            self.actions.append(action)
            return action in self.allowed

        def streamer(*, model, messages, **kwargs):
            self.generated += 1
            yield {"event": "STARTED", "provider": "ollama", "model": model}
            yield {"event": "DELTA", "text": "synthetic answer"}
            yield {"event": "COMPLETE", "provider": "ollama",
                   "model": model, "text": "synthetic answer"}

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: self.now, streamer=streamer)
        self.host = b4.ForestHostAdmission(
            self.journal, self.bridge, clock_ms=lambda: self.now,
            verified_peer=verifier, approved_intent=policy,
            synthetic_fence_factory=self.issuer.factory)

    def tearDown(self):
        self.issuer.close()
        self.db.close()
        self.temp.cleanup()

    def wire(self, **overrides):
        frame = {"schema": b4.SCHEMA, "action": "GENERATE",
                 "requestId": "forest_b4c_request_1234",
                 "sessionId": self.session,
                 "model": "qwen3:1.7b", "expectedRevision": 1}
        frame.update(overrides)
        return json.dumps(frame).encode("utf-8")

    def run_generation(self, wire=None):
        return list(self.host.generate(
            wire if wire is not None else self.wire(), peer=self.peer))

    def forest_attempt(self):
        return self.db.execute(
            "SELECT status, reply_turn_id FROM forest_attempts_b3 "
            "WHERE session_id=?", (self.session,)).fetchone()

    def assert_no_reply(self):
        self.assertEqual([t["role"] for t in
                          self.journal.turns("owner_a", self.session)], ["user"])
        self.assertEqual(self.journal.session("owner_a", self.session)["revision"], 1)

    def test_held_permit_covers_sqlite_commit_then_terminal_ack(self):
        events = self.run_generation()
        self.assertEqual([e["event"] for e in events],
                         ["RESERVED", "STARTED", "DELTA", "COMMITTED"])
        self.assertEqual(self.actions, ["PREPARE_GENERATE", "COMMIT_GENERATE"])
        self.assertEqual(self.generated, 1)
        self.assertEqual(self.issuer.enter_count, 1)
        self.assertEqual(self.issuer.exit_count, 1)
        self.assertEqual(self.issuer.terminals, 1)
        self.assertEqual(self.issuer.permit_status(), "COMMIT_CONFIRMED")
        self.assertEqual(self.forest_attempt()[0], "COMMITTED")
        self.assertEqual(self.issuer.last_binding.attempt_id, events[0]["attempt_id"])
        self.assertEqual(self.issuer.last_binding.user_turn_id,
                         self.journal.turns("owner_a", self.session)[0]["turn_id"])
        self.assertEqual(self.issuer.last_binding.tree_key, "CHERRY")
        self.assertEqual(self.issuer.last_binding.request_id,
                         "forest_b4c_request_1234")
        self.assertEqual(self.issuer.last_binding.model_key, "qwen3:1.7b")
        self.assertEqual(self.issuer.last_binding.expected_revision, 1)

    def test_revoke_before_prepare_refuses_without_inference(self):
        self.issuer.revoke()
        self.allowed.discard("PREPARE_GENERATE")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.run_generation()
        self.assertEqual(self.generated, 0)
        self.assertIsNone(self.forest_attempt())

    def test_revoke_before_permit_refuses_even_after_provisional_delta(self):
        gen = self.host.generate(self.wire(), peer=self.peer)
        self.assertEqual(next(gen)["event"], "RESERVED")
        self.assertEqual(next(gen)["event"], "STARTED")
        self.assertEqual(next(gen)["event"], "DELTA")
        self.assertEqual(self.issuer.revoke(), "REVOKED")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            list(gen)
        self.assertEqual(self.generated, 1)
        self.assertEqual(self.forest_attempt()[0], "ABORTED")
        self.assert_no_reply()

    def test_permit_first_revocation_does_not_ack_before_terminal(self):
        observations = []

        def revoke_while_held():
            observations.append(self.issuer.revoke())
            observations.append(self.issuer.revoked)

        self.issuer.on_enter = revoke_while_held
        events = self.run_generation()
        self.assertEqual(observations, ["REVOKING", False])
        self.assertEqual(events[-1]["event"], "COMMITTED")
        self.assertEqual(self.issuer.permit_status(), "COMMIT_CONFIRMED")
        self.assertTrue(self.issuer.revoked)

    def test_loss_of_terminal_ack_keeps_unknown_and_suppresses_commit_event(self):
        self.issuer.terminal_missing = True
        visible = []
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            for event in self.host.generate(self.wire(), peer=self.peer):
                visible.append(event)
        self.assertEqual(self.forest_attempt()[0], "COMMITTED")
        self.assertEqual(self.issuer.permit_status(), "UNKNOWN_HOLD")
        self.assertNotIn("COMMITTED", [e["event"] for e in visible])
        self.assertEqual(self.generated, 1)
        with self.assertRaises(b4.AdmissionRefusal):
            self.run_generation()
        self.assertEqual(self.generated, 1)  # no inference replay

    def test_terminal_exception_after_sqlite_commit_is_unknown_hold(self):
        self.issuer.terminal_crashes = True
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.run_generation()
        self.assertEqual(self.forest_attempt()[0], "COMMITTED")
        self.assertEqual(self.issuer.permit_status(), "UNKNOWN_HOLD")

    def test_exit_exception_after_successful_receipt_not_user_confirmed(self):
        self.issuer.exit_crashes = True
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.run_generation()
        self.assertEqual(self.forest_attempt()[0], "COMMITTED")
        self.assertEqual(self.issuer.permit_status(), "COMMIT_CONFIRMED")

    def test_revoke_after_delta_before_final_policy_check_refuses_reply(self):
        gen = self.host.generate(self.wire(), peer=self.peer)
        next(gen)
        next(gen)
        next(gen)
        self.allowed.discard("COMMIT_GENERATE")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            list(gen)
        self.assertEqual(self.forest_attempt()[0], "ABORTED")
        self.assertEqual(self.issuer.permit_status(), "UNKNOWN_HOLD")
        self.assert_no_reply()

    def test_misbound_permit_attempt_fails_closed(self):
        self.issuer.invalid_binding = True
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.run_generation()
        self.assertEqual(self.generated, 1)
        self.assert_no_reply()

    def test_denied_commit_phase_keeps_prepare_and_no_final_write(self):
        self.allowed = {"PREPARE_GENERATE"}
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.run_generation()
        self.assertEqual(self.actions, ["PREPARE_GENERATE", "COMMIT_GENERATE"])
        self.assert_no_reply()

    def test_principal_swap_before_final_authorization_refuses(self):
        gen = self.host.generate(self.wire(), peer=self.peer)
        next(gen); next(gen); next(gen)
        self.verified_owner = "owner_other"
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            list(gen)
        self.assert_no_reply()

    def test_no_client_supplied_grants_in_fenced_mode(self):
        for spoof in ({"ownerKey": "owner_a"}, {"permitId": "fake"},
                      {"commitGrant": True}, {"peerPid": 1008}):
            with self.subTest(spoof=spoof):
                with self.assertRaisesRegex(
                        b4.AdmissionRefusal, "INVALID_INTENT"):
                    self.run_generation(self.wire(**spoof))
        self.assertEqual(self.generated, 0)
        self.assertIsNone(self.forest_attempt())

    def test_bad_fence_factory_denied_before_b3_attempt(self):
        with self.assertRaisesRegex(
                b4.AdmissionRefusal, "HOST_DEPENDENCY_MISSING"):
            b4.ForestHostAdmission(
                self.journal, self.bridge, clock_ms=lambda: self.now,
                verified_peer=lambda *args: None,
                approved_intent=lambda *args: True,
                synthetic_fence_factory=True)
        self.assertIsNone(self.forest_attempt())

    def test_direct_b3_invalid_fence_refuses_without_inference(self):
        for extra in ({"fence_factory": object(), "fence_request_id": "x" * 18},
                      {"fence_factory": self.issuer.factory},
                      {"fence_request_id": "x" * 18}):
            with self.subTest(extra=extra):
                with self.assertRaises(b3.BridgeRefusal):
                    list(self.bridge.exchange(
                        owner="owner_a", session_id=self.session,
                        expected_revision=1, model="qwen3:1.7b",
                        pre_commit=lambda: True, **extra))
        self.assertIsNone(self.forest_attempt())
        self.assertEqual(self.generated, 0)

    def test_different_issuer_database_does_not_prove_forest_commit(self):
        self.issuer.terminal_missing = True
        with self.assertRaises(b4.AdmissionRefusal):
            self.run_generation()
        self.assertEqual(self.issuer.permit_status(), "UNKNOWN_HOLD")
        self.assertEqual(self.forest_attempt()[0], "COMMITTED")
        # This fixture cannot independently attest cross-store outcome.
        self.assertFalse(hasattr(self.issuer, "production_authority"))


if __name__ == "__main__":
    unittest.main()
