#!/usr/bin/env python3
"""DOC4 C5-H12: confirmed PX COMMIT is not undone by lost desktop receipt.

This suite never calls the native issuer to sign, loads no installed key,
connects to no protected PX service, and uses only disposable sockets.
The existing H4 independent human-consent hard denial remains mandatory.
"""
from __future__ import annotations

from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S

RECEIPT = {
    "schema": "postapollo.connections.hospital-native-issuer-response.v1",
    "status": "COMMITTED",
    "action": "TRASH",
    "roomId": "room-h12-disposable",
    "revision": 14,
    "originalPreserved": True,
    "burnAllowed": False,
}


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error
        self.calls, self.packets = 0, []

    def send(self, frame):
        self.calls += 1
        self.packets.append(frame)
        if self.error is not None:
            raise self.error
        return len(frame) if self.result is None else self.result

    def recv(self, *_args, **_kwargs):
        raise AssertionError("client receipt must not require an unsafe retry or ACK")


class HospitalC5H12ClientDeliveryUnknown(unittest.TestCase):
    def sent(self, fake):
        S._send_committed_client_receipt_or_unknown(fake, RECEIPT)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(fake.packets, [C.canonical(RECEIPT)])
        self.assertNotIn(b"signedGrant", fake.packets[0])

    def unknown(self, fake):
        with self.assertRaisesRegex(
            C.Refused, "PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY"
        ):
            S._send_committed_client_receipt_or_unknown(fake, RECEIPT)
        self.assertEqual(fake.calls, 1, "one attempt, no client receipt replay")

    def test_01_full_kernel_transport_packet_sent_once(self):
        self.sent(FakeClient())

    def test_02_actual_linux_seqpacket_client_receives_minimal_committed(self):
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with sender, receiver:
            S._send_committed_client_receipt_or_unknown(sender, RECEIPT)
            self.assertEqual(receiver.recv(4096), C.canonical(RECEIPT))
            self.assertNotIn(b"signedGrant", C.canonical(RECEIPT))

    def test_03_actual_linux_closed_client_receipt_is_unknown(self):
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            receiver.close()
            with self.assertRaisesRegex(
                C.Refused, "PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY"
            ):
                S._send_committed_client_receipt_or_unknown(sender, RECEIPT)
        finally:
            sender.close()

    def test_04_zero_byte_client_send_is_unknown(self):
        self.unknown(FakeClient(result=0))

    def test_05_partial_client_send_is_unknown(self):
        self.unknown(FakeClient(result=1))

    def test_06_negative_client_send_is_unknown(self):
        self.unknown(FakeClient(result=-1))

    def test_07_broken_pipe_after_committed_is_unknown(self):
        self.unknown(FakeClient(error=BrokenPipeError("client left")))

    def test_08_reset_client_after_committed_is_unknown(self):
        self.unknown(FakeClient(error=ConnectionResetError("client reset")))

    def test_09_timeout_after_committed_is_unknown(self):
        self.unknown(FakeClient(error=TimeoutError("desktop did not accept packet")))

    def test_10_refusal_after_committed_is_unknown(self):
        self.unknown(FakeClient(error=C.Refused("HOSPITAL_NATIVE_HOLD // CLIENT_UNAVAILABLE")))

    def test_11_type_error_from_client_send_is_unknown(self):
        self.unknown(FakeClient(error=TypeError("invalid send")))

    def test_12_json_canonical_failure_is_unknown(self):
        client = FakeClient()
        with patch.object(C, "canonical", side_effect=ValueError("serialization")):
            with self.assertRaisesRegex(
                C.Refused, "PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY"
            ):
                S._send_committed_client_receipt_or_unknown(client, RECEIPT)
        self.assertEqual(client.calls, 0, "no retry or socket write after serialization failure")

    def test_13_client_disconnect_never_invokes_px_writer_again(self):
        client = FakeClient(error=OSError("post-COMMIT desktop disconnected"))
        with patch.object(
            S, "_writer_exchange",
            side_effect=AssertionError("client reply must never reissue PX COMMIT"),
        ):
            self.unknown(client)

    def test_14_successful_kernel_send_does_not_wait_for_client_ack(self):
        self.sent(FakeClient())  # recv() deliberately raises if unexpectedly called.

    def test_15_source_orders_px_commit_before_client_send_once(self):
        source = (ROOT / "services/connections/hospital/"
                  "HospitalNativeIssuerService.py").read_text()
        main = source[source.index("def main():"):]
        self.assertLess(main.index("response = _native_step(client, policy)"),
                        main.index("_send_committed_client_receipt_or_unknown(client, response)"))
        self.assertEqual(main.count("client.send("), 1, "READY handshake only")
        helper = source[source.index("def _send_committed_client_receipt_or_unknown("):
                        source.index("def main():")]
        self.assertEqual(helper.count("client.send("), 1)
        self.assertNotIn("_writer_exchange(", helper)
        self.assertNotIn("C.load_installed_key(", helper)
        self.assertIn("PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY", helper)

    def test_16_h4_h11_source_gates_still_hold(self):
        source = (ROOT / "services/connections/hospital/"
                  "HospitalNativeIssuerService.py").read_text()
        step = source[source.index("def _native_step(client, policy):"):
                      source.index("def _commit_with_terminal_receipt_or_unknown(")]
        self.assertLess(
            step.index("_require_independent_room_consent(request, prepared, peer, first_seat)"),
            step.index("key = C.load_installed_key()"))
        self.assertLess(
            step.index("key = C.load_installed_key()"),
            step.index("return _commit_with_terminal_receipt_or_unknown("))
        self.assertIn('C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")', source)
        commit = source[source.index("def _commit_with_terminal_receipt_or_unknown("):
                        source.index("def _send_committed_client_receipt_or_unknown(")]
        self.assertEqual(commit.count("_writer_exchange("), 1)
        self.assertIn("PX_COMMIT_OUTCOME_UNKNOWN_HOLD_NO_AUTO_RETRY", commit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
