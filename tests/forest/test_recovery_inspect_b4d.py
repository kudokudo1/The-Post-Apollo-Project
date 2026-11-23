"""Forest B4d // synthetic read-only recovery/status contract tests.

Temporary SQLite only. The peer verifier and issuer fence are fake and grant
no installed Linux, C5, user consent, or production authority.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import host_admission_b4a as host
import recovery_inspect_b4d as recovery
import session_journal_v0 as b1
import turn_bridge_b3 as b3


def fake_stream(*, model, messages, **ignored):
    yield {"event": "STARTED", "model": model, "provider": "ollama"}
    yield {"event": "DELTA", "text": "secret fake assistant reply"}
    yield {"event": "COMPLETE", "model": model, "provider": "ollama",
           "text": "secret fake assistant reply"}


class SyntheticPermit:
    def __init__(self, binding, *, acknowledge):
        self.binding = binding
        self.acknowledge = acknowledge

    def __enter__(self):
        return self

    def terminal(self, result):
        return self.acknowledge

    def __exit__(self, exc_type, exc, traceback):
        return False


class ReadOnlyRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b4d-recovery-fixture-")
        self.path = Path(self.temp.name) / "synthetic.db"
        self.db = sqlite3.connect(self.path, timeout=2)
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.session = self.journal.create_session(
            "owner_a", "CHERRY", "private synthetic title", now_ms=100)["session_id"]
        self.journal.append_turn(
            "owner_a", self.session, expected_revision=0, role="user",
            body="private synthetic user prompt", now_ms=101)
        self.peer = host.KernelPeer(pid=4455, uid=1000, gid=1000)
        self.owner = "owner_a"
        self.allowed = {"INSPECT_ATTEMPT", "GENERATE"}
        self.actions = []
        self.model_calls = 0
        self.now = 200

        def verify(peer, now):
            return host.VerifiedCaller(
                owner_key=self.owner, peer_pid=peer.pid, peer_uid=peer.uid,
                valid_until_ms=now + 2000)

        def policy(principal, action, session, model, now):
            self.actions.append(action)
            return action in self.allowed

        def streamer(**kwargs):
            self.model_calls += 1
            yield from fake_stream(**kwargs)

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: self.now, streamer=streamer)
        self.host = host.ForestHostAdmission(
            self.journal, self.bridge, clock_ms=lambda: self.now,
            verified_peer=verify, approved_intent=policy)
        self.inspector = recovery.ForestLocalRecoveryInspector(self.journal)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def reserve(self, *, owner="owner_a", session=None):
        attempt, messages = self.bridge._reserve(
            owner, session or self.session, 1, "qwen3:1.7b")
        self.assertTrue(messages)
        return attempt

    def status_wire(self, attempt_id, **overrides):
        wire = {
            "schema": host.SCHEMA, "action": "INSPECT_ATTEMPT",
            "requestId": "forest_recovery_request_12345",
            "sessionId": self.session, "attemptId": attempt_id,
        }
        wire.update(overrides)
        return json.dumps(wire, separators=(",", ":")).encode()

    def inspect(self, attempt_id, *, wire=None, peer=None):
        return self.host.inspect_attempt(
            wire if wire is not None else self.status_wire(attempt_id),
            peer=self.peer if peer is None else peer)

    def generate(self, *, acknowledge=True):
        # Two-phase fixture with a deliberately untrusted in-process permit.
        fenced_host = host.ForestHostAdmission(
            self.journal, self.bridge, clock_ms=lambda: self.now,
            verified_peer=lambda peer, now: host.VerifiedCaller(
                owner_key=self.owner, peer_pid=peer.pid, peer_uid=peer.uid,
                valid_until_ms=now + 2000),
            approved_intent=lambda *args: True,
            synthetic_fence_factory=lambda principal, binding: SyntheticPermit(
                binding, acknowledge=acknowledge),
        )
        wire = json.dumps({
            "schema": host.SCHEMA, "action": "GENERATE",
            "requestId": "forest_generate_request_1234",
            "sessionId": self.session, "model": "qwen3:1.7b",
            "expectedRevision": 1,
        }).encode()
        events = []
        try:
            for event in fenced_host.generate(wire, peer=self.peer):
                events.append(event)
        except host.AdmissionRefusal as exc:
            return events, exc.code
        return events, None

    def test_read_only_reserved_without_launching_model(self):
        attempt = self.reserve()
        before = self.db.total_changes
        report = self.inspect(attempt)
        self.assertEqual(report["status"], "LOCAL_RECOVERY_ONLY")
        data = report["recovery"]
        self.assertEqual(data["forestWriteState"], "FOREST_RESERVED")
        self.assertEqual(data["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(data["safeToRetryInference"])
        self.assertFalse(data["safeToReleaseRevocation"])
        self.assertFalse(data["c5EvidenceAuthenticated"])
        self.assertFalse(data["productionAuthority"])
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.model_calls, 0)
        self.assertEqual(self.actions, ["INSPECT_ATTEMPT"])

    def test_read_only_aborted_does_not_claim_issuer_settled(self):
        attempt = self.reserve()
        self.bridge._abort(attempt)
        report = self.inspect(attempt)["recovery"]
        self.assertEqual(report["forestWriteState"], "FOREST_ABORTED")
        self.assertEqual(report["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(report["terminalReceiptAuthenticated"])
        self.assertFalse(report["safeToRetryInference"])

    def test_committed_local_still_c5_unknown_even_after_test_ack(self):
        events, err = self.generate(acknowledge=True)
        self.assertIsNone(err)
        self.assertEqual(events[-1]["event"], "COMMITTED")
        attempt = events[0]["attempt_id"]
        data = self.inspect(attempt)["recovery"]
        self.assertEqual(data["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(data["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(data["terminalReceiptAuthenticated"])
        self.assertFalse(data["safeToReleaseRevocation"])
        self.assertEqual(self.model_calls, 1)

    def test_lost_terminal_ack_retains_local_committed_but_unsettled(self):
        events, error = self.generate(acknowledge=False)
        self.assertEqual(error, "TURN_UNAVAILABLE")
        self.assertNotIn("COMMITTED", [x["event"] for x in events])
        attempt = events[0]["attempt_id"]
        report = self.inspect(attempt)["recovery"]
        self.assertEqual(report["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(report["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(report["safeToRetryInference"])
        self.assertEqual(self.model_calls, 1)
        events2, err2 = self.generate(acknowledge=False)
        self.assertEqual(err2, "TURN_UNAVAILABLE")
        self.assertEqual(self.model_calls, 1)

    def test_unknown_attempt_cannot_disclose_owner_or_session(self):
        with self.assertRaisesRegex(host.AdmissionRefusal,
                                    "ATTEMPT_UNAVAILABLE") as absent:
            self.inspect("a_missing")
        self.owner = "owner_b"
        attempt = self.reserve()
        with self.assertRaisesRegex(host.AdmissionRefusal,
                                    "ATTEMPT_UNAVAILABLE") as other_owner:
            self.inspect(attempt)
        self.assertEqual(str(absent.exception), str(other_owner.exception))

    def test_wrong_session_refuses_same_as_unknown_attempt(self):
        attempt = self.reserve()
        other = self.journal.create_session(
            "owner_a", "MAPLE", "different session", now_ms=101)
        with self.assertRaisesRegex(host.AdmissionRefusal,
                                    "ATTEMPT_UNAVAILABLE"):
            self.inspect(attempt, wire=self.status_wire(
                attempt, sessionId=other["session_id"]))

    def test_inspect_policy_is_separate_from_generate_or_read(self):
        attempt = self.reserve()
        self.allowed = {"GENERATE", "READ_SESSION"}
        with self.assertRaisesRegex(host.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.inspect(attempt)
        self.assertEqual(self.actions, ["INSPECT_ATTEMPT"])
        self.assertEqual(self.model_calls, 0)

    def test_policy_or_peer_unavailable_does_not_read_rows(self):
        attempt = self.reserve()
        self.owner = "owner_b"
        self.allowed.clear()
        with self.assertRaisesRegex(host.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.inspect(attempt)
        with self.assertRaisesRegex(host.AdmissionRefusal,
                                    "PEER_EVIDENCE_REQUIRED"):
            self.inspect(attempt, peer=host.KernelPeer(pid=0, uid=1000, gid=1000))

    def test_request_rejects_caller_credentials_and_fake_settlement(self):
        attempt = self.reserve()
        for injected in ({"ownerKey": "owner_a"}, {"token": "secret"},
                         {"issuerSettlement": "CONFIRMED"},
                         {"safeToRetryInference": True},
                         {"proof": {"sig": "fake"}},
                         {"model": "qwen3:1.7b"}):
            with self.subTest(fields=injected):
                with self.assertRaisesRegex(host.AdmissionRefusal,
                                            "INVALID_INTENT"):
                    self.inspect(attempt, wire=self.status_wire(
                        attempt, **injected))
        self.assertEqual(self.actions, [])

    def test_wrong_action_and_request_grammar_refused_before_policy(self):
        attempt = self.reserve()
        frames = [
            self.status_wire(attempt, schema="wrong"),
            self.status_wire(attempt, requestId="x"),
            self.status_wire(attempt, attemptId="../wrong"),
            self.status_wire(attempt, action="READ_SESSION"),
            self.status_wire(attempt, action="GENERATE"),
            b'{"schema":"post-apollo.forest.host-intent.experimental-b4a",'
            b'"action":"INSPECT_ATTEMPT","attemptId":"a_test",'
            b'"requestId":"forest_recovery_request_12345",'
            b'"sessionId":"s_x","attemptId":"a_replay"}',
        ]
        for wire in frames:
            with self.subTest(wire=wire[:80]):
                with self.assertRaises(host.AdmissionRefusal):
                    self.inspect(attempt, wire=wire)
        self.assertEqual(self.actions, [])

    def test_local_result_never_contains_prompt_reply_title_or_owner(self):
        events, err = self.generate()
        self.assertIsNone(err)
        reply = self.inspect(events[0]["attempt_id"])
        serialized = json.dumps(reply)
        for secret in ("private synthetic user prompt",
                       "secret fake assistant reply",
                       "private synthetic title", "owner_a",
                       "qwen3:1.7b", "CHERRY"):
            self.assertNotIn(secret, serialized)

    def test_repeated_read_is_idempotent_and_does_not_update_revision(self):
        attempt = self.reserve()
        changes = self.db.total_changes
        before = self.journal.session("owner_a", self.session)["revision"]
        first = self.inspect(attempt)
        second = self.inspect(attempt)
        self.assertEqual(first, second)
        self.assertEqual(self.db.total_changes, changes)
        self.assertEqual(
            self.journal.session("owner_a", self.session)["revision"], before)

    def test_read_only_sqlite_connection_succeeds_without_write_access(self):
        attempt = self.reserve()
        db = sqlite3.connect(
            "file:" + str(self.path) + "?mode=ro", uri=True)
        try:
            db.execute("PRAGMA query_only=ON")
            journal = b1.ForestSessionJournal(db)
            report = recovery.ForestLocalRecoveryInspector(journal).inspect(
                owner="owner_a", session_id=self.session, attempt_id=attempt)
            self.assertEqual(report["forestWriteState"], "FOREST_RESERVED")
            self.assertFalse(report["productionAuthority"])
        finally:
            db.close()

    def test_durable_reopen_preserves_local_observation(self):
        events, error = self.generate(acknowledge=False)
        self.assertEqual(error, "TURN_UNAVAILABLE")
        attempt = events[0]["attempt_id"]
        self.db.close()
        self.db = sqlite3.connect(self.path)
        journal = b1.ForestSessionJournal(self.db)
        report = recovery.ForestLocalRecoveryInspector(journal).inspect(
            owner="owner_a", session_id=self.session, attempt_id=attempt)
        self.assertEqual(report["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(report["c5Settlement"], "UNKNOWN_HOLD")

    def test_corrupted_local_reply_reference_is_integrity_hold(self):
        attempt = self.reserve()
        # Foreign-key integrity is enabled. Simulate a logically invalid
        # committed attempt pointing to an existing USER rather than an
        # assistant reply; physical FK constraints remain intact.
        user_turn_id = self.journal.turns(
            "owner_a", self.session)[0]["turn_id"]
        self.db.execute(
            "UPDATE forest_attempts_b3 SET status='COMMITTED',"
            "reply_turn_id=? WHERE attempt_id=?", (user_turn_id, attempt))
        self.db.commit()
        with self.assertRaisesRegex(recovery.RecoveryRefusal,
                                    "LOCAL_INTEGRITY_HOLD"):
            self.inspector.inspect(
                owner="owner_a", session_id=self.session,
                attempt_id=attempt)
        with self.assertRaisesRegex(host.AdmissionRefusal,
                                    "ATTEMPT_UNAVAILABLE"):
            self.inspect(attempt)

    def test_missing_attempt_table_never_bootstraps_or_migrates(self):
        test_db = sqlite3.connect(":memory:")
        try:
            b1.bootstrap_synthetic(test_db)
            with self.assertRaisesRegex(recovery.RecoveryRefusal,
                                        "ATTEMPT_SCHEMA_MISSING"):
                recovery.ForestLocalRecoveryInspector(
                    b1.ForestSessionJournal(test_db))
            self.assertIsNone(test_db.execute(
                "SELECT name FROM sqlite_master WHERE name='forest_attempts_b3'"
            ).fetchone())
        finally:
            test_db.close()

    def test_fails_closed_if_attempt_row_is_malformed(self):
        attempt = self.reserve()
        # An ABORTED attempt must not reference any reply, even an
        # existing row satisfying SQLite's foreign-key constraint.
        user_turn_id = self.journal.turns(
            "owner_a", self.session)[0]["turn_id"]
        self.db.execute(
            "UPDATE forest_attempts_b3 SET status='ABORTED',"
            "reply_turn_id=? WHERE attempt_id=?", (user_turn_id, attempt))
        self.db.commit()
        with self.assertRaisesRegex(recovery.RecoveryRefusal,
                                    "LOCAL_INTEGRITY_HOLD"):
            self.inspector.inspect(
                owner="owner_a", session_id=self.session, attempt_id=attempt)

    def test_no_network_model_execution_or_c5_authority_in_inspector(self):
        source = (Path(__file__).resolve().parents[2] /
                  "scripts/forest/recovery_inspect_b4d.py").read_text()
        for forbidden in ("sqlite3.connect(", "socket.", "http.client",
                          "subprocess", "ollama_chat_transport", "ForestC5AuthorityBoundary",
                          "os.open(", "INSERT INTO", "UPDATE forest",
                          "DELETE FROM", "/api/chat"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
