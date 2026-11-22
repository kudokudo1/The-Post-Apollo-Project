#!/usr/bin/env python3
"""Real Linux peer-fd tests for non-authorizing Connections TimeW observation."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "c3e_timew_native_packet_observer",
    ROOT / "services/connections/ConnectionsTimeWNativePacketObservation.py")
assert spec is not None and spec.loader is not None
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


@unittest.skipUnless(sys.platform == "linux", "Linux native socket test only")
class NativePeerReadOnlyTests(unittest.TestCase):
    def pair(self, *, kind=socket.SOCK_SEQPACKET, credentials=True, timeout=0.5):
        reader, writer = socket.socketpair(socket.AF_UNIX, kind)
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        reader.settimeout(timeout)
        if credentials:
            reader.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        return reader, writer

    def deny(self, reason, r):
        with self.assertRaisesRegex(P.ObservationHold, reason):
            P.inspect_one_untrusted_packet(r)

    def test_real_kernel_peer_pidfd_observation_is_still_untrusted(self):
        r, w = self.pair()
        payload = b'{"fakeProtectedSelection":true,"grant":"SPENT"}'
        w.send(payload)
        z = P.inspect_one_untrusted_packet(r)
        self.assertEqual(z["packetLength"], len(payload))
        self.assertEqual(z["packetSha256Untrusted"],
                         hashlib.sha256(payload).hexdigest())
        self.assertEqual(z["kernelPeerPidObserved"], os.getpid())
        self.assertEqual(z["status"],
                         "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED")
        self.assertEqual(z["safeActions"], [])
        for flag in P.NO_AUTHORITY:
            self.assertIs(z[flag], False, flag)

    def test_inherited_socket_child_sender_cannot_borrow_parent_identity(self):
        r, w = self.pair()
        child = os.fork()
        if child == 0:
            try:
                r.close()
                w.send(b'child says surface is selected')
                w.close()
                os._exit(0)
            except (OSError, ValueError):
                os._exit(5)
        w.close()
        try:
            self.deny("DIFFERENT_SENDER_OR_INHERITED_SOCKET", r)
        finally:
            _child, status = os.waitpid(child, 0)
            self.assertEqual(status, 0)

    def test_stream_socket_refused_before_receive(self):
        r, _ = self.pair(kind=socket.SOCK_STREAM)
        self.deny("EXACT_CONNECTED_UNIX_SEQPACKET_REQUIRED", r)

    def test_missing_passcred_refused(self):
        r, w = self.pair(credentials=False)
        w.send(b'payload')
        self.deny("PER_PACKET_KERNEL_CREDENTIALS_REQUIRED", r)

    def test_timeout_none_and_unbounded_refused(self):
        for timeout in (None, 0, 2.0):
            with self.subTest(timeout=timeout):
                r, w = self.pair(timeout=timeout)
                w.send(b'payload')
                self.deny("BOUNDED_TIMEOUT_REQUIRED", r)

    def test_oversized_packet_refused_not_truncated_into_good_packet(self):
        r, w = self.pair()
        w.send(b'x' * (P.MAX_PAYLOAD + 1024))
        self.deny("PACKET_TRUNCATED_OVERSIZED_OR_EMPTY", r)

    def test_empty_packet_refused(self):
        r, w = self.pair()
        w.send(b'')
        self.deny("PACKET_TRUNCATED_OVERSIZED_OR_EMPTY", r)

    def test_peer_pidfd_kernel_unsupported_is_safe_hold(self):
        r, w = self.pair()
        w.send(b'payload')
        with patch.object(P, "SO_PEERPIDFD", 0x7fffffff):
            self.deny("KERNEL_PEER_OBSERVATION_UNAVAILABLE", r)

    def test_closed_receiver_refused(self):
        r, _ = self.pair()
        r.close()
        self.deny("KERNEL_PEER_OBSERVATION_UNAVAILABLE", r)

    def test_empty_or_synthetic_authority_not_promoted(self):
        for content in (b'not JSON', b'{"productionAuthority":true}',
                        b'{"scope":"hospital-staffing","approved":true}'):
            with self.subTest(content=content):
                r, w = self.pair()
                w.send(content)
                result = P.inspect_one_untrusted_packet(r)
                self.assertFalse(result["productionAuthority"])
                self.assertFalse(result["nativeGeometryAllowed"])
                self.assertFalse(result["sourceEvidenceTrusted"])

    def test_no_enrollment_no_grant_even_if_caller_supplies_fake_roots(self):
        for args in ({}, {"public_key":"self-enrolled", "c5_spent":True}):
            with self.assertRaisesRegex(P.ObservationHold,
                                        "PROTECTED_SWAYPX_SOURCE_AND_C5_NOT_ENROLLED"):
                P.run_native_timew_source_admission(**args)


if __name__ == "__main__":
    unittest.main()
