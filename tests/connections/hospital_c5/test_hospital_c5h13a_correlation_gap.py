#!/usr/bin/env python3
"""H13a: actual issuer helper witnesses, not a recovery implementation.

Only ephemeral fixture grants, mocked PX exchanges and disposable socketpairs.
No installed issuer, protected storage, recovery endpoint or authority.
"""
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_hospital_c5h11_commit_unknown_hold as H11

C, S = H11.C, H11.S


def fixture():
    case = H11.HospitalC5H11OriginalCommitUnknown()
    case.setUp()
    return case


class OriginalCorrelationGap(unittest.TestCase):
    def test_distinct_original_nonces_collapse_to_same_desktop_receipt(self):
        first, second = fixture(), fixture()
        second.nonce = C.b64(bytes([91]) * 32)
        self.assertNotEqual(first.nonce, second.nonce)
        second.prepared["requestNonce"] = second.nonce
        second.receipt = second.correct_receipt()
        left, right = first.invoke(), second.invoke()
        self.assertNotEqual(first.calls[0]["requestNonce"],
                            second.calls[0]["requestNonce"])
        self.assertEqual(left, right)
        self.assertNotIn("requestNonce", left)
        self.assertNotIn("grantDigest", left)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(len(second.calls), 1)

    def test_cross_original_px_receipt_never_becomes_desktop_success(self):
        case = fixture()
        wrong = dict(case.receipt, requestNonce=C.b64(bytes([92]) * 32))
        case.unknown(result=C.canonical(wrong))

    def test_original_px_ack_loss_never_attempts_second_commit(self):
        case = fixture()
        case.unknown(fault=TimeoutError("fixture original ACK lost"))

    def test_verified_px_commit_then_real_client_disconnect(self):
        case = fixture()
        receipt = case.invoke()
        self.assertEqual(receipt["status"], "COMMITTED")
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with sender, receiver:
            receiver.close()
            with patch.object(S, "_writer_exchange",
                              side_effect=AssertionError("unexpected PX retry")):
                with self.assertRaisesRegex(
                    C.Refused,
                    "PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY"
                ):
                    S._send_committed_client_receipt_or_unknown(sender, receipt)
        self.assertEqual(len(case.calls), 1)
        self.assertEqual(case.calls[0]["requestNonce"], case.nonce)

    def test_successful_delivery_still_omits_original_correlation(self):
        case = fixture()
        receipt = case.invoke()
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with sender, receiver:
            S._send_committed_client_receipt_or_unknown(sender, receipt)
            raw = receiver.recv(4096)
        self.assertEqual(raw, C.canonical(receipt))
        self.assertNotIn(b"requestNonce", raw)
        self.assertNotIn(b"grantDigest", raw)

    def test_request_cannot_supply_correlation_as_current_authority(self):
        case = fixture()
        with self.assertRaises(C.Refused):
            C.validate_request(C.canonical(dict(case.request,
                                                requestNonce=case.nonce)))

    def test_independent_consent_remains_deny_only(self):
        case = fixture()
        with self.assertRaisesRegex(C.Refused,
                                   "INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE"):
            S._require_independent_room_consent(
                case.request, case.prepared, (4321, 1000, 1000, 54321),
                "logind-seat0-c1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
