#!/usr/bin/env python3
"""DOC4 C5-H10: real Linux file-descriptor disposal in native issuer receiver.

No root, installed unit, private signer or protected PX. Disposable socketpair
tests prove that rejecting ancillary data cannot leave received SCM_RIGHTS
descriptors open in the long-running issuer. All test fds are local /dev/null.
"""
from __future__ import annotations

import array
import os
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))

import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S


@unittest.skipUnless(sys.platform == "linux", "Linux SCM_RIGHTS only")
class HospitalNativeAncillaryFdCleanup(unittest.TestCase):
    def setUp(self):
        self.sender = (os.getpid(), os.getuid(), os.getgid())
        self.addCleanup(self.cleanup_tracked_files)
        self.tracked = []

    def cleanup_tracked_files(self):
        for fd in self.tracked:
            try:
                os.close(fd)
            except OSError:
                pass

    def file(self):
        fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        self.tracked.append(fd)
        return fd

    def duplicate(self):
        fd = os.dup(self.file())
        self.tracked.append(fd)
        return fd

    def pair(self):
        rx, tx = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(rx.close)
        self.addCleanup(tx.close)
        rx.settimeout(1.0)
        rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        return rx, tx

    @staticmethod
    def open_fds():
        return set(int(x) for x in os.listdir("/proc/self/fd"))

    def assert_closed(self, fd):
        with self.assertRaises(OSError):
            os.fstat(fd)

    def fake(self, *, data=b"test", controls=(), flags=0, addr=None):
        class Fake:
            def __init__(self):
                self.options = []
                self.args = None
            def setsockopt(self, *args):
                self.options.append(args)
            def recvmsg(self, *args):
                self.args = args
                return data, list(controls), flags, addr
        return Fake()

    def test_01_normal_kernel_packet_still_accepted(self):
        rx, tx = self.pair()
        tx.sendall(b"legitimate-native-request")
        self.assertEqual(
            S._packet_recv(rx, expected_sender=self.sender),
            b"legitimate-native-request")

    def test_02_real_single_scm_rights_refused_without_fd_leak(self):
        rx, tx = self.pair()
        source = self.file()
        before = self.open_fds()
        sent = tx.sendmsg(
            [b"untrusted-native-fd"],
            [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [source]))])
        self.assertEqual(sent, len(b"untrusted-native-fd"))
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(rx, expected_sender=self.sender)
        self.assertEqual(before, self.open_fds())
        os.fstat(source)  # The sender's existing descriptor must remain intact.

    def test_03_real_multi_fd_scm_rights_refused_without_leak(self):
        rx, tx = self.pair()
        sources = [self.file() for _ in range(3)]
        before = self.open_fds()
        tx.sendmsg([b"three-fds"], [(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", sources))])
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(rx, expected_sender=self.sender)
        self.assertEqual(before, self.open_fds())
        for fd in sources:
            os.fstat(fd)

    def test_04_real_rights_closed_before_wrong_sender_credential(self):
        rx, tx = self.pair()
        source = self.file()
        before = self.open_fds()
        tx.sendmsg([b"wrong-id"], [(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [source]))])
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(rx, expected_sender=(self.sender[0] + 1, *self.sender[1:]))
        self.assertEqual(before, self.open_fds())

    def test_05_real_oversized_packet_with_rights_leaves_no_fd(self):
        rx, tx = self.pair()
        source = self.file()
        before = self.open_fds()
        tx.sendmsg([b"x" * (S.MAX_IPC + 128)], [(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [source]))])
        with self.assertRaises(C.Refused):
            S._packet_recv(rx, expected_sender=self.sender)
        self.assertEqual(before, self.open_fds())

    def test_06_real_truncated_ancillary_rights_leaves_no_fd(self):
        rx, tx = self.pair()
        source = self.file()
        before = self.open_fds()
        tx.sendmsg([b"many-rights"], [(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [source] * 80))])
        with self.assertRaises(C.Refused):
            S._packet_recv(rx, expected_sender=self.sender)
        self.assertEqual(before, self.open_fds())

    def test_07_forged_rights_control_fds_all_closed(self):
        first, second = self.duplicate(), self.duplicate()
        pkt = self.fake(controls=[
            (socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", first)),
            (socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", second)),
        ])
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(first)
        self.assert_closed(second)

    def test_08_malformed_trailing_rights_byte_still_closes_full_fd(self):
        fd = self.duplicate()
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", fd) + b"!")])
        with self.assertRaisesRegex(C.Refused, "RIGHTS_MALFORMED_OR_CLOSE_FAILED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(fd)

    def test_09_bad_fd_rights_record_does_not_skip_later_valid_fd(self):
        fd = self.duplicate()
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_RIGHTS,
            struct.pack("2i", 1 << 30, fd))])
        with self.assertRaisesRegex(C.Refused, "RIGHTS_MALFORMED_OR_CLOSE_FAILED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(fd)

    def test_10_negative_fd_rights_record_cannot_skip_valid_fd(self):
        fd = self.duplicate()
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("2i", -1, fd))])
        with self.assertRaisesRegex(C.Refused, "RIGHTS_MALFORMED_OR_CLOSE_FAILED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(fd)

    def test_11_msg_ctrunc_closes_received_rights_before_refusal(self):
        fd = self.duplicate()
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", fd))],
            flags=socket.MSG_CTRUNC)
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(fd)

    def test_12_msg_trunc_closes_received_rights_before_refusal(self):
        fd = self.duplicate()
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", fd))],
            flags=socket.MSG_TRUNC)
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_RIGHTS_CLOSED"):
            S._packet_recv(pkt, expected_sender=self.sender)
        self.assert_closed(fd)

    def test_13_missing_credentials_even_with_no_fds_refused(self):
        with self.assertRaisesRegex(
                C.Refused, "PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER"):
            S._packet_recv(self.fake(), expected_sender=self.sender)

    def test_14_unknown_ancillary_control_refused_after_credentials(self):
        packet = self.fake(controls=[
            (socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
             struct.pack("3i", *self.sender)),
            (socket.SOL_SOCKET, 0x7fffffff, b"x")])
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_CONTROL_MESSAGE"):
            S._packet_recv(packet, expected_sender=self.sender)

    def test_15_duplicate_kernel_credentials_refused(self):
        anc = (socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
               struct.pack("3i", *self.sender))
        with self.assertRaisesRegex(
                C.Refused, "PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER"):
            S._packet_recv(self.fake(controls=[anc, anc]),
                           expected_sender=self.sender)

    def test_16_unexpected_sender_address_refused(self):
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
            struct.pack("3i", *self.sender))], addr=b"other-peer")
        with self.assertRaisesRegex(C.Refused, "BOUNDED_NATIVE_PACKET_REFUSED"):
            S._packet_recv(pkt, expected_sender=self.sender)

    def test_17_recvmsg_uses_close_on_exec_and_enables_passcred(self):
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
            struct.pack("3i", *self.sender))])
        self.assertEqual(S._packet_recv(pkt, expected_sender=self.sender), b"test")
        self.assertEqual(pkt.args[-1], socket.MSG_CMSG_CLOEXEC)
        self.assertGreaterEqual(pkt.args[1], socket.CMSG_SPACE(12))
        self.assertIn((socket.SOL_SOCKET, socket.SO_PASSCRED, 1), pkt.options)

    def test_18_malformed_credentials_never_create_authority(self):
        pkt = self.fake(controls=[(
            socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
            struct.pack("3i", *self.sender) + b"!")])
        with self.assertRaisesRegex(C.Refused, "UNEXPECTED_NATIVE_CONTROL_MESSAGE"):
            S._packet_recv(pkt, expected_sender=self.sender)

    def test_19_source_preserves_unconditional_consent_hard_gate(self):
        source = (ROOT / "services/connections/hospital/"
                  "HospitalNativeIssuerService.py").read_text()
        self.assertIn('C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")',
                      source)
        start = source.index("def _native_step(client, policy):")
        step = source[start:]
        self.assertLess(
            step.index("_require_independent_room_consent(request, prepared, peer, first_seat)"),
            step.index("key = C.load_installed_key()"))
        self.assertLess(step.index("key = C.load_installed_key()"),
                        step.index('"kind": "commit"'))

    def test_20_no_test_bypass_or_runtime_hospital_agent_added(self):
        source = (ROOT / "services/connections/hospital/"
                  "HospitalNativeIssuerService.py").read_text()
        for unsafe in ("HospitalC5ExactConsentProbe",
                       "HospitalC5H9C3eNegativeIntegration",
                       "HOSPITAL_C5_HUMAN_CONSENT",
                       "allow_untrusted", "operatorConfirmed"):
            self.assertNotIn(unsafe, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
