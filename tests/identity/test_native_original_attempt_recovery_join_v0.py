"""DOC 6: actual signed native frame + untrusted outcome candidate never settles."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import secrets
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_signed_command_client_v0 import AttemptedWireFingerprint
from native_outcome_candidate_shadow_v0 import (
    OriginalCommandBinding, SCHEMA as CANDIDATE_SCHEMA, inspect_supplied_candidate,
)
from native_original_attempt_recovery_join_v0 import (
    SCHEMA, inspect_original_attempt_once, inspect_original_attempt_snapshot,
)
from signed_command_receipt_v0 import (
    LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, build_request,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ascii_hash(value: str) -> str:
    return sha(value.encode("ascii"))


class OriginalAttemptJoinTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.issuer = ReceiptIssuer(self.private)
        self.nonce = secrets.token_urlsafe(32)
        self.rid = "NATIVE_HOST_REQUEST_000001"
        self.calls = []

    def evidence(self, action="BEGIN", state=None):
        rid = None if action == "BEGIN" else self.rid
        wire = build_request(action, rid, self.nonce)
        attempted = AttemptedWireFingerprint(
            action=action, request_id_sha256=None if rid is None else ascii_hash(rid),
            client_nonce_sha256=ascii_hash(self.nonce), frame_sha256=sha(wire))
        original = OriginalCommandBinding(
            attempt_id="1" * 32, action=action,
            request_digest=attempted.request_id_sha256,
            nonce_digest=attempted.client_nonce_sha256,
            host_instance_digest=ascii_hash(self.issuer._instance),
            seat_digest="a" * 64, session_digest="b" * 64,
            challenge_digest="c" * 64, history_digest="d" * 64,
            issuer_epoch=5, minimum_sequence=1)
        state = state or {"BEGIN": "REQUESTED", "STATUS": "PENDING",
                          "CANCEL": "CANCELLED", "RECOVER": "REQUESTED"}[action]
        result_rid = (
            None if state == "UNAVAILABLE" else
            "RECOVERED_HOST_REQUEST_000002" if action == "RECOVER" else
            "BEGIN_HOST_REQUEST_000001" if action == "BEGIN" else rid)
        legacy = json.dumps({"schema": LEGACY_RECEIPT_SCHEMA,
                             "state": state, "requestId": result_rid},
                            separators=(",", ":")).encode("ascii") + b"\n"
        frame = self.issuer.seal(action, rid, self.nonce, legacy)
        candidate = dict(
            schema=CANDIDATE_SCHEMA, attemptId=original.attempt_id,
            action=original.action, requestDigest=original.request_digest,
            nonceDigest=original.nonce_digest,
            hostInstanceDigest=original.host_instance_digest,
            seatDigest=original.seat_digest,
            sessionDigest=original.session_digest,
            challengeDigest=original.challenge_digest,
            historyDigest=original.history_digest,
            issuerEpoch=original.issuer_epoch,
            sequence=original.minimum_sequence,
            claimedResult="CLAIMED_NO_EFFECT")
        return attempted, original, rid, frame, candidate

    def lookup(self, candidate):
        self.calls.append(True)
        return candidate

    def inspect(self, attempted, original, rid, frame, candidate,
                nonce=None, key=None, provider=True):
        return inspect_original_attempt_once(
            attempted=attempted, original=original,
            original_client_nonce=self.nonce if nonce is None else nonce,
            original_request_id=rid, recorded_signed_frame=frame,
            pinned_receipt_key=self.private.public_key() if key is None else key,
            candidate_provider=(
                (lambda _: self.lookup(candidate)) if provider else None))

    def inspect_snapshot(self, attempted, original, rid, frame, candidate,
                         nonce=None, key=None):
        return inspect_original_attempt_snapshot(
            attempted=attempted, original=original,
            original_client_nonce=self.nonce if nonce is None else nonce,
            original_request_id=rid, candidate_snapshot=candidate,
            recorded_signed_frame=frame,
            pinned_receipt_key=self.private.public_key() if key is None else key)

    def hold(self, value, *, checked=None, calls=None, matched=None):
        self.assertEqual(value.schema, SCHEMA)
        self.assertEqual(value.state, "UNKNOWN_HOLD")
        self.assertEqual(value.safe_actions, ())
        if checked is not None:
            self.assertIs(value.signed_frame_checked, checked)
        if calls is not None:
            self.assertEqual(value.candidate_lookup_count, calls)
        if matched is not None:
            self.assertIs(value.original_frame_matched, matched)
        for prop in ("can_retry", "can_begin_sign_in", "can_cancel",
                     "can_recover", "can_connect_provider",
                     "original_host_authenticated", "protected_current_history",
                     "independent_issuer_enrolled", "human_one_use_consent",
                     "terminal_outcome_settled", "production_authority"):
            self.assertIs(getattr(value, prop), False)

    def test_snapshot_matching_two_sources_still_unknown_and_zero_lookup(self):
        result = self.inspect_snapshot(*self.evidence())
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.reason,
                         "MATCHING_UNTRUSTED_SOURCES_STILL_NOT_SETTLEMENT")
        self.assertEqual(result.candidate_reason, "MATCHED_CLAIM_STILL_UNTRUSTED")
        self.assertEqual(self.calls, [])

    def test_snapshot_all_actions_no_new_native_command(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                result = self.inspect_snapshot(*self.evidence(action))
                self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(self.calls, [])

    def test_snapshot_old_fixture_semantics_agree_without_lookup(self):
        data = self.evidence()
        pure = self.inspect_snapshot(*data)
        old = self.inspect(*data)
        self.hold(pure, matched=True, checked=True, calls=0)
        self.hold(old, matched=True, checked=True, calls=1)
        self.assertEqual(pure.reason, old.reason)
        self.assertEqual(pure.candidate_reason, old.candidate_reason)
        self.assertEqual(pure.signed_frame_reason, old.signed_frame_reason)
        self.assertEqual(self.calls, [True])

    def test_snapshot_callable_is_never_invoked(self):
        class Executable:
            def __init__(self):
                self.count = 0
            def __call__(self, *_):
                self.count += 1
                raise RuntimeError("would have run arbitrary Python")
        payload = Executable()
        attempted, original, rid, frame, _ = self.evidence()
        result = self.inspect_snapshot(attempted, original, rid, frame, payload)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "MALFORMED_UNTRUSTED_CANDIDATE")
        self.assertEqual(payload.count, 0)

    def test_snapshot_dict_subclass_with_side_effecting_access_refused(self):
        class ActiveDict(dict):
            def __getitem__(self, key):
                raise RuntimeError("untrusted subclass side effect")
        attempted, original, rid, frame, candidate = self.evidence()
        result = self.inspect_snapshot(
            attempted, original, rid, frame, ActiveDict(candidate))
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_snapshot_non_string_dict_key_never_executes_custom_hash(self):
        class ActiveKey:
            def __init__(self):
                self.calls = 0
            def __hash__(self):
                self.calls += 1
                return 982451653
            def __eq__(self, other):
                self.calls += 100
                return False
        attempted, original, rid, frame, candidate = self.evidence()
        value = candidate.pop("schema")
        key = ActiveKey()
        candidate[key] = value
        key.calls = 0  # Ignore the necessary one-time dict construction hash.
        result = self.inspect_snapshot(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "MALFORMED_UNTRUSTED_CANDIDATE")
        self.assertEqual(key.calls, 0)

    def test_snapshot_str_subclass_key_never_executes_custom_hash(self):
        class ActiveString(str):
            def __new__(cls, value):
                obj = super().__new__(cls, value)
                obj.calls = 0
                return obj
            def __hash__(self):
                self.calls += 1
                return super().__hash__()
            def __eq__(self, other):
                self.calls += 100
                return super().__eq__(other)
        attempted, original, rid, frame, candidate = self.evidence()
        value = candidate.pop("schema")
        key = ActiveString("schema")
        candidate[key] = value
        key.calls = 0
        result = self.inspect_snapshot(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "MALFORMED_UNTRUSTED_CANDIDATE")
        self.assertEqual(key.calls, 0)

    def test_snapshot_absent_candidate_is_no_provider_not_failure(self):
        attempted, original, rid, frame, _ = self.evidence()
        result = self.inspect_snapshot(attempted, original, rid, frame, None)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "SUPPLIED_CANDIDATE_NOT_AVAILABLE")

    def test_snapshot_invalid_original_fails_before_candidate_read(self):
        attempted, original, rid, frame, candidate = self.evidence()
        for changed in (None, replace(attempted, action="STATUS"),
                        replace(attempted, frame_sha256="f" * 64)):
            with self.subTest(changed=repr(changed)[:50]):
                result = self.inspect_snapshot(
                    changed, original, rid, frame, candidate)
                self.hold(result, matched=False, checked=False, calls=0)
                self.assertEqual(result.candidate_reason, "NOT_INSPECTED")
        self.assertEqual(self.calls, [])

    def test_snapshot_request_and_nonce_drift_never_inspects_source(self):
        attempted, original, rid, frame, candidate = self.evidence("STATUS")
        for altered_rid, altered_nonce in (
            ("OTHER_HOST_REQUEST_00002", self.nonce),
            (rid, secrets.token_urlsafe(32)),
            ("∑", self.nonce),
        ):
            with self.subTest(rid=repr(altered_rid)):
                result = self.inspect_snapshot(
                    attempted, original, altered_rid, frame, candidate,
                    nonce=altered_nonce)
                self.hold(result, matched=False, checked=False, calls=0)
        self.assertEqual(self.calls, [])

    def test_snapshot_forged_authority_flag_never_grants(self):
        attempted, original, rid, frame, candidate = self.evidence()
        candidate["canRetry"] = True
        result = self.inspect_snapshot(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.candidate_reason,
                         "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_snapshot_history_and_seat_mismatch_do_not_settle(self):
        attempted, original, rid, frame, candidate = self.evidence()
        for field, replacement in (("historyDigest", "0"*64),
                                   ("seatDigest", "1"*64),
                                   ("issuerEpoch", 100)):
            with self.subTest(field=field):
                changed = dict(candidate, **{field: replacement})
                result = self.inspect_snapshot(
                    attempted, original, rid, frame, changed)
                self.hold(result, matched=True, checked=True, calls=0)
                self.assertEqual(result.reason,
                                 "RECOVERY_CANDIDATE_CONFLICTS_WITH_ORIGINAL")

    def test_snapshot_signed_authenticated_and_unavailable_stay_hold(self):
        for action, state in (("STATUS", "AUTHENTICATED"),
                              ("BEGIN", "UNAVAILABLE")):
            with self.subTest(state=state):
                result = self.inspect_snapshot(
                    *self.evidence(action, state=state))
                self.hold(result, matched=True, checked=True, calls=0)
                self.assertFalse(hasattr(result, "access_token"))

    def test_snapshot_unpinned_or_wrong_key_stays_hold(self):
        attempted, original, rid, frame, candidate = self.evidence()
        wrong = Ed25519PrivateKey.generate().public_key()
        for key in (wrong, False):
            with self.subTest(key=repr(key)):
                result = self.inspect_snapshot(
                    attempted, original, rid, frame, candidate, key=key)
                self.hold(result, matched=True, checked=False, calls=0)
                self.assertFalse(result.terminal_outcome_settled)

    def test_snapshot_stale_signed_sequence_remains_hold(self):
        attempted, original, rid, frame, candidate = self.evidence()
        original = replace(original, minimum_sequence=2)
        candidate["sequence"] = 2
        result = self.inspect_snapshot(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertEqual(result.reason,
                         "SIGNED_RECEIPT_CONFLICTS_WITH_ORIGINAL")

    def test_snapshot_replay_does_not_change_prior_unknown(self):
        data = self.evidence()
        a = self.inspect_snapshot(*data)
        b = self.inspect_snapshot(*data)
        self.hold(a, matched=True, checked=True, calls=0)
        self.hold(b, matched=True, checked=True, calls=0)
        self.assertEqual(a, b)
        self.assertEqual(self.calls, [])

    def test_snapshot_output_does_not_contain_raw_secret_or_command(self):
        result = self.inspect_snapshot(*self.evidence("STATUS"))
        self.hold(result, matched=True, checked=True, calls=0)
        self.assertNotIn(self.nonce, repr(result))
        self.assertNotIn(self.rid, repr(result))
        for value in ("command", "raw_nonce", "raw_frame", "authorization",
                      "approve", "retry", "settle"):
            self.assertFalse(hasattr(result, value))
        with self.assertRaises(FrozenInstanceError):
            result.production_authority = True

    def test_direct_supplied_comparator_does_not_invoke_candidate(self):
        attempted, original, rid, frame, candidate = self.evidence()
        result = inspect_supplied_candidate(original=original, candidate=candidate)
        self.assertEqual(result.state, "UNKNOWN_HOLD")
        self.assertEqual(result.lookup_count, 0)
        self.assertEqual(result.reason, "MATCHED_CLAIM_STILL_UNTRUSTED")
        self.assertEqual(self.calls, [])

    def test_snapshot_entrypoint_has_no_provider_or_network_call(self):
        import ast
        root = ROOT / "services" / "identity"
        join = ast.parse((root / "native_original_attempt_recovery_join_v0.py"
                          ).read_text())
        entry = next(n for n in join.body if isinstance(n, ast.FunctionDef)
                     and n.name == "inspect_original_attempt_snapshot")
        self.assertNotIn("candidate_provider",
                         [arg.arg for arg in entry.args.kwonlyargs])
        self.assertNotIn("inspect_candidate_once",
                         [n.id for n in ast.walk(entry)
                          if isinstance(n, ast.Name)])
        self.assertIn("inspect_supplied_candidate",
                      [n.id for n in ast.walk(entry) if isinstance(n, ast.Name)])
        self.assertEqual(self.calls, [])

    def test_real_signed_fixture_and_matching_claim_do_not_settle(self):
        data = self.evidence()
        result = self.inspect(*data)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(result.reason,
                         "MATCHING_UNTRUSTED_SOURCES_STILL_NOT_SETTLEMENT")
        self.assertEqual(len(self.calls), 1)

    def test_all_four_commands_match_without_grant(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                self.calls.clear()
                result = self.inspect(*self.evidence(action=action))
                self.hold(result, matched=True, checked=True, calls=1)

    def test_signed_authenticated_status_never_grants_provider(self):
        data = self.evidence(action="STATUS", state="AUTHENTICATED")
        result = self.inspect(*data)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertFalse(hasattr(result, "access_token"))

    def test_signed_unavailable_no_effect_claim_never_permits_retry(self):
        data = self.evidence(state="UNAVAILABLE")
        result = self.inspect(*data)
        self.hold(result, matched=True, checked=True, calls=1)

    def test_absent_local_attempt_blocks_candidate_lookup(self):
        _, original, rid, frame, candidate = self.evidence()
        result = self.inspect(None, original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)
        self.assertEqual(self.calls, [])

    def test_malformed_original_binding_blocks_lookup(self):
        attempted, _, rid, frame, candidate = self.evidence()
        result = self.inspect(attempted, {"not": "original"}, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)
        self.assertEqual(self.calls, [])

    def test_foreign_attempt_object_blocks_lookup(self):
        attempted, original, rid, frame, candidate = self.evidence()
        result = self.inspect(attempted.__dict__ if hasattr(attempted, "__dict__")
                              else {"action": attempted.action},
                              original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)
        self.assertEqual(self.calls, [])

    def test_wrong_original_action_blocks_lookup(self):
        attempted, original, rid, frame, candidate = self.evidence("STATUS")
        result = self.inspect(replace(attempted, action="CANCEL"),
                              original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_wrong_nonce_commitment_blocks_lookup(self):
        attempted, original, rid, frame, candidate = self.evidence()
        result = self.inspect(replace(attempted, client_nonce_sha256="f" * 64),
                              original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_wrong_host_request_commitment_blocks_lookup(self):
        attempted, original, rid, frame, candidate = self.evidence("CANCEL")
        result = self.inspect(replace(attempted, request_id_sha256="f" * 64),
                              original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_invalid_digest_type_or_case_blocks_lookup(self):
        data = self.evidence()
        attempted, original, rid, frame, candidate = data
        for field, val in (("frame_sha256", True),
                           ("frame_sha256", "A" * 64),
                           ("client_nonce_sha256", "0"),
                           ("request_id_sha256", 1)):
            with self.subTest(field=field, val=repr(val)):
                self.calls.clear()
                result = self.inspect(replace(attempted, **{field: val}),
                                      original, rid, frame, candidate)
                self.hold(result, matched=False, checked=False, calls=0)
                self.assertEqual(self.calls, [])

    def test_changed_exact_frame_digest_never_queries(self):
        attempted, original, rid, frame, candidate = self.evidence()
        result = self.inspect(replace(attempted, frame_sha256="a" * 64),
                              original, rid, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)
        self.assertEqual(result.reason, "ORIGINAL_SERIALIZED_FRAME_CONFLICT")

    def test_raw_nonce_different_from_original_frame_never_queries(self):
        attempted, original, rid, frame, candidate = self.evidence()
        another = secrets.token_urlsafe(32)
        result = self.inspect(attempted, original, rid, frame, candidate, nonce=another)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_raw_request_different_from_original_frame_never_queries(self):
        attempted, original, _, frame, candidate = self.evidence("STATUS")
        result = self.inspect(attempted, original, "SECOND_HOST_REQUEST_0001",
                              frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_non_ascii_request_identifier_never_queries(self):
        attempted, original, _, frame, candidate = self.evidence("STATUS")
        result = self.inspect(attempted, original, "☯" * 20, frame, candidate)
        self.hold(result, matched=False, checked=False, calls=0)

    def test_valid_local_attempt_missing_candidate_and_receipt_is_still_hold(self):
        attempted, original, rid, _, _ = self.evidence()
        result = self.inspect(attempted, original, rid, None, None, provider=False)
        self.hold(result, matched=True, checked=False, calls=0)
        self.assertEqual(result.reason, "INCOMPLETE_OR_UNTRUSTED_RECOVERY_EVIDENCE")

    def test_candidate_provider_failure_one_call_no_retry(self):
        attempted, original, rid, frame, candidate = self.evidence()
        def fails(_):
            self.calls.append(True)
            raise TimeoutError("no issuer response")
        result = inspect_original_attempt_once(
            attempted=attempted, original=original, original_client_nonce=self.nonce,
            original_request_id=rid, recorded_signed_frame=frame,
            pinned_receipt_key=self.private.public_key(), candidate_provider=fails)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(len(self.calls), 1)

    def test_candidate_wrong_history_head_is_explicit_conflict(self):
        attempted, original, rid, frame, candidate = self.evidence()
        candidate["historyDigest"] = "e" * 64
        result = self.inspect(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(result.reason, "RECOVERY_CANDIDATE_CONFLICTS_WITH_ORIGINAL")

    def test_candidate_forged_authority_field_cannot_promote(self):
        attempted, original, rid, frame, candidate = self.evidence()
        candidate["productionAuthority"] = True
        result = self.inspect(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(result.candidate_reason, "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_wrong_signed_key_never_promotes(self):
        attempted, original, rid, frame, candidate = self.evidence()
        key = Ed25519PrivateKey.generate().public_key()
        result = self.inspect(attempted, original, rid, frame, candidate, key=key)
        self.hold(result, matched=True, checked=False, calls=1)
        self.assertEqual(result.reason, "INCOMPLETE_OR_UNTRUSTED_RECOVERY_EVIDENCE")

    def test_wrong_signed_instance_is_explicit_conflict(self):
        attempted, original, rid, frame, candidate = self.evidence()
        original = replace(original, host_instance_digest="f" * 64)
        candidate["hostInstanceDigest"] = original.host_instance_digest
        result = self.inspect(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(result.reason, "SIGNED_RECEIPT_CONFLICTS_WITH_ORIGINAL")

    def test_stale_signed_sequence_is_explicit_conflict(self):
        attempted, original, rid, frame, candidate = self.evidence()
        original = replace(original, minimum_sequence=3)
        candidate["sequence"] = 3
        result = self.inspect(attempted, original, rid, frame, candidate)
        self.hold(result, matched=True, checked=True, calls=1)
        self.assertEqual(result.reason, "SIGNED_RECEIPT_CONFLICTS_WITH_ORIGINAL")

    def test_replaying_same_signed_frame_and_candidate_remains_hold(self):
        data = self.evidence()
        a, b = self.inspect(*data), self.inspect(*data)
        self.hold(a, matched=True, checked=True, calls=1)
        self.hold(b, matched=True, checked=True, calls=1)
        self.assertEqual(len(self.calls), 2)

    def test_result_immutable_no_raw_nonce_request_or_frame(self):
        data = self.evidence()
        result = self.inspect(*data)
        self.hold(result, matched=True, checked=True)
        with self.assertRaises(FrozenInstanceError):
            result.production_authority = True
        serialized = repr(result)
        self.assertNotIn(self.nonce, serialized)
        self.assertNotIn(self.rid, serialized)
        self.assertFalse(hasattr(result, "raw_frame"))
        self.assertFalse(hasattr(result, "clear_hold"))
        self.assertFalse(hasattr(result, "settle"))
        self.assertFalse(hasattr(result, "retry"))

    def test_shared_value_type_preserves_client_compatibility(self):
        # Re-exported class remains the same immutable value, while shipped
        # recovery code never imports the raw native sender.
        from native_attempt_fingerprint_v0 import AttemptedWireFingerprint as Shared
        from desktop_signed_command_client_v0 import AttemptedWireFingerprint as Legacy
        self.assertIs(Shared, Legacy)
        self.assertIs(AttemptedWireFingerprint, Shared)
        attempted, original, rid, frame, candidate = self.evidence()
        self.assertIsInstance(attempted, Shared)
        self.hold(self.inspect(attempted, original, rid, frame, candidate),
                  matched=True, checked=True, calls=1)

    def test_no_sender_storage_or_c5_import(self):
        import ast
        path = ROOT / "services/identity/native_original_attempt_recovery_join_v0.py"
        code = path.read_text()
        imports = []
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.Import):
                imports.extend(v.name for v in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for name in ("socket", "sqlite3", "subprocess",
                     "installed_command_adapter_v1", "desktop_command_gateway_v0",
                     "desktop_signed_command_client_v0",
                     "local_command_outcome_hold_reference_v0"):
            self.assertNotIn(name, imports)
        self.assertNotIn("sendall(", code)
        self.assertNotIn("production_authority=True", code)


if __name__ == "__main__":
    unittest.main()
