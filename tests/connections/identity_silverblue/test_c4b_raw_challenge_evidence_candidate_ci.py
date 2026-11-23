#!/usr/bin/env python3
"""DOC 2: raw 32-byte challenge ↔ original C4b signed denial attack cases."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical
import c4b_raw_challenge_evidence_candidate_ci as E

def b64(blob):
    return base64.urlsafe_b64encode(blob).rstrip(b"=")

class RawChallengeEvidenceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.raw = bytes(range(32))
        self.nonce = E.encode_raw_challenge_ci_only(self.raw)
        self.key = Ed25519PrivateKey.generate()
        self.pub = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        body = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE", "requestId": None,
        }) + b"\n"
        self.frame = ReceiptIssuer(self.key).seal(
            "BEGIN", None, self.nonce, body,
        )
        self.serial = self.proof(self.pub, self.frame)

    @staticmethod
    def proof(pub, frame):
        return E.C4B.PROOF_PREFIX + b"pub=" + b64(pub) + b" frame=" + b64(frame) + b"\n"

    def check(self, **changes):
        return E.inspect_raw_challenge_denial_ci_only(
            raw_challenge=changes.get("raw", self.raw),
            serial=changes.get("serial", self.serial),
        )

    def assert_denied(self, result):
        self.assertEqual(result["schema"], E.SCHEMA)
        self.assertEqual(result["status"], E.STATUS)
        for flag in E.DENIED:
            self.assertIs(result[flag], False, flag)

    def test_01_exact_original_signed_denial_still_nonauthoritative(self):
        result = self.check()
        self.assert_denied(result)
        self.assertIs(result["ciOnlyOriginalSignedDenialVerified"], True)
        self.assertEqual(result["runtimePublicKeySha256"], hashlib.sha256(self.pub).hexdigest())

    def test_02_raw_challenge_and_existing_nonce_are_distinct_digest_domains(self):
        self.assertEqual(len(self.nonce), 43)
        self.assertEqual(self.nonce, b64(self.raw).decode("ascii"))
        r = self.check()
        self.assertEqual(r["rawChallengeSha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(r["encodedCommandNonceSha256"], hashlib.sha256(self.nonce.encode()).hexdigest())
        self.assertNotEqual(r["rawChallengeSha256"], r["encodedCommandNonceSha256"])

    def test_03_short_raw_challenge_refused(self):
        with self.assertRaises(E.Refused):
            self.check(raw=self.raw[:-1])

    def test_04_long_raw_challenge_refused(self):
        with self.assertRaises(E.Refused):
            self.check(raw=self.raw + b"x")

    def test_05_bytearray_refused(self):
        with self.assertRaises(E.Refused):
            self.check(raw=bytearray(self.raw))

    def test_06_text_or_boolean_challenge_refused(self):
        for val in (self.nonce, True, None):
            with self.subTest(val=val), self.assertRaises(E.Refused):
                self.check(raw=val)

    def test_07_one_byte_mutated_challenge_refused(self):
        with self.assertRaises(E.Refused):
            self.check(raw=bytes([1]) + self.raw[1:])

    def test_08_substituted_public_signing_key_refused(self):
        key = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(E.Refused):
            self.check(serial=self.proof(key, self.frame))

    def test_09_modified_signed_denial_refused(self):
        altered = bytearray(self.frame)
        altered[-4] ^= 1
        with self.assertRaises(E.Refused):
            self.check(serial=self.proof(self.pub, bytes(altered)))

    def test_10_duplicate_uart_proof_refused(self):
        with self.assertRaises(E.Refused):
            self.check(serial=self.serial + self.serial)

    def test_11_extra_uart_authorization_text_not_a_grant(self):
        out = self.check(serial=self.serial + b"C4B_ID_PASS // CAN_BEGIN_SIGN_IN_TRUE\n")
        self.assert_denied(out)

    def test_12_wrong_receipt_action_refused(self):
        body = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE", "requestId": None,
        }) + b"\n"
        wrong = ReceiptIssuer(self.key).seal("CANCEL", None, self.nonce, body)
        with self.assertRaises(E.Refused):
            self.check(serial=self.proof(self.pub, wrong))

    def test_13_original_positive_authority_field_refused(self):
        original = E.C4B.inspect_ci_only
        def poisoned(*, serial, controller_challenge):
            x = original(serial=serial, controller_challenge=controller_challenge)
            x["hostAuthenticated"] = True
            return x
        with mock.patch.object(E.C4B, "inspect_ci_only", side_effect=poisoned):
            with self.assertRaisesRegex(E.Refused, "PROOF_AUTHORITY_REFUSED"):
                self.check()

    def test_14_unexpected_original_proof_field_refused(self):
        original = E.C4B.inspect_ci_only
        def poisoned(*, serial, controller_challenge):
            x = original(serial=serial, controller_challenge=controller_challenge)
            x["productionGranted"] = True
            return x
        with mock.patch.object(E.C4B, "inspect_ci_only", side_effect=poisoned):
            with self.assertRaisesRegex(E.Refused, "PROOF_FIELDS_REFUSED"):
                self.check()

    def test_15_original_nonce_digest_substitution_refused(self):
        original = E.C4B.inspect_ci_only
        def poisoned(*, serial, controller_challenge):
            x = original(serial=serial, controller_challenge=controller_challenge)
            x["controllerChallengeSha256"] = "0" * 64
            return x
        with mock.patch.object(E.C4B, "inspect_ci_only", side_effect=poisoned):
            with self.assertRaisesRegex(E.Refused, "NONCE_DIGEST_MISMATCH"):
                self.check()

    def test_16_noncanonical_serial_prefix_refused(self):
        with self.assertRaises(E.Refused):
            self.check(serial=b"spoof " + self.serial)

    def test_17_denial_proof_without_receipt_refused(self):
        with self.assertRaises(E.Refused):
            self.check(serial=b"C4B_ID_PASS // RECEIPT_ALREADY_VERIFIED\n")

    def test_18_no_native_signer_credential_or_trust_root_created(self):
        src = (Path(__file__).parent /
               "c4b_raw_challenge_evidence_candidate_ci.py").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        for prohibited in ("Ed25519PrivateKey", "socket.socket(", "sqlite3.connect(",
                           "subprocess.run(", "os.system(", "credentialActionsEnabled\": True",
                           "productionAuthority\": True"):
            self.assertNotIn(prohibited, src)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assert_denied(self.check())

if __name__ == "__main__":
    unittest.main(verbosity=2)
