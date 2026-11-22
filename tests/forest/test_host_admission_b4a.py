"""Forest B4a synthetic host admission tests. No sockets, credentials or Ollama."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import host_admission_b4a as b4  # noqa: E402
import session_journal_v0 as b1  # noqa: E402
import turn_bridge_b3 as b3  # noqa: E402


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b4a-synthetic-")
        self.db = sqlite3.connect(Path(self.temp.name) / "fixture.db")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        session = self.journal.create_session("owner_a", "CHERRY", "Synthetic", now_ms=100)
        self.session_id = session["session_id"]
        self.journal.append_turn("owner_a", self.session_id, expected_revision=0,
                                 role="user", body="Synthetic prompt", now_ms=101)
        self.peer = b4.KernelPeer(pid=12345, uid=1000, gid=1000)
        self.now = 200
        self.allowed = {"READ_SESSION", "GENERATE"}
        self.verified_calls = []
        self.policy_calls = []
        self.generated_calls = []
        self.identity = "owner_a"
        self.valid_until_delta = 2000
        self.verify_failure = None
        self.policy_failure = None

        def verified(peer, now_ms):
            self.verified_calls.append((peer, now_ms))
            if self.verify_failure is not None:
                raise self.verify_failure
            return b4.VerifiedCaller(
                owner_key=self.identity,
                peer_pid=peer.pid, peer_uid=peer.uid,
                valid_until_ms=now_ms + self.valid_until_delta)

        def policy(principal, action, session_id, model, now_ms):
            self.policy_calls.append((principal, action, session_id, model, now_ms))
            if self.policy_failure is not None:
                raise self.policy_failure
            return action in self.allowed

        def model_streamer(*, model, messages, **kwargs):
            self.generated_calls.append((model, messages))
            yield {"event": "STARTED", "provider": "ollama", "model": model}
            yield {"event": "DELTA", "text": "Synthetic reply"}
            yield {"event": "COMPLETE", "provider": "ollama",
                   "model": model, "text": "Synthetic reply"}

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: self.now, streamer=model_streamer)
        self.admission = b4.ForestHostAdmission(
            self.journal, self.bridge, clock_ms=lambda: self.now,
            verified_peer=verified, approved_intent=policy)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def intent(self, action="READ_SESSION", **overrides):
        request = {"schema": b4.SCHEMA, "action": action,
                   "requestId": "test_request_123456789",
                   "sessionId": self.session_id}
        if action == "GENERATE":
            request.update({"model": "qwen3:1.7b", "expectedRevision": 1})
        request.update(overrides)
        return json.dumps(request, separators=(",", ":")).encode()

    def read(self, wire=None, peer=None):
        return self.admission.read_session(
            wire if wire is not None else self.intent(),
            peer=self.peer if peer is None else peer)

    def generate(self, wire=None, peer=None):
        return list(self.admission.generate(
            wire if wire is not None else self.intent("GENERATE"),
            peer=self.peer if peer is None else peer))

    def test_read_only_receipt_exposes_no_title_body_owner_or_token(self):
        reply = self.read()
        self.assertEqual(reply["status"], "READ_ONLY")
        self.assertEqual(reply["session"]["tree_key"], "CHERRY")
        self.assertEqual(reply["session"]["revision"], 1)
        self.assertEqual(self.policy_calls[0][1], "READ_SESSION")
        self.assertNotIn("Synthetic prompt", repr(reply))
        self.assertNotIn("Synthetic", repr(reply))
        self.assertNotIn("owner_a", repr(reply))
        self.assertNotIn("access_token", repr(reply))

    def test_generation_requires_trusted_peer_and_model_permission(self):
        events = self.generate()
        self.assertEqual([e["event"] for e in events],
                         ["RESERVED", "STARTED", "DELTA", "COMMITTED"])
        self.assertEqual(events[-1]["text"], "Synthetic reply")
        self.assertEqual(len(self.generated_calls), 1)
        self.assertEqual(self.policy_calls[0][1], "GENERATE")
        self.assertEqual(self.policy_calls[0][3], "qwen3:1.7b")
        self.assertEqual(self.journal.session("owner_a", self.session_id)["revision"], 2)

    def test_client_supplied_owner_key_is_a_forbidden_extra_field(self):
        malicious = self.intent(ownerKey="owner_b")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "INVALID_INTENT"):
            self.read(malicious)
        self.assertEqual(self.verified_calls, [])
        self.assertEqual(self.policy_calls, [])

    def test_client_supplied_consent_claims_or_tool_commands_are_forbidden(self):
        for field, value in (("approved", True), ("peerUid", 1000),
                             ("command", "rm"), ("body", "please run"),
                             ("token", "fake"), ("seat", "seat0")):
            with self.subTest(field=field):
                with self.assertRaisesRegex(b4.AdmissionRefusal, "INVALID_INTENT"):
                    self.generate(self.intent("GENERATE", **{field: value}))
        self.assertEqual(self.generated_calls, [])
        self.assertEqual(self.verified_calls, [])

    def test_unknown_or_unverified_peer_denied(self):
        for peer in (b4.KernelPeer(pid=0, uid=1000, gid=1000),
                     b4.KernelPeer(pid=123, uid=-1, gid=1000),
                     b4.KernelPeer(pid=True, uid=1000, gid=1000),
                     "unverified"):
            with self.subTest(peer=repr(peer)):
                with self.assertRaisesRegex(
                        b4.AdmissionRefusal, "PEER_EVIDENCE_REQUIRED"):
                    self.read(peer=peer)
        self.assertEqual(self.policy_calls, [])

    def test_verifier_refusal_and_raised_error_fail_closed(self):
        self.valid_until_delta = 0
        with self.assertRaisesRegex(b4.AdmissionRefusal, "CALLER_UNVERIFIED"):
            self.read()
        self.valid_until_delta = 2000
        self.verify_failure = RuntimeError("private token")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TRUST_UNAVAILABLE"):
            self.read()
        self.assertEqual(self.policy_calls, [])

    def test_expiry_outside_lease_refused(self):
        for delta in (-20, 0, 300001):
            self.valid_until_delta = delta
            with self.subTest(delta=delta):
                with self.assertRaisesRegex(b4.AdmissionRefusal,
                                            "CALLER_UNVERIFIED"):
                    self.read()
        self.assertEqual(self.policy_calls, [])

    def test_host_authorized_owner_scope_does_not_leak_other_session(self):
        self.identity = "owner_b"
        with self.assertRaisesRegex(b4.AdmissionRefusal, "SESSION_UNAVAILABLE"):
            self.read()
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.generate()
        self.assertEqual(self.generated_calls, [])
        self.assertEqual(len(self.journal.turns("owner_a", self.session_id)), 1)

    def test_permission_gate_denies_by_default_and_never_reaches_model(self):
        self.allowed.clear()
        with self.assertRaisesRegex(b4.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.read()
        with self.assertRaisesRegex(b4.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.generate()
        self.assertEqual(self.generated_calls, [])
        self.assertEqual(self.journal.session("owner_a", self.session_id)["revision"], 1)

    def test_policy_failure_does_not_log_sensitive_message(self):
        self.policy_failure = ValueError("a private secret")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "POLICY_UNAVAILABLE") as error:
            self.generate()
        self.assertNotIn("a private secret", str(error.exception))
        self.assertEqual(self.generated_calls, [])

    def test_strict_action_separation(self):
        with self.assertRaisesRegex(b4.AdmissionRefusal, "INVALID_ACTION"):
            self.read(self.intent("GENERATE"))
        with self.assertRaisesRegex(b4.AdmissionRefusal, "INVALID_ACTION"):
            self.generate(self.intent("READ_SESSION"))
        self.assertEqual(self.policy_calls, [])

    def test_invalid_json_duplicate_fields_utf8_and_size_refused(self):
        for wire in (
            b"{}", b"\xff",
            b'{"action":"READ_SESSION","action":"GENERATE"}',
            b"x" * 1537,
            b'{"action":NaN}',
        ):
            with self.subTest(wire=wire[:24]):
                with self.assertRaises(b4.AdmissionRefusal):
                    self.read(wire)
        self.assertEqual(self.policy_calls, [])

    def test_extra_fields_and_schema_version_refused_before_callbacks(self):
        for wire in (self.intent(schema="wrong"),
                     self.intent(requestId="x"),
                     self.intent(sessionId="../bad"),
                     self.intent("GENERATE", expectedRevision=True),
                     self.intent("GENERATE", model="invalid model"),
                     self.intent("GENERATE", expectedRevision=-1),
                     self.intent("GENERATE", model=None)):
            with self.subTest(wire=wire[:70]):
                with self.assertRaises(b4.AdmissionRefusal):
                    self.generate(wire)
        self.assertEqual(self.policy_calls, [])
        self.assertEqual(self.generated_calls, [])

    def test_unauthorized_call_does_not_write_attempt(self):
        self.allowed = {"READ_SESSION"}
        with self.assertRaisesRegex(b4.AdmissionRefusal, "NOT_AUTHORIZED"):
            self.generate()
        result = self.db.execute(
            "SELECT COUNT(*) FROM forest_attempts_b3"
        ).fetchone()[0]
        self.assertEqual(result, 0)

    def test_cancellation_leaves_b3_aborted_attempt_without_retry(self):
        generator = self.admission.generate(
            self.intent("GENERATE"), peer=self.peer)
        self.assertEqual(next(generator)["event"], "RESERVED")
        generator.close()
        result = self.db.execute(
            "SELECT status FROM forest_attempts_b3"
        ).fetchone()[0]
        self.assertEqual(result, "ABORTED")
        with self.assertRaisesRegex(b4.AdmissionRefusal, "TURN_UNAVAILABLE"):
            self.generate()
        self.assertEqual(self.generated_calls, [])

    def test_host_dependencies_are_mandatory(self):
        with self.assertRaisesRegex(b4.AdmissionRefusal, "HOST_DEPENDENCY_MISSING"):
            b4.ForestHostAdmission(self.journal, self.bridge,
                clock_ms=lambda: self.now, verified_peer=None,
                approved_intent=lambda *args: True)

    def test_no_listener_or_user_database_opener_present(self):
        src = (Path(__file__).resolve().parents[2] /
               "scripts/forest/host_admission_b4a.py").read_text()
        for forbidden in ("socket.socket(", "socketserver", "subprocess",
                          "sqlite3.connect(", "os.makedirs", "HospitalRoom",
                          "Qml", "Quickshell", "open("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
