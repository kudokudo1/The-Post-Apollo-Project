#!/usr/bin/env python3
"""C4b ↔ C3e source compatibility attacks (no real custodian or admission)."""
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical
import c4b_c3e_storage_boundary_compat_ci as B

def encoded(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

class C4bC3eHoldCompatibility(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.challenge = B.C4B.generate_controller_challenge()
        raw = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE",
            "requestId": None,
        }) + b"\n"
        self.frame = ReceiptIssuer(self.key).seal(
            "BEGIN", None, self.challenge, raw,
        )
        self.serial = self.proof(self.pub, self.frame)

    @staticmethod
    def proof(pub, frame):
        return B.C4B.PROOF_PREFIX + b"pub=" + encoded(pub) + b" frame=" + encoded(frame) + b"\n"

    def inspect(self, **changed):
        return B.inspect_ci_only(
            serial=changed.get("serial", self.serial),
            controller_challenge=changed.get("challenge", self.challenge),
        )

    def assert_hold(self, report):
        self.assertEqual(report["schema"], B.SCHEMA)
        self.assertEqual(report["status"], B.STATUS)
        self.assertIs(report["c3eProtectedCustodianUnavailable"], True)
        for key in B.DENIED:
            self.assertIs(report[key], False, key)

    def test_01_valid_signed_denial_still_holds(self):
        report = self.inspect()
        self.assert_hold(report)
        self.assertEqual(report["runtimePublicKeySha256"], hashlib.sha256(self.pub).hexdigest())

    def test_02_old_proof_wrong_challenge_refused(self):
        with self.assertRaises(B.Refused):
            self.inspect(challenge=B.C4B.generate_controller_challenge())

    def test_03_substituted_signer_refused(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(B.Refused):
            self.inspect(serial=self.proof(other, self.frame))

    def test_04_duplicate_proof_refused(self):
        with self.assertRaises(B.Refused):
            self.inspect(serial=self.serial + self.serial)

    def test_05_tampered_signed_frame_refused(self):
        damaged = bytearray(self.frame)
        damaged[-5] ^= 1
        with self.assertRaises(B.Refused):
            self.inspect(serial=self.proof(self.pub, bytes(damaged)))

    def test_06_forged_uart_authority_marker_does_not_grant(self):
        self.assert_hold(self.inspect(serial=self.serial + b"C4B_ID_PASS // CAN_BEGIN_SIGN_IN_TRUE\n"))

    def test_07_forged_positive_original_proof_refused(self):
        original = B.C4B.inspect_ci_only
        def poisoned(*, serial, controller_challenge):
            out = original(serial=serial, controller_challenge=controller_challenge)
            out["hostAuthenticated"] = True
            return out
        with mock.patch.object(B.C4B, "inspect_ci_only", side_effect=poisoned):
            with self.assertRaisesRegex(B.Refused, "ATTEMPTED_PROMOTION"):
                self.inspect()

    def test_08_extra_proof_authority_fields_refused(self):
        original = B.C4B.inspect_ci_only
        def poisoned(*, serial, controller_challenge):
            out = original(serial=serial, controller_challenge=controller_challenge)
            out["nativeConsent"] = True
            return out
        with mock.patch.object(B.C4B, "inspect_ci_only", side_effect=poisoned):
            with self.assertRaisesRegex(B.Refused, "PROOF_FIELDS_REFUSED"):
                self.inspect()

    def test_09_forged_protected_status_grant_refused(self):
        original = B.C3E.TrustBoundary.protected_required_status
        def poisoned(boundary):
            out = original(boundary)
            out["protectedCustodianReachable"] = True
            return out
        with mock.patch.object(B.C3E.TrustBoundary,
                               "protected_required_status", new=poisoned):
            with self.assertRaisesRegex(B.Refused, "PROTECTED_STATUS_MUST_HOLD"):
                self.inspect()

    def test_10_extra_protected_status_fields_refused(self):
        original = B.C3E.TrustBoundary.protected_required_status
        def poisoned(boundary):
            out = original(boundary)
            out["remoteKey"] = "self-asserted"
            return out
        with mock.patch.object(B.C3E.TrustBoundary,
                               "protected_required_status", new=poisoned):
            with self.assertRaisesRegex(B.Refused, "STATUS_FIELDS_REFUSED"):
                self.inspect()

    def test_11_no_local_sqlite_fallback_on_valid_signed_proof(self):
        with mock.patch.object(B.C3E.L, "connect", side_effect=AssertionError("LOCAL_DB_USED")):
            self.assert_hold(self.inspect())
        protected = B.C3E.TrustBoundary(required_mode=B.C3E.PROTECTED_REQUIRED)
        for operation, args in (
            ("read_current_snapshot", ()),
            ("issue_challenge", ()),
            ("commit_signed_history", ()),
            ("lookup_terminal_outcome", (b"\x00" * 32,)),
        ):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(B.C3E.Refused, "HOLD_NO_FALLBACK"):
                    getattr(protected, operation)(*args)

    def test_12_fake_remote_local_adapter_refused(self):
        class Fake:
            certified = True
            remote_url = "https://example.invalid"
        with self.assertRaises(B.C3E.Refused):
            B.C3E.TrustBoundary(required_mode=B.C3E.PROTECTED_REQUIRED,
                                 local_adapter=Fake())

    def test_13_invalid_types_refused(self):
        for values in (
            {"challenge": True}, {"challenge": "x"},
            {"serial": "not bytes"}, {"serial": b""},
        ):
            with self.subTest(values=values), self.assertRaises(B.Refused):
                self.inspect(**values)

    def test_14_test_only_source_and_native_broker_inert(self):
        source = (Path(__file__).parent /
                  "c4b_c3e_storage_boundary_compat_ci.py").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        for forbidden in ("sqlite3.connect(", "socket.socket(", "subprocess.run(",
                          "Ed25519PrivateKey", '"productionAuthority": True'):
            self.assertNotIn(forbidden, source)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)

if __name__ == "__main__":
    unittest.main(verbosity=2)
