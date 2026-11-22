#!/usr/bin/env python3
"""Real Linux SCM_RIGHTS fd cleanup regression for deny-only TimeW observer.

The test creates real OS file descriptors and proves their closure after HOLD.
It does not create a trusted producer, installer, SwayPX selection or C5 grant.
"""
from __future__ import annotations

import array
import errno
import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "connections_timew_fd_cleanup",
    ROOT / "services/connections/ConnectionsTimeWNativePacketObservation.py")
if spec is None or spec.loader is None:
    raise RuntimeError("C3E_TIMEW_OBSERVER_REQUIRED")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


@unittest.skipUnless(sys.platform == "linux", "Linux SCM_RIGHTS only")
class NativeRightsCleanupTests(unittest.TestCase):
    def pair(self):
        reader, writer = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        reader.settimeout(0.5)
        reader.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        return reader, writer

    def closed(self, fd):
        with self.assertRaises(OSError) as caught:
            os.fstat(fd)
        self.assertEqual(caught.exception.errno, errno.EBADF)

    def test_01_received_unexpected_rights_are_closed_before_hold(self):
        reader, writer = self.pair()
        writer.send(b'{"fakeCompositorGrant":true}')
        anchor = os.open("/dev/null", os.O_RDONLY)
        self.addCleanup(os.close, anchor)
        received = []
        original_recvmsg = socket.socket.recvmsg

        def inject(sock, *args):
            packet, controls, flags, address = original_recvmsg(sock, *args)
            received.append(os.dup(anchor))
            return (packet, controls + [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", received).tobytes())],
                flags, address)

        with patch.object(socket.socket, "recvmsg", new=inject):
            with self.assertRaisesRegex(P.ObservationHold,
                                        "UNEXPECTED_SCM_RIGHTS_CLOSED"):
                P.inspect_one_untrusted_packet(reader)
        self.assertEqual(len(received), 1)
        self.closed(received[0])
        os.fstat(anchor)  # Must not close an unrelated, pre-existing descriptor.

    def test_02_truncated_and_malformed_rights_close_every_delivered_fd(self):
        reader, writer = self.pair()
        writer.send(b"fake C5 SPENT")
        anchor = os.open("/dev/null", os.O_RDONLY)
        self.addCleanup(os.close, anchor)
        received = []
        original_recvmsg = socket.socket.recvmsg

        def inject(sock, *args):
            packet, controls, _flags, address = original_recvmsg(sock, *args)
            received.extend((os.dup(anchor), os.dup(anchor)))
            return (packet, controls + [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", [received[0]]).tobytes() + b"x"),
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", [received[1]]).tobytes())],
                socket.MSG_CTRUNC, address)

        with patch.object(socket.socket, "recvmsg", new=inject):
            with self.assertRaisesRegex(
                    P.ObservationHold,
                    "UNEXPECTED_SCM_RIGHTS_MALFORMED_OR_CLOSE_FAILED"):
                P.inspect_one_untrusted_packet(reader)
        self.assertEqual(len(received), 2)
        for fd in received:
            self.closed(fd)
        os.fstat(anchor)

    def test_03_actual_linux_rights_truncation_does_not_leak_fds(self):
        reader, writer = self.pair()
        fd = os.open("/dev/null", os.O_RDONLY)
        try:
            writer.sendmsg([b"fake source packet"], [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", [fd]).tobytes())])
        finally:
            os.close(fd)
        before = len(os.listdir("/proc/self/fd"))
        with self.assertRaises(P.ObservationHold):
            P.inspect_one_untrusted_packet(reader)
        after = len(os.listdir("/proc/self/fd"))
        self.assertEqual(after, before)

    def test_04_recvmsg_uses_close_on_exec_flag(self):
        reader, writer = self.pair()
        writer.send(b"untrusted")
        called = []
        real_recvmsg = socket.socket.recvmsg

        def observe_flag(sock, *args):
            called.append(args)
            return real_recvmsg(sock, *args)

        with patch.object(socket.socket, "recvmsg", new=observe_flag):
            out = P.inspect_one_untrusted_packet(reader)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][2], socket.MSG_CMSG_CLOEXEC)
        for flag in P.NO_AUTHORITY:
            self.assertIs(out[flag], False)

    def test_05_later_rights_are_closed_after_earlier_bad_cmsg(self):
        reader, writer = self.pair()
        writer.send(b"untrusted")
        fd = os.open("/dev/null", os.O_RDONLY)
        self.addCleanup(os.close, fd)
        claimed_fd = os.dup(fd)
        real_recvmsg = socket.socket.recvmsg

        def inject(sock, *args):
            packet, controls, flags, addr = real_recvmsg(sock, *args)
            return (packet, controls + [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS, b"x"),
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", [claimed_fd]).tobytes())],
                flags, addr)

        with patch.object(socket.socket, "recvmsg", new=inject):
            with self.assertRaisesRegex(
                    P.ObservationHold,
                    "UNEXPECTED_SCM_RIGHTS_MALFORMED_OR_CLOSE_FAILED"):
                P.inspect_one_untrusted_packet(reader)
        self.closed(claimed_fd)


if __name__ == "__main__":
    unittest.main()
