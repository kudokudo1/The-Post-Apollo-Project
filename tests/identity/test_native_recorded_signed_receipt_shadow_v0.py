"""DOC 6 recorded command-receipt shadow: authenticated bytes != trusted outcome."""
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

from native_outcome_candidate_shadow_v0 import OriginalCommandBinding
from native_recorded_signed_receipt_shadow_v0 import (
    SCHEMA, inspect_recorded_signed_receipt,
)
from signed_command_receipt_v0 import (
    LEGACY_RECEIPT_SCHEMA, ReceiptIssuer,
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


class RecordedSignedReceiptShadowTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.issuer = ReceiptIssuer(self.private_key)
        self.nonce = secrets.token_urlsafe(32)
        self.rid = "ORIGINAL_HOST_REQUEST_000001"

    def setup_frame(self, *, action="BEGIN", state=None, request_id=None,
                    nonce=None, issuer=None, key=None):
        issuer = issuer or self.issuer
        nonce = nonce or self.nonce
        rid = None if action == "BEGIN" else (self.rid if request_id is None else request_id)
        phase = state or {
            "BEGIN": "REQUESTED", "STATUS": "PENDING",
            "CANCEL": "CANCELLED", "RECOVER": "REQUESTED",
        }[action]
        host_rid = (
            None if phase == "UNAVAILABLE" else
            "NEW_RECOVERED_REQUEST_00001" if action == "RECOVER" else
            "BEGIN_HOST_REQUEST_000001" if action == "BEGIN" else rid
        )
        raw = json.dumps({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": phase, "requestId": host_rid,
        }, separators=(",", ":")).encode("ascii") + b"\n"
        frame = issuer.seal(action, rid, nonce, raw)
        expected = OriginalCommandBinding(
            attempt_id="1" * 32,
            action=action,
            request_digest=None if rid is None else digest(rid),
            nonce_digest=digest(nonce),
            host_instance_digest=digest(issuer._instance),
            seat_digest="a" * 64,
            session_digest="b" * 64,
            challenge_digest="c" * 64,
            history_digest="d" * 64,
            issuer_epoch=7,
            minimum_sequence=1,
        )
        return expected, frame, rid, nonce

    def check(self, original, frame, rid, nonce, key=None):
        return inspect_recorded_signed_receipt(
            original=original,
            recorded_frame=frame,
            pinned_receipt_key=key or self.private_key.public_key(),
            original_request_id=rid,
            original_client_nonce=nonce,
        )

    def assert_hold(self, output, checked=None):
        self.assertEqual(output.schema, SCHEMA)
        self.assertEqual(output.state, "UNKNOWN_HOLD")
        self.assertEqual(output.safe_actions, ())
        if checked is not None:
            self.assertIs(output.signed_frame_checked, checked)
        for field in (
            "can_retry", "can_begin_sign_in", "can_cancel", "can_recover",
            "can_connect_provider", "independently_enrolled_host",
            "protected_history_current", "protected_terminal_outcome",
            "human_one_use_consent", "production_authority",
        ):
            self.assertIs(getattr(output, field), False)

    def test_genuine_begin_receipt_still_no_protected_terminal(self):
        original, frame, rid, nonce = self.setup_frame()
        report = self.check(original, frame, rid, nonce)
        self.assert_hold(report, True)
        self.assertEqual(report.reason, "SIGNED_FRAME_MATCHED_BUT_NO_PROTECTED_TERMINAL")

    def test_each_native_command_valid_receipt_stays_hold(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                expected, frame, rid, nonce = self.setup_frame(action=action)
                self.assert_hold(self.check(expected, frame, rid, nonce), True)

    def test_signed_authenticated_host_status_is_not_provider_grant(self):
        expected, frame, rid, nonce = self.setup_frame(
            action="STATUS", state="AUTHENTICATED")
        report = self.check(expected, frame, rid, nonce)
        self.assert_hold(report, True)
        self.assertFalse(hasattr(report, "hostAuthenticated"))
        self.assertFalse(hasattr(report, "access_token"))

    def test_signed_unavailable_does_not_prove_no_effect(self):
        expected, frame, rid, nonce = self.setup_frame(state="UNAVAILABLE")
        self.assert_hold(self.check(expected, frame, rid, nonce), True)

    def test_wrong_public_key_cannot_reuse_signed_frame(self):
        expected, frame, rid, nonce = self.setup_frame()
        other_key = Ed25519PrivateKey.generate().public_key()
        self.assert_hold(self.check(expected, frame, rid, nonce, other_key), False)

    def test_modified_signed_body_refused(self):
        expected, frame, rid, nonce = self.setup_frame()
        envelope = json.loads(frame)
        envelope["body"]["state"] = "AUTHENTICATED"
        tampered = json.dumps(envelope).encode() + b"\n"
        self.assert_hold(self.check(expected, tampered, rid, nonce), False)

    def test_signed_frame_wrong_original_nonce_refused(self):
        expected, frame, rid, nonce = self.setup_frame()
        other = secrets.token_urlsafe(32)
        self.assert_hold(self.check(expected, frame, rid, other), False)
        changed = replace(expected, nonce_digest=digest(other))
        self.assert_hold(self.check(changed, frame, rid, other), False)

    def test_signed_frame_wrong_original_request_refused(self):
        expected, frame, rid, nonce = self.setup_frame(action="STATUS")
        other = "SECOND_HOST_REQUEST_0000002"
        self.assert_hold(self.check(expected, frame, other, nonce), False)
        changed = replace(expected, request_digest=digest(other))
        self.assert_hold(self.check(changed, frame, other, nonce), False)

    def test_signed_frame_wrong_action_refused(self):
        expected, frame, rid, nonce = self.setup_frame(action="STATUS")
        changed = replace(expected, action="CANCEL")
        self.assert_hold(self.check(changed, frame, rid, nonce), False)

    def test_wrong_signed_host_instance_digest_remains_hold(self):
        expected, frame, rid, nonce = self.setup_frame()
        changed = replace(expected, host_instance_digest="0" * 64)
        report = self.check(changed, frame, rid, nonce)
        self.assert_hold(report, True)
        self.assertEqual(report.reason, "SIGNED_FRAME_WRONG_HOST_OR_SEQUENCE")

    def test_old_signed_sequence_below_floor_refused(self):
        expected, frame, rid, nonce = self.setup_frame()
        changed = replace(expected, minimum_sequence=2)
        report = self.check(changed, frame, rid, nonce)
        self.assert_hold(report, True)
        self.assertEqual(report.reason, "SIGNED_FRAME_WRONG_HOST_OR_SEQUENCE")

    def test_replayed_prior_signed_frame_is_not_fresh_reconciliation(self):
        expected, frame, rid, nonce = self.setup_frame()
        old = self.check(expected, frame, rid, nonce)
        new = self.check(expected, frame, rid, nonce)
        self.assert_hold(old, True)
        self.assert_hold(new, True)
        self.assertEqual(old.reason, new.reason)

    def test_missing_frame_and_missing_pin_are_denied(self):
        expected, frame, rid, nonce = self.setup_frame()
        for missing in (None, b"", b"no newline", b"x" * 1025, "frame"):
            with self.subTest(missing=repr(missing)):
                self.assert_hold(self.check(expected, missing, rid, nonce), False)
        self.assert_hold(inspect_recorded_signed_receipt(
            original=expected, recorded_frame=frame,
            pinned_receipt_key=None, original_request_id=rid,
            original_client_nonce=nonce), False)

    def test_extra_envelope_claims_are_refused(self):
        expected, frame, rid, nonce = self.setup_frame()
        envelope = json.loads(frame)
        envelope["productionAuthority"] = True
        changed = json.dumps(envelope).encode("ascii") + b"\n"
        self.assert_hold(self.check(expected, changed, rid, nonce), False)

    def test_non_ascii_or_malformed_request_refused_before_digest(self):
        expected, frame, rid, nonce = self.setup_frame(action="STATUS")
        for bad in ("✶" * 20, "x", "a" * 97, "unsafe / path", 4):
            with self.subTest(bad=repr(bad)):
                self.assert_hold(self.check(expected, frame, bad, nonce), False)

    def test_begin_must_not_claim_prior_request_id(self):
        expected, frame, rid, nonce = self.setup_frame()
        self.assert_hold(self.check(expected, frame, self.rid, nonce), False)

    def test_bad_original_binding_refused_without_signature_check(self):
        expected, frame, rid, nonce = self.setup_frame()
        report = inspect_recorded_signed_receipt(
            original={"claimed": "BEGIN"}, recorded_frame=frame,
            pinned_receipt_key=self.private_key.public_key(),
            original_request_id=rid, original_client_nonce=nonce)
        self.assert_hold(report, False)

    def test_immutable_result_exposes_no_settle_retry_approval(self):
        expected, frame, rid, nonce = self.setup_frame()
        result = self.check(expected, frame, rid, nonce)
        with self.assertRaises(FrozenInstanceError):
            result.production_authority = True
        for method in ("settle", "clear_hold", "retry", "approve", "connect"):
            self.assertFalse(hasattr(result, method))
        self.assert_hold(result, True)

    def test_no_network_store_native_sender_or_c5_imports(self):
        import ast
        source = (ROOT / "services/identity/native_recorded_signed_receipt_shadow_v0.py").read_text()
        imports = []
        tree = ast.parse(source)
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                imports.extend(a.name for a in item.names)
            elif isinstance(item, ast.ImportFrom) and item.module:
                imports.append(item.module)
        for ban in (
            "socket", "sqlite3", "subprocess", "desktop_signed_command_client_v0",
            "installed_command_adapter_v1",
            "desktop_command_gateway_v0",
            "local_command_outcome_hold_reference_v0",
        ):
            self.assertNotIn(ban, imports)
        self.assertNotIn("sendall(", source)
        self.assertNotIn("production_authority=True", source)


if __name__ == "__main__":
    unittest.main()
