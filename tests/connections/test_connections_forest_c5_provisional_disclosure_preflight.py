#!/usr/bin/env python3
"""DOC3 // separate provisional disclosure candidate is NEVER an issuer grant."""
from __future__ import annotations

import contextlib
import hashlib
import json
import socket
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/forest"))

from services.connections.forest import ForestC5ProvisionalDisclosurePreflight as D
from services.connections.forest import ForestC5AuthorityBoundary as C
from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5ExactSessionV1Preflight as V
import session_journal_v0 as b1
import turn_bridge_b3 as b3
import local_terminal_outbox_b4f as b4f
import ollama_chat_transport as chat
import native_host_candidate_b5b as native
from shared_context_b6r1 import TaskContext
from runtime_stop_control_r2 import RuntimeStopControl
from context_first_tree_m2 import SessionContextRef
sys.path.insert(0, str(ROOT / "tests/connections"))
from test_connections_forest_c5_provisional_delta_disclosure import FakePermit
sys.path.insert(0, str(ROOT / "tests/forest"))
from test_ollama_chat_transport import FakeOllama, packet

SECRET = "SYNTHETIC_SECRET_PROVISIONAL_1234"


class ProvisionalCandidateNegativeTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "schema": V.INTENT_SCHEMA_V1, "audience": S.AUDIENCE,
            "phase": "COMMIT_GENERATE", "action": "GENERATE",
            "principal": "alice", "tree": "treeA", "sessionId": "sessionA",
            "userTurn": "u123", "attempt": "a123", "request": "r123",
            "grant": "g123", "model": "qwen3:1.7b",
            "revision": 4, "consentEpoch": 12,
            "issuedAtMs": 900, "expiresAtMs": 1200,
            "challenge": "nonce_0123456789abcd",
            "requesterReleaseSha256": "a" * 64,
            "commitHostReleaseSha256": "b" * 64,
            "requesterPid": 2233, "requesterStartTicks": 998877,
            "requesterUid": 1000, "seatEpoch": 45,
        }
        self.commit_wire = S.canonical_bytes(self.base)
        self.candidate = self.mk_candidate(self.base, self.commit_wire)

    @staticmethod
    def mk_candidate(original, commit_wire):
        return {
            "schema": D.SCHEMA,
            "audience": D.AUDIENCE,
            "phase": D.PHASE, "action": D.PHASE,
            "commitIntentSha256": hashlib.sha256(commit_wire).hexdigest(),
            "principal": original["principal"], "tree": original["tree"],
            "sessionId": original["sessionId"], "userTurn": original["userTurn"],
            "attempt": original["attempt"], "model": original["model"],
            "revision": original["revision"],
            "consentEpoch": original["consentEpoch"],
            "disclosureRequest": "disc_request_1234567890",
            "disclosureCandidateId": "disc_candidate_1234567890",
            "disclosureNonce": "disc_nonce_1234567890",
            "disclosureEpoch": 3,
            "recipientInstance": "forest_terminal_1",
            "recipientReleaseSha256": "c" * 64,
            "recipientSeatEpoch": 45,
            "maxBytes": 16000,
            "issuedAtMs": 1000, "expiresAtMs": 1100,
        }

    def wire(self, **changes):
        return S.canonical_bytes(dict(self.candidate, **changes))

    def examine(self, wire=None, original=None, at=1000):
        return D.inspect_untrusted_disclosure_candidate(
            self.wire() if wire is None else wire,
            self.commit_wire if original is None else original, now_ms=at)

    def block(self, text=SECRET, **kwargs):
        return D.block_provisional_delta(
            self.wire(), self.commit_wire,
            {"event": "DELTA", "text": text, "provisional": True},
            now_ms=1000, **kwargs)

    def deny(self, reason, wire=None, original=None, at=1000):
        with self.assertRaises(D.DisclosureHold) as caught:
            self.examine(wire, original, at)
        self.assertIn(reason, str(caught.exception))
        self.assertNotIn(SECRET, str(caught.exception))

    def no_grant(self, x):
        self.assertEqual(x["safeActions"], [])
        for k in D.NO_AUTHORITY:
            self.assertIs(x[k], False, k)
        for item in (SECRET, "sessionA", "alice", "qwen3:1.7b"):
            self.assertNotIn(item, str(x))

    def test_01_matching_candidate_only_reports_hold(self):
        got = self.examine()
        self.assertEqual(
            got["status"],
            "CANDIDATE_MATCHES_ORIGINAL_SCOPE_NO_PROTECTED_PERMISSION_HOLD")
        self.assertTrue(got["bothWiresCallerControlled"])
        self.no_grant(got)

    def test_02_even_matching_candidate_drops_actual_delta_text(self):
        result = self.block()
        self.assertIsNone(result["emitEvent"])
        self.assertEqual(result["emittedBytes"], 0)
        self.assertEqual(
            result["status"],
            "UNTRUSTED_DELTA_SUPPRESSED_NO_C5_DISCLOSURE_PERMISSION_HOLD")
        self.no_grant(result)

    def test_03_commit_grant_cannot_be_disclosure_action(self):
        self.deny("WRONG_DISCLOSURE_DOMAIN_OR_ACTION",
                  self.wire(action="COMMIT_GENERATE"))
        self.deny("WRONG_DISCLOSURE_DOMAIN_OR_ACTION",
                  self.wire(phase="COMMIT_GENERATE"))

    def test_04_commit_v1_wire_itself_not_accepted_as_disclosure(self):
        self.deny("INVALID_CANDIDATE_WIRE", self.commit_wire)

    def test_05_alien_audience_not_accepted(self):
        self.deny("WRONG_DISCLOSURE_DOMAIN_OR_ACTION",
                  self.wire(audience=S.AUDIENCE))

    def test_06_changed_parent_intent_digest_denied(self):
        self.deny("PARENT_COMMIT_INTENT_MISMATCH",
                  self.wire(commitIntentSha256="f" * 64))

    def test_07_exact_original_session_attempt_user_turn_scope(self):
        for name, value in (
            ("principal", "eve"), ("tree", "treeB"),
            ("sessionId", "sessionB"), ("userTurn", "u999"),
            ("attempt", "a999"), ("model", "other:model"),
            ("revision", 5), ("consentEpoch", 13),
        ):
            with self.subTest(name=name):
                self.deny("ORIGINAL_SCOPE_MISMATCH_" + name,
                          self.wire(**{name: value}))

    def test_08_modified_original_commit_requires_distinct_parent_digest(self):
        changed = dict(self.base, sessionId="otherSession")
        self.deny("PARENT_COMMIT_INTENT_MISMATCH",
                  original=S.canonical_bytes(changed))

    def test_09_original_wrong_phase_not_a_provisional_permission(self):
        changed = dict(self.base, phase="DISCLOSE_PROVISIONAL")
        self.deny("INVALID_ORIGINAL_COMMIT_INTENT",
                  original=S.canonical_bytes(changed))

    def test_10_missing_or_extra_fields_denied_not_ignored(self):
        incomplete = dict(self.candidate)
        del incomplete["recipientSeatEpoch"]
        self.deny("INVALID_CANDIDATE_WIRE", S.canonical_bytes(incomplete))
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire(permitId="p_fake"))
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire(text=SECRET))
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire(authorized=True))

    def test_11_duplicate_json_fields_denied(self):
        original = self.wire().decode("ascii")
        changed = original.replace(
            '"schema":', '"schema":"postapollo.forest.provisional-disclosure-intent.candidate-v0","schema":', 1)
        self.deny("INVALID_CANDIDATE_WIRE", changed.encode("ascii"))

    def test_12_noncanonical_json_denied(self):
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire().replace(b':', b': ', 1))

    def test_13_boolean_integer_and_negative_amount_denied(self):
        for field, value in (
            ("revision", True), ("consentEpoch", True),
            ("recipientSeatEpoch", True), ("maxBytes", True),
            ("maxBytes", 0), ("disclosureEpoch", 0),
            ("issuedAtMs", -1),
        ):
            with self.subTest(field=field, value=value):
                if field in ("revision", "consentEpoch"):
                    self.deny("ORIGINAL_SCOPE_MISMATCH_" + field,
                              self.wire(**{field: value}))
                else:
                    self.deny("INVALID_" + field,
                              self.wire(**{field: value}))

    def test_14_unbounded_candidate_bytes_denied(self):
        self.deny("UNBOUNDED_CANDIDATE_OUTPUT",
                  self.wire(maxBytes=D.MAX_CANDIDATE_BYTES + 1))

    def test_15_candidate_expired_or_not_yet_current_denied(self):
        self.deny("CANDIDATE_NOT_CURRENT", at=1100)
        self.deny("CANDIDATE_NOT_CURRENT", at=999)

    def test_16_disclosure_cannot_extend_commit_lease(self):
        self.deny("DISCLOSURE_CANNOT_EXTEND_ORIGINAL_COMMIT_LEASE",
                  self.wire(expiresAtMs=1201))
        self.deny("DISCLOSURE_CANNOT_EXTEND_ORIGINAL_COMMIT_LEASE",
                  self.wire(issuedAtMs=899))

    def test_17_zero_length_or_oversized_lease_denied(self):
        self.deny("INVALID_CANDIDATE_LEASE",
                  self.wire(expiresAtMs=1000))
        self.deny("INVALID_CANDIDATE_LEASE",
                  self.wire(issuedAtMs=1000, expiresAtMs=500000))

    def test_18_disclosure_ids_cannot_reuse_commit_grant_or_request(self):
        for field, value in (
            ("disclosureRequest", self.base["request"]),
            ("disclosureCandidateId", self.base["grant"]),
            ("disclosureNonce", self.base["challenge"]),
            ("disclosureNonce", self.candidate["disclosureRequest"]),
        ):
            with self.subTest(field=field):
                self.deny("COMMIT_AND_DISCLOSURE_IDENTIFIERS_MUST_BE_DISTINCT",
                          self.wire(**{field: value}))

    def test_19_recipient_identity_is_required_but_not_authenticated(self):
        self.deny("INVALID_RECIPIENT_RELEASE",
                  self.wire(recipientReleaseSha256="bad"))
        self.deny("INVALID_recipientInstance",
                  self.wire(recipientInstance="bad.privileged:instance"))
        self.no_grant(self.examine())

    def test_20_outstanding_revocation_is_not_in_candidate(self):
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire(revocationCleared=True))
        self.deny("INVALID_CANDIDATE_WIRE",
                  self.wire(humanConsentVerified=True))

    def test_21_untrusted_event_accepted_only_as_structural_drop(self):
        event = {"event": "DELTA", "text": SECRET, "provisional": True}
        for bad in (
            dict(event, event="COMMITTED"),
            dict(event, provisional=False),
            dict(event, text=""),
            dict(event, text=123),
            dict(event, permitId="p_fake"),
        ):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                    D.DisclosureHold, "ONLY_UNTRUSTED_PROVISIONAL_DELTA_IS_INSPECTABLE"
                ):
                    D.block_provisional_delta(
                        self.wire(), self.commit_wire, bad, now_ms=1000)

    def test_22_unpaired_surrogate_text_denied_without_echo(self):
        with self.assertRaises(D.DisclosureHold) as caught:
            self.block(text="\ud800")
        self.assertIn("INVALID_DELTA_ENCODING", str(caught.exception))

    def test_23_oversized_delta_denied_without_echo(self):
        with self.assertRaises(D.DisclosureHold) as caught:
            self.block(text=SECRET * 800)
        self.assertIn("DELTA_EXCEEDS_ABSOLUTE_SOURCE_CAP", str(caught.exception))

    def test_24_multibyte_delta_has_no_release_or_output(self):
        x = self.block(text="✅" * 100)
        self.assertIsNone(x["emitEvent"])
        self.assertEqual(x["emittedBytes"], 0)
        self.no_grant(x)

    def test_25_static_source_has_no_native_writer_or_model_actuator(self):
        source = (ROOT / "services/connections/forest/ForestC5ProvisionalDisclosurePreflight.py").read_text()
        for term in ("sqlite3.connect(", "socket.socket(", "subprocess.",
                     "Ed25519PrivateKey", "os.system(", "stream_chat(",
                     "safeToEmitProvisionalText\": True", "requests.post("):
            self.assertNotIn(term, source)
        self.assertEqual(D.PHASE, "DISCLOSE_PROVISIONAL")
        self.assertNotEqual(D.AUDIENCE, S.AUDIENCE)

    def test_26_actual_forest_b3_delta_can_be_discarded_at_untrusted_sink(self):
        # No actual external sink or real C5 permission. The B3 generator
        # already yielded to its immediate caller. Here only downstream
        # delivery is blocked. This is NOT a native policy implementation.
        with tempfile.TemporaryDirectory(prefix="doc3-disclosure-") as root:
            db = sqlite3.connect(str(Path(root) / "forest.sqlite"))
            try:
                b1.bootstrap_synthetic(db)
                b3.bootstrap_attempts_synthetic(db)
                b4f.bootstrap_local_terminal_outbox_synthetic(db)
                journal = b1.ForestSessionJournal(db)
                sid = journal.create_session(
                    "owner_a", "CHERRY", "private synthetic", now_ms=100)["session_id"]
                uid = journal.append_turn(
                    "owner_a", sid, expected_revision=0,
                    role="user", body="private synthetic question",
                    now_ms=101)["turn_id"]

                def fake_model(*, model, messages, **_):
                    self.assertEqual(messages[-1]["role"], "user")
                    yield {"event": "STARTED", "model": model, "provider": "ollama"}
                    yield {"event": "DELTA", "text": SECRET}
                    yield {"event": "COMPLETE", "model": model,
                           "provider": "ollama", "text": SECRET}

                bridge = b3.ForestTurnBridge(
                    journal, clock_ms=lambda: 200, streamer=fake_model,
                    synthetic_terminal_outbox=True)
                stream = bridge.exchange(
                    owner="owner_a", session_id=sid, expected_revision=1,
                    model="qwen3:1.7b", pre_commit=lambda: False)
                res = next(stream)
                self.assertEqual(res["event"], "RESERVED")
                self.assertEqual(next(stream)["event"], "STARTED")
                delta = next(stream)
                orig = dict(self.base, principal="owner_a", tree="CHERRY",
                            sessionId=sid, userTurn=uid, attempt=res["attempt_id"],
                            revision=1, issuedAtMs=100, expiresAtMs=300)
                iw = S.canonical_bytes(orig)
                cw = S.canonical_bytes(dict(
                    self.mk_candidate(orig, iw),
                    issuedAtMs=150, expiresAtMs=250))
                result = D.block_provisional_delta(cw, iw, delta, now_ms=200)
                self.no_grant(result)
                self.assertIsNone(result["emitEvent"])
                self.assertNotIn(SECRET, str(result))
                with self.assertRaisesRegex(
                    b3.BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED"
                ):
                    next(stream)
                status = db.execute(
                    "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?",
                    (res["attempt_id"],)).fetchone()[0]
                self.assertEqual(status, "ABORTED")
                self.assertEqual(len(journal.turns("owner_a", sid)), 1)
            finally:
                db.close()


    def test_27_invalid_delta_encoding_does_not_retain_unicode_error_chain(self):
        text = SECRET + "\ud800"
        with self.assertRaisesRegex(D.DisclosureHold, "INVALID_DELTA_ENCODING") as exc:
            self.block(text=text)
        self.assertIsNone(exc.exception.__cause__)
        self.assertIsNone(exc.exception.__context__)
        self.assertNotIn(SECRET, str(exc.exception))

    def test_28_invalid_json_refusal_does_not_retain_raw_decoder_document(self):
        malformed = ('{"private":"' + SECRET + '",').encode("ascii")
        for wire, original, reason in (
            (malformed, None, "INVALID_CANDIDATE_WIRE"),
            (None, malformed, "INVALID_ORIGINAL_COMMIT_INTENT"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(D.DisclosureHold, reason) as exc:
                    self.examine(wire=wire, original=original)
                self.assertIsNone(exc.exception.__cause__)
                self.assertIsNone(exc.exception.__context__)
                self.assertNotIn(SECRET, str(exc.exception))

    def test_29_oversize_codepoint_count_refuses_before_utf8_encoding(self):
        # An invalid surrogate at the end would raise UnicodeError if an
        # oversized value were encoded before the codepoint-count guard.
        text = "x" * D.MAX_CANDIDATE_BYTES + "\ud800"
        with self.assertRaisesRegex(
            D.DisclosureHold, "DELTA_EXCEEDS_ABSOLUTE_SOURCE_CAP"
        ):
            self.block(text=text)

    def test_30_utf8_byte_limit_preserved_after_codepoint_guard(self):
        self.no_grant(self.block(text="\u00e9" * (D.MAX_CANDIDATE_BYTES // 2)))
        with self.assertRaisesRegex(
            D.DisclosureHold, "DELTA_EXCEEDS_ABSOLUTE_SOURCE_CAP"
        ):
            self.block(text="\u00e9" * (D.MAX_CANDIDATE_BYTES // 2 + 1))



    def test_31_event_key_count_and_types_checked_before_equality(self):
        class HostileKey(str):
            armed = False
            __hash__ = str.__hash__

            def __eq__(self, other):
                if self.armed:
                    raise AssertionError("unexpected key comparison")
                return super().__eq__(other)

        key = HostileKey("event")
        event = {key: "DELTA", "text": SECRET, "provisional": True}
        key.armed = True
        oversized = {"event": "DELTA", "text": SECRET, "provisional": True}
        oversized.update({f"extra{i}": None for i in range(2048)})
        for bad in (event, oversized):
            with self.assertRaisesRegex(
                D.DisclosureHold, "ONLY_UNTRUSTED_PROVISIONAL_DELTA_IS_INSPECTABLE"
            ) as caught:
                D.block_provisional_delta(
                    self.wire(), self.commit_wire, bad, now_ms=1000)
            self.assertNotIn(SECRET, str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)

    def test_32_event_tag_rejects_custom_comparison_without_execution(self):
        class HostileTag(str):
            def __eq__(self, other):
                raise AssertionError("unexpected event tag equality")

            def __ne__(self, other):
                raise AssertionError("unexpected event tag inequality")

        for tag in (HostileTag("DELTA"), 1, None):
            with self.subTest(kind=type(tag).__name__):
                with self.assertRaisesRegex(
                    D.DisclosureHold, "ONLY_UNTRUSTED_PROVISIONAL_DELTA_IS_INSPECTABLE"
                ):
                    D.block_provisional_delta(
                        self.wire(), self.commit_wire,
                        {"event": tag, "text": SECRET, "provisional": True},
                        now_ms=1000)
        self.no_grant(self.block())



    def _exercise_existing_transport_and_hold_sender(self, *, cancel, lost_ack=False):
        """Join existing B2/B3/C5/B5b in a disposable test, not a host path."""
        class PublicFixture(FakeOllama):
            # Deliberately isolated public synthetic provider data.
            lines = [packet(SECRET, done=True)]
            observed = []

        server = ThreadingHTTPServer(("127.0.0.1", 0), PublicFixture)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with tempfile.TemporaryDirectory(prefix="doc3-first-tree-") as root:
                with contextlib.closing(sqlite3.connect(
                        str(Path(root) / "public-fixture.sqlite"))) as db:
                    b1.bootstrap_synthetic(db)
                    b3.bootstrap_attempts_synthetic(db)
                    b4f.bootstrap_local_terminal_outbox_synthetic(db)
                    journal = b1.ForestSessionJournal(db)
                    sid = journal.create_session(
                        "fixture_owner", "CHERRY", "Public fixture", now_ms=100)["session_id"]
                    uid = journal.append_turn(
                        "fixture_owner", sid, expected_revision=0, role="user",
                        body="Public synthetic question", now_ms=101)["turn_id"]
                    context = TaskContext("fixture_owner", "CHERRY", None,
                                          "fixture_task", "fixture_execution",
                                          1, "INTERACTIVE")
                    operation = "fixture_operation_1234567890"
                    control = RuntimeStopControl(context, operation)
                    attempt_id = None
                    ref = SessionContextRef(context, sid, 1, uid)
                    authority = C.ForestC5AuthorityBoundary(required_mode=C.MODE_PROTECTED)

                    def pre_commit():
                        # B3 now owns commit entry; this remains an injected
                        # synthetic B4 policy hook, not protected authority.
                        if lost_ack:
                            self.assertEqual(control.request_stop(
                                context, operation, attempt_id),
                                "COMMIT_ENTRY_ALREADY_WON")
                            self.assertFalse(control.transport_event.is_set())
                        return True

                    fences = (dict(fence_factory=lambda binding: FakePermit(binding, result=False),
                                   fence_request_id=operation) if lost_ack else {})

                    bridge = b3.ForestTurnBridge(
                        journal, clock_ms=lambda: 200, streamer=chat.stream_chat,
                        synthetic_terminal_outbox=True)
                    with contextlib.closing(bridge.exchange(
                        owner="fixture_owner", session_id=sid,
                        expected_revision=1, model="qwen3:1.7b",
                        endpoint=endpoint, pre_commit=pre_commit,
                        context_ref=ref, current_context_ref=ref,
                        resolve_current_context=lambda: ref,
                        stop_control=control, operation_id=operation, **fences
                    )) as stream:
                        res = next(stream)
                        self.assertEqual(res["event"], "RESERVED")
                        attempt_id = res["attempt_id"]
                        # Actual B3 now binds the reserved attempt itself.
                        started = next(stream)
                        self.assertEqual(started["event"], "STARTED")
                        delta = next(stream)
                        self.assertEqual(delta["text"], SECRET)
                        self.assertIs(delta["provisional"], True)
                        orig = dict(self.base, principal="fixture_owner",
                                    tree="CHERRY", sessionId=sid, userTurn=uid,
                                    attempt=res["attempt_id"], revision=1,
                                    issuedAtMs=100, expiresAtMs=300)
                        iw = S.canonical_bytes(orig)
                        cw = S.canonical_bytes(dict(
                            self.mk_candidate(orig, iw),
                            issuedAtMs=150, expiresAtMs=250))
                        result = D.block_provisional_delta(cw, iw, delta, now_ms=200)
                        self.no_grant(result)
                        self.assertIsNone(result["emitEvent"])
                        self.assertEqual(result["emittedBytes"], 0)
                        with self.assertRaisesRegex(
                            C.ForestC5Hold, "PROVISIONAL_OUTPUT_SEPARATE_PROTECTED_PERMISSION_REQUIRED"
                        ) as denied:
                            authority.authorize_disclose_provisional(delta, cw)
                        self.assertNotIn(SECRET, str(denied.exception))
                        if cancel:
                            self.assertEqual(control.request_stop(
                                context, operation, attempt_id), "STOP_LATCHED")
                            with self.assertRaisesRegex(b3.BridgeRefusal, "OLLAMA_CANCELLED"):
                                next(stream)
                            self.assertFalse(control.try_enter_commit(
                                context, operation, attempt_id))
                        elif lost_ack:
                            with self.assertRaisesRegex(b3.BridgeRefusal, "UNKNOWN_HOLD"):
                                next(stream)
                        else:
                            terminal = next(stream)
                            self.assertEqual(terminal["event"], "COMMITTED")
                            self.assertEqual(terminal["text"], SECRET)
                            self.assertEqual(terminal["revision"], 2)
                            # A durable local reply is itself text-bearing;
                            # never reinterpret it as permission to release.
                            with self.assertRaisesRegex(
                                D.DisclosureHold,
                                "ONLY_UNTRUSTED_PROVISIONAL_DELTA_IS_INSPECTABLE"
                            ) as caught:
                                D.block_provisional_delta(cw, iw, terminal, now_ms=200)
                            self.assertNotIn(SECRET, str(caught.exception))
                            with self.assertRaisesRegex(
                                C.ForestC5Hold, "COMMITTED_REPLY_PROTECTED_RELEASE_POLICY_REQUIRED"
                            ) as denied:
                                authority.authorize_release_committed_reply(terminal)
                            self.assertNotIn(SECRET, str(denied.exception))
                            self.assertEqual(control.request_stop(
                                context, operation, attempt_id),
                                "COMMIT_ENTRY_ALREADY_WON")
                            with self.assertRaises(StopIteration):
                                next(stream)
                        # Actual B3 finally block closes the one-shot control.
                        self.assertEqual(control.request_stop(
                            context, operation, attempt_id), "CONTROL_CLOSED")
                        # The existing native candidate can submit only its
                        # immutable public HOLD. Explicit test invocation,
                        # not an installed B3-to-Bark adapter.
                        sender, receiver = socket.socketpair(
                            socket.AF_UNIX, socket.SOCK_SEQPACKET)
                        with sender, receiver:
                            sender.settimeout(1)
                            receiver.settimeout(1)
                            self.assertTrue(native._submit_public_hold_once(sender))
                            wire = receiver.recv(2048)
                            self.assertEqual(wire, native._PUBLIC_HOLD)
                            self.assertEqual(len(wire), len(native._PUBLIC_HOLD))
                            for marker in (SECRET, sid, uid, res["attempt_id"],
                                           "fixture_owner"):
                                self.assertNotIn(marker.encode("utf-8"), wire)
                            status = json.loads(wire)
                            self.assertEqual(status["status"], "UNKNOWN_HOLD")
                            self.assertEqual(status["privateBytesSubmitted"], 0)
                            self.assertIs(status["revocationFencedAck"], False)
                            self.assertIs(status["permissionGranted"], False)
                            self.assertEqual(status["safeActions"], [])
                        attempt = db.execute(
                            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?",
                            (res["attempt_id"],)).fetchone()[0]
                        self.assertEqual(attempt, "ABORTED" if cancel else "COMMITTED")
                        report = b4f.ForestLocalTerminalOutboxInspector(journal).inspect(
                            owner="fixture_owner", session_id=sid,
                            attempt_id=res["attempt_id"])
                        self.assertEqual(report["c5Settlement"], "UNKNOWN_HOLD")
                        self.assertIs(report["safeToRetryInference"], False)
                        self.assertIs(report["safeToReleaseRevocation"], False)
                        self.assertEqual(len(journal.turns("fixture_owner", sid)),
                                         1 if cancel else 2)
                        self.assertEqual(len(PublicFixture.observed), 1)
                        self.assertEqual(PublicFixture.observed[0][2]["messages"],
                                         [{"role": "user", "content": "Public synthetic question"}])
                        self.assertEqual(authority.status()["safeActions"], [])
                        for field in C.NO_AUTHORITY:
                            self.assertIs(authority.status()[field], False, field)
        finally:
            server.shutdown()
            server.server_close()
            serving.join(timeout=2)

    def test_33_existing_b2_b3_commit_does_not_release_reply(self):
        self._exercise_existing_transport_and_hold_sender(cancel=False)

    def test_34_existing_b2_cancel_does_not_release_or_ack_revoke(self):
        self._exercise_existing_transport_and_hold_sender(cancel=True)

    def test_35_r2_commit_entry_wins_but_lost_ack_stays_unknown(self):
        self._exercise_existing_transport_and_hold_sender(cancel=False, lost_ack=True)


if __name__ == "__main__":
    unittest.main()
