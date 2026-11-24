#!/usr/bin/env python3
"""DOC4 C5-H11: original PX COMMIT outcome is UNKNOWN if terminal reply missing.

All inputs are disposable. The real native C5 issuer retains unconditional
human-consent hard denial BEFORE the installed signing key. These tests
directly exercise only the newly separated *post-authorized* commit helper
with an ephemeral in-memory test signature and mocked PX exchange.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S
import test_hospital_c5_native_consent_hard_hold as H4


class HospitalC5H11OriginalCommitUnknown(unittest.TestCase):
    def setUp(self):
        fixture = H4.NativeConsentHardHold("test_02_valid_trash_and_polkit_success_still_hold")
        fixture.setUp()
        self.request = fixture.request
        self.prepared = fixture.prepared
        self.policy = fixture.policy
        self.nonce = fixture.prepared["requestNonce"]
        self.now = fixture.now
        self.key = Ed25519PrivateKey.generate()  # Not an installed credential.
        self.signed = C.sign_px_grant(
            request=self.request, prepared=self.prepared,
            operator_uid=1000, seat_id="logind-seat0-c1",
            host_id=self.policy["hostId"], private_key=self.key,
            nonce_bytes=bytes(range(32)), approval_bytes=bytes(range(18)),
            now=self.now,
        )
        self.receipt = self.correct_receipt()
        self.calls = []

    def correct_receipt(self):
        body = json.loads(self.signed)["body"]
        return {
            "schema": C.RECEIPT_SCHEMA,
            "requestNonce": self.nonce,
            "roomId": self.request["roomId"],
            "action": self.request["action"],
            "revisionAfter": self.prepared["expectedRevision"] + 1,
            "grantDigest": hashlib.sha256(
                C.PX_DOMAIN + C.canonical(body)).hexdigest(),
            "state": "TRASHED" if self.request["action"] == "TRASH" else "ACTIVE",
            "originalPreserved": True, "burnAllowed": False,
        }

    def invoke(self, *, result=None, fault=None):
        def writer(policy, packet):
            self.calls.append(packet)
            self.assertIs(policy, self.policy)
            self.assertEqual(packet["kind"], "commit")
            self.assertEqual(packet["action"], self.request["action"])
            self.assertEqual(packet["roomId"], self.request["roomId"])
            self.assertEqual(packet["requestNonce"], self.nonce)
            self.assertEqual(packet["writerInstance"],
                             self.prepared["writerInstance"])
            self.assertEqual(packet["signedGrant"], self.signed.decode("ascii"))
            if fault is not None:
                raise fault
            return (C.canonical(self.receipt)
                    if result is None else result)
        with patch.object(S, "_writer_exchange", side_effect=writer):
            return S._commit_with_terminal_receipt_or_unknown(
                self.policy, self.request, self.prepared, self.nonce, self.signed)

    def unknown(self, *, result=None, fault=None):
        with self.assertRaisesRegex(
            C.Refused, "PX_COMMIT_OUTCOME_UNKNOWN_HOLD_NO_AUTO_RETRY"
        ):
            self.invoke(result=result, fault=fault)
        self.assertEqual(len(self.calls), 1,
                         "must attempt original COMMIT exactly once")

    def test_01_correct_original_px_receipt_committed_once(self):
        out = self.invoke()
        self.assertEqual(out["status"], "COMMITTED")
        self.assertEqual(out["action"], "TRASH")
        self.assertEqual(out["roomId"], self.request["roomId"])
        self.assertTrue(out["originalPreserved"])
        self.assertFalse(out["burnAllowed"])
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("signedGrant", out)

    def test_02_missing_ack_after_original_commit_is_unknown(self):
        self.unknown(fault=TimeoutError("response lost after database commit"))

    def test_03_closed_writer_socket_after_commit_is_unknown(self):
        self.unknown(fault=ConnectionResetError("writer exited after commit"))

    def test_04_untrusted_writer_post_send_refusal_is_unknown(self):
        self.unknown(fault=C.Refused("HOSPITAL_NATIVE_HOLD // PEER_CHANGED"))

    def test_05_no_writer_before_send_conservatively_unknown(self):
        self.unknown(fault=OSError("no protected writer socket"))

    def test_06_malformed_commit_ack_is_unknown(self):
        self.unknown(result=b"not a receipt")

    def test_07_empty_commit_ack_is_unknown(self):
        self.unknown(result=b"")

    def test_08_wrong_grant_digest_is_unknown_not_false_refusal(self):
        receipt = dict(self.receipt, grantDigest="f" * 64)
        self.unknown(result=C.canonical(receipt))

    def test_09_wrong_room_ack_is_unknown_not_new_operation(self):
        receipt = dict(self.receipt, roomId="hospital-room-99")
        self.unknown(result=C.canonical(receipt))

    def test_10_wrong_nonce_ack_is_unknown_not_safe_to_retry(self):
        receipt = dict(self.receipt, requestNonce=C.b64(bytes(range(31, -1, -1))))
        self.unknown(result=C.canonical(receipt))

    def test_11_wrong_action_ack_is_unknown(self):
        receipt = dict(self.receipt, action="RESTORE")
        self.unknown(result=C.canonical(receipt))

    def test_12_wrong_revision_ack_is_unknown(self):
        receipt = dict(self.receipt, revisionAfter=self.prepared["expectedRevision"])
        self.unknown(result=C.canonical(receipt))

    def test_13_original_not_preserved_ack_is_unknown(self):
        receipt = dict(self.receipt, originalPreserved=False)
        self.unknown(result=C.canonical(receipt))

    def test_14_burn_claiming_ack_is_unknown(self):
        receipt = dict(self.receipt, burnAllowed=True)
        self.unknown(result=C.canonical(receipt))

    def test_15_extra_authorizing_field_ack_is_unknown(self):
        receipt = dict(self.receipt, productionAuthorized=True)
        self.unknown(result=C.canonical(receipt))

    def test_16_duplicate_receipt_json_fields_ack_is_unknown(self):
        raw = C.canonical(self.receipt)
        raw = raw[:-1] + b',"roomId":"hospital-room-99"}'
        self.unknown(result=raw)

    def test_17_restore_valid_receipt_keeps_exact_original_identity(self):
        self.request["action"] = "RESTORE"
        self.prepared.update(action="RESTORE", state="TRASHED",
                             canTrash=False, canRestore=True)
        self.signed = C.sign_px_grant(
            request=self.request, prepared=self.prepared,
            operator_uid=1000, seat_id="logind-seat0-c1",
            host_id=self.policy["hostId"], private_key=self.key,
            nonce_bytes=bytes(range(32)), approval_bytes=bytes(range(18)),
            now=self.now,
        )
        self.receipt = self.correct_receipt()
        out = self.invoke()
        self.assertEqual(out["status"], "COMMITTED")
        self.assertEqual(out["action"], "RESTORE")
        self.assertEqual(len(self.calls), 1)

    def test_18_restore_bad_terminal_ack_is_unknown(self):
        self.request["action"] = "RESTORE"
        self.prepared.update(action="RESTORE", state="TRASHED",
                             canTrash=False, canRestore=True)
        self.signed = C.sign_px_grant(
            request=self.request, prepared=self.prepared,
            operator_uid=1000, seat_id="logind-seat0-c1",
            host_id=self.policy["hostId"], private_key=self.key,
            nonce_bytes=bytes(range(32)), approval_bytes=bytes(range(18)),
            now=self.now,
        )
        self.receipt = self.correct_receipt()
        self.unknown(result=C.canonical(dict(self.receipt, state="TRASHED")))

    def test_19_consent_guard_still_blocks_direct_native_step_before_key(self):
        with self.assertRaisesRegex(
            C.Refused, "INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE"
        ):
            S._require_independent_room_consent(
                self.request, self.prepared,
                (4321, 1000, 1000, 54321), "logind-seat0-c1")

    def test_20_original_source_orders_consent_before_signer_before_commit(self):
        s = (ROOT / "services/connections/hospital/"
             "HospitalNativeIssuerService.py").read_text()
        main = s[s.index("def _native_step(client, policy):"):
                 s.index("def _commit_with_terminal_receipt_or_unknown(")]
        self.assertLess(
            main.index("_require_independent_room_consent(request, prepared, peer, first_seat)"),
            main.index("key = C.load_installed_key()"))
        self.assertLess(main.index("key = C.load_installed_key()"),
                        main.index("signed = C.sign_px_grant("))
        self.assertLess(main.index("signed = C.sign_px_grant("),
                        main.index("return _commit_with_terminal_receipt_or_unknown("))
        commit = s[s.index("def _commit_with_terminal_receipt_or_unknown("):
                   s.index("def main():")]
        self.assertEqual(commit.count("_writer_exchange("), 1)
        self.assertNotIn("retry", commit.lower().split("except ")[1].split("raise")[0])
        self.assertIn("PX_COMMIT_OUTCOME_UNKNOWN_HOLD_NO_AUTO_RETRY", commit)
        self.assertNotIn("os.environ", commit)
        self.assertNotIn("load_installed_key", commit)
        self.assertNotIn("sqlite3.connect(", commit.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
